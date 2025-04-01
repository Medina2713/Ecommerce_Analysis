import psycopg2
from psycopg2.extras import execute_batch
import os
import pandas as pd
from flask import Flask, jsonify, render_template, request
import logging
from collections import defaultdict, Counter
from datetime import datetime
from utils import get_product_by_id_api
from contextlib import contextmanager

logger = logging.getLogger("database")
# conexão antiga

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        dbname = os.getenv('DB_NAME'),
        user = os.getenv('DB_USER'),
        password = os.getenv('DB_PASSWORD'),
        host = os.getenv('DB_HOST'),
        port = os.getenv('DB_PORT') 
    )
    try:
        yield conn
        
    finally:
        conn.close()


# QUERYS ----------------
INSERT_VENDAS = '''
    INSERT INTO vendas (
        nf, 
        id_nf_erp, 
        data_emissao,
        valor_total, 
        cidade, 
        pedido_ecommerce, 
        serie, 
        nome_cliente, 
        uf, 
        frete_nf, 
        desconto, 
        valor_produtos,
        pis,
        cofins,
        icms,
        difal
        
        
    ) 
    VALUES (
    %(nf)s, %(id_nf_erp)s, %(data_emissao)s, %(valor_total)s, %(cidade)s,
    %(pedido_ecommerce)s, %(serie)s, %(nome_cliente)s, %(uf)s, %(frete_nf)s,
     %(desconto)s, %(valor_produtos)s, %(pis)s, %(cofins)s, %(icms)s, %(difal)s )
     RETURNING id;
'''

INSERT_VENDA_PRODUTOS = ''' 
    INSERT INTO venda_produtos (
        venda_id,
        quantidade, valor_unitario,
        valor_total, nome, categoria, comissao_mktp, custo_unitario,
        origem_produto,produto_id,sku,marca
    )
    VALUES (
        %(venda_id)s, %(quantidade)s, %(valor_unitario)s,
        %(valor_total)s, %(nome)s, %(categoria)s,
        %(comissao_mktp)s, %(custo_unitario)s,%(origem_produto)s, %(produto_id)s, %(sku)s, %(marca)s
    );
'''# PND -Recolocar produto_id



SELECT_TAXA_MKTP = '''
    SELECT taxa, acrescimo
    FROM taxas_marketplaces
    WHERE marketplace = %s
        AND EXTRACT(YEAR FROM mes) = EXTRACT(YEAR FROM DATE %s)
        AND EXTRACT(MONTH FROM mes) = EXTRACT(MONTH FROM DATE %s);
'''
#1
UPDATE_ICMS = '''
   UPDATE vendas v
    SET icms = CASE
        WHEN uf = 'MG' THEN  valor_total * 0.06
        ELSE valor_total * 0.013

    END
    
    WHERE id IN (
        SELECT id
        FROM vendas
        WHERE ajustada = FALSE
        ORDER BY id DESC
        LIMIT %s
    ); 
'''
UPDATE_ICMS_ORIGEM = '''
        UPDATE vendas v
    SET icms = CASE
        WHEN uf = 'MG' AND vp.origem_produto IN ('1', '2', '3', '6', '7') THEN v.valor_total * 0.14
        WHEN uf = 'MG' AND vp.origem_produto NOT IN ('1', '2', '3', '6', '7') THEN v.valor_total * 0.06
        ELSE v.valor_total * 0.013
    END
    FROM venda_produtos vp
    WHERE v.id = vp.venda_id
    AND v.id IN (
        SELECT v_in.id
        FROM vendas v_in
        WHERE v_in.ajustada = FALSE
        ORDER BY v_in.id DESC
        LIMIT %s
        
    ); 
'''
#2
UPDATE_COMISSAO = '''
    UPDATE vendas v
    SET 
        comissao = COALESCE(sub.total_comissao, 0),
        custo_produtos = COALESCE(sub.total_custo_produtos, 0)
    FROM (
        SELECT 
            venda_id, 
            SUM(comissao_mktp) AS total_comissao,
            SUM(custo_unitario * quantidade) AS total_custo_produtos
        FROM venda_produtos
        GROUP BY venda_id
    ) sub
    WHERE v.id = sub.venda_id
    AND v.id IN (
        SELECT id
        FROM vendas
        WHERE ajustada = false
        ORDER BY id DESC
        LIMIT %s
        
    )
    ;
'''
#3
UPDATE_PICOFINS = '''
    UPDATE vendas v
    SET 
        pis_calculado = pis - ((COALESCE(frete_mktp, 0) + custo_produtos + comissao + frete_nf - subsidio ) * 0.0165),
        cofins_calculado = cofins - ((COALESCE(frete_mktp, 0) + custo_produtos + comissao + frete_nf - subsidio ) * 0.076)
    WHERE v.id IN (
        SELECT id
        FROM VENDAS
        WHERE ajustada = false
        ORDER BY id DESC
        LIMIT %s
    );
'''
#4
UPDATE_MARGEM = '''
    UPDATE vendas v
    SET 
        margem = valor_produtos + subsidio - (icms + difal + pis_calculado + cofins_calculado + comissao + custo_produtos + COALESCE(frete_mktp,0)),
        ajustada = TRUE
    WHERE v.id IN (
        SELECT id
        FROM vendas
        WHERE ajustada = false
        ORDER BY id DESC
        LIMIT %s
    );
'''
TRIM_VENDAS_NF = '''
    UPDATE vendas
    SET nf = ltrim(nf,'0')
    WHERE nf LIKE '0%';
    '''
FRETE_AVULSO_MKTP_VENDAS = '''
    UPDATE vendas
    SET
        frete_mktp = COALESCE(NULLIF(f.valor_frete, 'NaN'::float), 0),
        subsidio = COALESCE(NULLIF(f.subsidio, 'NaN'::float), 0)
    FROM fretes_avulsos f
    WHERE vendas.nf = f.nf
    AND vendas.serie = f.serie;
'''
UPDATE_VENDA_ML = '''
   UPDATE vendas v
SET
    subsidio = CASE
                    WHEN (ABS(COALESCE(pm.receita_envio, 0)) - ABS(COALESCE(pm.tarifa_envio, 0))) > 0
                    THEN (ABS(COALESCE(pm.receita_envio, 0)) - ABS(COALESCE(pm.tarifa_envio, 0)))
                    ELSE 0
               END,

    frete_mktp = CASE
                    WHEN (ABS(COALESCE(pm.receita_envio, 0)) - ABS(COALESCE(pm.tarifa_envio, 0))) < 0
                    THEN ABS(ABS(COALESCE(pm.receita_envio, 0)) - ABS(COALESCE(pm.tarifa_envio, 0)))
                    ELSE 0
                 END,
	estimada = false,
	comissao = ABS(pm.tarifa_venda)
FROM pedidos_ml pm
WHERE v.pedido_ecommerce = pm.numero_pedido
AND v.estimada = true;

'''

UPDATE_VENDA_SHP = '''
    UPDATE vendas v
    SET
        estimada = false,
        comissao = ABS(pshp.taxa_comissao + taxa_servico)
        
    FROM pedidos_shp pshp
    WHERE v.pedido_ecommerce = pshp.numero_pedido
    AND v.estimada = true;
'''

UPDATE_VENDA_MGL = '''
        UPDATE vendas v
    SET
        comissao = ABS(pmgl.taxa_desconto + pmgl.taxa_promocao + pmgl.taxa_venda + pmgl.taxa_pedido),
        frete_mktp = ABS(pmgl.cop_frete),
        subsidio = COALESCE(pmgl.receita_desconto, 0) + COALESCE(pmgl.receita_promocao, 0),
        estimada = FALSE

    FROM pedidos_mgl pmgl
    WHERE v.pedido_ecommerce = pmgl.numero_pedido
    AND estimada = TRUE;
'''

UPDATE_VENDAS_AMR = '''
    UPDATE vendas v
    SET
        comissao = ABS(pamr.comissao +
        pamr.comissao_ressarcimento_promocao +
        pamr.comissao_sem_desbloqueio + pamr.participacao_frete +
        pamr.tarifa_adicional),
        estimada = FALSE
    FROM pedidos_amr pamr
    WHERE RIGHT (v.pedido_ecommerce, LENGTH(v.pedido_ecommerce) - POSITION('-' IN v.pedido_ecommerce)) = pamr.numero_pedido
    AND ESTIMADA = TRUE;
'''
INSERT_FRETE_MKTP_AMZ = '''
    UPDATE vendas
    SET frete_mktp = %s
    WHERE id = %s
'''
UPDATE_NOME_LOJA = '''
   UPDATE vendas
SET loja = CASE
    WHEN LEFT(pedido_ecommerce, 2) = '20' AND serie = '1' THEN 'Mercado Livre'
    WHEN LEFT(pedido_ecommerce, 2) = '20' AND serie = '4' THEN 'Full Mercado Livre'
    WHEN LEFT(pedido_ecommerce, 2) = '24' THEN 'Shopee'
    WHEN LEFT(pedido_ecommerce, 2) = '25' THEN 'Shopee'
    WHEN LEFT(pedido_ecommerce, 2) = '70' THEN 'Amazon'
    WHEN LEFT(pedido_ecommerce, 2) IN ('Lo', 'Sh', 'Am') THEN 'Americanas'
    WHEN LEFT(pedido_ecommerce, 2) = 'LU' AND serie = '1' THEN 'Magalu'
    WHEN LEFT(pedido_ecommerce, 2) = 'LU' AND serie = '3' THEN 'Full Magalu'
    WHEN LEFT(pedido_ecommerce, 2) = '10' THEN 'Loja Integrada'
    ELSE 'Loja Desconhecida'
END
WHERE ajustada = FALSE;

'''
#--------------------------------
def insert_nf_data_to_db_database(connection, nf_dict, id_nf_request, item_dict): # Recebe o dicionário com os valores da nf e faz o INSERT no banco
    #print(f"insert_nf_data_to_db_database - item_dict:{item_dict}\nTipo do item_dict: {type(item_dict)}")
    print(f"insert_nf_data_to_db_database - ITEM DICT ↑↑↑↑↑↑\n{item_dict}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(INSERT_VENDAS, nf_dict)
            venda_id = cursor.fetchone()[0] 
           # print(f"insert_nf_data_to_db - venda_id: {type(venda_id)}")
           # print(f"insert_nf_data_to_db - Item_dict: {type(item_dict)}")
            
            for index, (item_key, item_value) in enumerate(item_dict.items(), start=1):
                #print(f"Processando {item_key}: {item_value} (tipo: {type(item_value)})")
                if not isinstance(item_value, dict):
                    #print(f"Skipping {item_key} porque não é um dicionário. Tipo atual: {type(item_value)}")
                    if item_key == 'frete_mktp':
                        frete_mktp = item_value
                    continue  # Pular para o próximo item
                
                
                #print(f"Venda_id antes: {item_value['venda_id']}")
                item_value['venda_id'] = venda_id
                  
                #print(f"insert_nf_data_to_db - Index: {index}, Key: {item_key}, Value: {item_value}")
                
                #get_comissao_ML(item_value['categoria'], nf_dict.get('serie','ERRO'))
                
                cursor.execute(INSERT_VENDA_PRODUTOS,item_value)
            
                
            

           # frete_mktp = item_dict.get('frete_mktp')
            
            #print(f"insert_nf_data_to_db - Frete_mktp = {item_dict['frete_mktp']}")
            cursor.execute(INSERT_FRETE_MKTP_AMZ,(frete_mktp,venda_id))
            connection.commit()
            
            
            print(f"insert_nf_data_to_db - ID_TINY: {id_nf_request} NF:{nf_dict.get('nf','ERRO')} \nDados inseridos com sucesso")
    
    except psycopg2.IntegrityError as e:
        connection.rollback()
        print(f"insert_nf_data_to_db - ID_TINY: {id_nf_request} INTEGRITY - Erro de integridade ao inserir a nf : {e}")
    
    except psycopg2.DataError as e:
        connection.rollback()
        print(f"insert_nf_data_to_db - ID_TINY: {id_nf_request} DATA ERROR - Erro de dados ao inserir a nf {nf_dict['nf']}: {e}")
    
    except psycopg2.DatabaseError as e:
        connection.rollback()
        print(f"insert_nf_data_to_db - ID_TINY: {id_nf_request} DATA BASE ERROR - Erro de banco de dados ao inserir a nf {nf_dict['nf']}: {e}")
    
    except Exception as e:
        connection.rollback()
        print(f"insert_nf_data_to_db - ID_TINY: {id_nf_request}\nErro desconhecido na nf {nf_dict['nf']} id {nf_dict['id_nf_erp']}: {e}")
            
def select_taxa_mktp_from_db_database(marketplace,data_emissao,connection): #recebe o nome da loja a data de emissão da NF e retorna a taxa daquele periodo
    try:
        with connection.cursor() as cursor:
            #print(f"select_taxa_mktp_from_db_database - Marketplace: {marketplace}\nData emissão: {data_emissao}")
            cursor.execute(SELECT_TAXA_MKTP,(marketplace,data_emissao,data_emissao))
            result = cursor.fetchone()
            #print(f"select_taxa_mktp_from_db_database - Result 0: {result[0]}\nResult 1: {result[1]}")
            taxa_dict = {
                'taxa':float(result[0]),
                'acrescimo':float(result[1])
            }
            
            ''' print(f"""select_taxa_mktp_from_db_database - 
                  Taxa resgatada: {taxa_dict.get('taxa', 'Erro')} 
                  Acrescimo: {taxa_dict.get('acrescimo', 'Erro')}
                  \nMarketplace: {marketplace}\nData emissão: {data_emissao}""")'''
            return taxa_dict
            
    except psycopg2.IntegrityError as e:
        connection.rollback()
        print(f"select_taxa_mktp_from_db_database - INTEGRITY - Erro de integridade ao resgatar taxa do pedido: {e}")
    
    except psycopg2.DataError as e:
        connection.rollback()
        print(f"select_taxa_mktp_from_db_database - DATA ERROR - Erro de dados ao resgatar taxa do pedido: {e}")
    
    except psycopg2.DatabaseError as e:
        connection.rollback()
        print(f"select_taxa_mktp_from_db_database -  DATA BASE ERROR - Erro de banco de dados ao resgatar taxa do pedido: {e}")
    
    except Exception as e:
        connection.rollback()
        print(f"select_taxa_mktp_from_db_database - Erro desconhecido ao resgatar taxa do pedido: {e}")
        
def update_vendas_database(connection, limit):
    try:
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_ICMS_ORIGEM,(limit,))
            cursor.execute(UPDATE_NOME_LOJA)
            cursor.execute(TRIM_VENDAS_NF)
            cursor.execute(UPDATE_COMISSAO,(limit,))
            cursor.execute(FRETE_AVULSO_MKTP_VENDAS)
            cursor.execute(UPDATE_VENDA_SHP)
            cursor.execute(UPDATE_VENDA_ML)
            cursor.execute(UPDATE_VENDA_MGL)
            cursor.execute(UPDATE_PICOFINS,(limit,))
            cursor.execute(UPDATE_MARGEM,(limit,))
            
            connection.commit()
            print(f"update_vendas_database - Vendas atualizadas e margem calculada")
    except Exception as e:
        print(f"Erro ao rodar SCRIPTS de atualização da tabela vendas: {e}")
  
def written_nfs_database(connection):
    SELECT_IDS_NFS = "SELECT id_nf_erp FROM vendas;"
    try:
        with connection.cursor() as cursor:
            cursor.execute(SELECT_IDS_NFS)
            ids_no_banco = {row[0] for row in cursor.fetchall()}
            return ids_no_banco
            
    except Exception as e:
        print(f"pendding_nfs_database - {e}")
      
def read_fretes_avulsos_sheet_database(connection):
    try:
        df = pd.read_excel('/root/Documents/API/API_PYTHON/Planilhas/Fretes_avulsos.xlsx', sheet_name='FRETES AVULSOS')
        
        with connection.cursor() as cursor:
            for index, row in df.iterrows():
                cursor.execute(
                    '''
                    
                    INSERT INTO fretes_avulsos (nf, serie, empresa_frete, valor_frete, subsidio)
                    VALUES (%s,%s,%s,%s,%s) 
                        
                        ''',(row['NF'],row['Serie'],row['Empresa'],row['Valor frete'],row['Subsidio'])
                        )
            connection.commit()
    except Exception as e:
        print(f"read_fretes_avulsos_sheet_database - erro ao inserir planilha na tabela: {e}")
        
def get_fretes_avulsos_planilha(connection):
    try:
        df = pd.read_excel('/root/Documents/API/API_PYTHON/Planilhas/Fretes_avulsos.xlsx', sheet_name='FRETES AVULSOS')

        with connection.cursor() as cursor:
            for index, row in df.iterrows():
                cursor.execute(
                    '''
                    INSERT INTO fretes_avulsos (nf, serie, empresa_frete, valor_frete, subsidio)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (nf, serie)
                    DO NOTHING
                    ''', (row['NF'], row['Serie'], row['Empresa'], row['Valor frete'], row['Subsidio'])
                )
            connection.commit()
    except Exception as e:
        print(f"read_fretes_avulsos_sheet_database - erro ao inserir planilha na tabela: {e}")
       
def read_pedidos_ML_sheet_database(connection):
    try:
        df = pd.read_excel('C:/Users/Desktop/Documents/Inventio/API_PYTHON/AUX_DOCS/ML_PEDIDOS.xlsx', sheet_name='Vendas BR', skiprows=5)
        
        df = df.fillna({
            'N.º de venda': '',                  
            'Receita por produtos (BRL)': 0,     
            'Receita por envio (BRL)': 0,
            'Tarifa de venda e impostos': 0,
            'Tarifas de envio': 0,
            'Total (BRL)': 0
            })
        
        with connection.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    cursor.execute(
                        '''
                        
                        INSERT INTO pedidos_ml (numero_pedido, receita_produtos, receita_envio, tarifa_venda, tarifa_envio, margem_pedido)
                        VALUES (%s,%s,%s,%s,%s,%s) 
                            
                            ''',(row['N.º de venda'],
                                row['Receita por produtos (BRL)'],
                                row['Receita por envio (BRL)'],
                                row['Tarifa de venda e impostos'],
                                row['Tarifas de envio'],
                                row['Total (BRL)'])
                            )
                    connection.commit()
                
                except psycopg2.errors.UniqueViolation:
                    
                    print(f"Pedido {row['N.º de venda']} já existe no banco. Pulando para o próximo.")
                    connection.rollback()
                    continue
                except Exception as inner_e:
                    # Tratar outros erros, fazer rollback e continuar
                    print(f"Erro ao inserir pedido {row['N.º de venda']}: {inner_e}")
                    connection.rollback()
                    continue
            connection.commit()
    except Exception as e:
        print(f"read_pedidos_ML_sheet_database - erro ao inserir planilha na tabela: {e}")
        connection.rollback()

def read_pedidos_SHP_sheet_database(connection):
    try:
        df = pd.read_excel('C:/Users/Desktop/Documents/Inventio/API_PYTHON/AUX_DOCS/SHP_PEDIDOS.xlsx', sheet_name='orders')
        df = df.fillna({
            'ID do pedido': '',
            'Subtotal do produto':0,
            'Taxa de comissão':0,
            'Taxa de serviço':0,
            })
        
        with connection.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    cursor.execute(
                        '''
                        
                        INSERT INTO pedidos_shp (numero_pedido, valor_produtos, taxa_comissao, taxa_serviço)
                        VALUES (%s,%s,%s,%s) 
                            
                            ''',(row['ID do pedido'],
                                 row['Subtotal do produto'],
                                 row['Taxa de comissão'],
                                 row['Taxa de serviço'],
                                )
                        )
                    connection.commit()
                
                except psycopg2.errors.UniqueViolation:
                    
                    print(f"Pedido {row['ID do pedido']} já existe no banco. Pulando para o próximo.")
                    connection.rollback()
                    continue
                except Exception as inner_e:
                    # Tratar outros erros, fazer rollback e continuar
                    print(f"Erro ao inserir pedido {row['ID do pedido']}: {inner_e}")
                    connection.rollback()
                    continue
            
            connection.commit()
    except Exception as e:
        print(f"read_pedidos_SHP_sheet_database - erro ao inserir planilha na tabela: {e}")
        connection.rollback()
        
def read_pedidos_MGL_sheet_database(connection):
    try:
        df = pd.read_excel('C:/Users/Desktop/Documents/Inventio/API_PYTHON/AUX_DOCS/MGL_PEDIDOS.xlsx', sheet_name='PEDIDOS')
        df = df.fillna({
            'Número do pedido': '',
            'Coparticipação de frete': 0,
            'Pago pelo Parceiro (Coparticipação de Desconto à Vista)':0,
            'Pago pelo Magalu (Coparticipação de Desconto à Vista)':0,
            'Pago pelo Magalu (Coparticipação de Preço Promocional)':0,
            'Pago pelo Parceiro (Coparticipação de Preço Promocional)':0,
            'Tarifa fixa por pacote':0,
            'Serviços do marketplace (1+2+3)':0
            
            })
        
        with connection.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    cursor.execute(
                        '''
                        
                        INSERT INTO pedidos_mgl (numero_pedido, cop_frete, receita_desconto,
                                                taxa_desconto, receita_promocao, taxa_promocao,
                                                taxa_venda, taxa_pedido)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) 
                            
                            ''',(row['Número do pedido'],
                                 row['Coparticipação de frete'],
                                 row['Pago pelo Magalu (Coparticipação de Desconto à Vista)'],
                                 row['Pago pelo Parceiro (Coparticipação de Desconto à Vista)'],
                                 row['Pago pelo Magalu (Coparticipação de Preço Promocional)'],
                                 row['Pago pelo Parceiro (Coparticipação de Preço Promocional)'],
                                 row['Serviços do marketplace (1+2+3)'],
                                 row['Tarifa fixa por pacote']
                                )
                        )
                    connection.commit()
                
                except psycopg2.errors.UniqueViolation:
                    
                    print(f"Pedido {row['Número do pedido']} já existe no banco. Pulando para o próximo.")
                    connection.rollback()
                    continue
                except Exception as inner_e:
                    # Tratar outros erros, fazer rollback e continuar
                    print(f"Erro ao inserir pedido {row['Número do pedido']}: {inner_e}")
                    connection.rollback()
                    continue
            
            connection.commit()
    except Exception as e:
        print(f"read_pedidos_MGL_sheet_database - erro ao inserir planilha na tabela: {e}")
        connection.rollback()
        
def read_pedidos_AMR_sheet_database(connection):
    file_path = 'C:\\Users\\Desktop\\Documents\\Inventio\\API_PYTHON\\AUX_DOCS\\AMR_PEDIDOS.xlsx'
    try:
        planilha = pd.read_excel(file_path, sheet_name=None)
        nome_antigo = list(planilha.keys())[0]
        nome_novo = 'PEDIDOS'
        dados_aba = planilha[nome_antigo]
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
            # Escrever a aba com o novo nome
            dados_aba.to_excel(writer, sheet_name=nome_novo, index=False)

        #print(f"A aba '{nome_antigo}' foi renomeada para '{nome_novo}' com sucesso!")
    except Exception as e:
        print(f"Deu ruim pra ler AMR: {e}")

    
    try:
        
        df = pd.read_excel(file_path, sheet_name='PEDIDOS')
        
        df = df.fillna({
            'Entrega': 0,
            'Tipo': '',
            'Valor':0           
            })
        resultados = {}
        for index, row in df.iterrows():
            num_pedido = row['Entrega']
            tipo = row['Tipo']
            valor = row['Valor']
            
            if num_pedido not in resultados:
                resultados[num_pedido] = {
                    'Venda': 0,
                    'Comissao': 0,
                    'Frete_B2W_Entrega': 0,
                    'Comissao_Ressarcimento_Promocao': 0,
                    'Comissao_Sem_Desbloqueio': 0,
                    'Estorno_Comissao': 0,
                    'Estorno_Frete_B2W_Entrega': 0,
                    'Estorno_Venda': 0,
                    'Participacao_frete': 0,
                    'Tarifa_Adicional': 0                    
                }
            if tipo in resultados[num_pedido]:
                resultados[num_pedido][tipo] = valor
        df_final = pd.DataFrame.from_dict(resultados, orient='index') 
        #print(df_final)
        
        with connection.cursor() as cursor:
            for num_pedido, valores in resultados.items():
                try:
                    cursor.execute(
                        '''
                        INSERT INTO pedidos_amr (numero_pedido, venda, comissao,
                                                frete_b2w_entrega, comissao_ressarcimento_promocao,
                                                comissao_sem_desbloqueio, estorno_comissao,
                                                estorno_frete_b2w_entrega, estorno_venda,
                                                participacao_frete, tarifa_adicional)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''',
                        (
                            num_pedido,
                            valores['Venda'],
                            valores['Comissao'],
                            valores['Frete_B2W_Entrega'],
                            valores['Comissao_Ressarcimento_Promocao'],
                            valores['Comissao_Sem_Desbloqueio'],
                            valores['Estorno_Comissao'],
                            valores['Estorno_Frete_B2W_Entrega'],
                            valores['Estorno_Venda'],
                            valores['Participacao_frete'],
                            valores['Tarifa_Adicional']
                        )
                    )
                    connection.commit()
                   # print('read_pedidos_AMR_sheet_database - Pedidos adicionados no banco!')
                
                except psycopg2.errors.UniqueViolation:
                    
                    print(f"read_pedidos_AMR_sheet_database - Pedido {row['Número do pedido']} já existe no banco. Pulando para o próximo.")
                    connection.rollback()
                    continue
                except Exception as inner_e:
                    # Tratar outros erros, fazer rollback e continuar
                    print(f"read_pedidos_AMR_sheet_database - Erro ao inserir pedido {row['Número do pedido']}: {inner_e}")
                    connection.rollback()
                    continue
            
            connection.commit()
            #print(f"")
    except Exception as e:
        print(f"read_pedidos_AMR_sheet_database - erro ao inserir planilha na tabela: {e}")
        connection.rollback()
 
 #FRONT END

def insert_record_front_db(num_nf, serie_nf, id_nf,empresa, valor_frete, subsidio, connection): #Logging Profissional Substitua print por bibliotecas como logging para um melhor monitoramento em produção:
    try:
        
        cursor = connection.cursor()

        # Inserindo no banco de dados
        insert_query = """
        INSERT INTO fretes_avulsos (nf, serie, id_nf_erp, empresa_frete, valor_frete, subsidio)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id_fretes_avulsos
        ;  
        """
        cursor.execute(insert_query, (num_nf, serie_nf, id_nf, empresa, valor_frete, subsidio))
        new_id = cursor.fetchone()[0]
        

        # Confirma a transação
        connection.commit()

        return new_id
    except psycopg2.errors.UniqueViolation:
        # Realiza o rollback para encerrar a transação
        connection.rollback()
        raise ValueError("Registro duplicado: a combinação de NF e Série já existe.")

    except Exception as e:
        # Realiza o rollback para outros erros
        connection.rollback()
        print("Erro ao inserir no banco:", e)
        return None

def check_record_exists(id_nf, num_nf, serie_nf, connection):
    query = """
    SELECT 1 FROM fretes_avulsos
    WHERE id_nf_erp = %s OR (nf = %s AND serie = %s)
    LIMIT 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, (id_nf, num_nf, serie_nf))
        return cursor.fetchone() is not None
def get_fretes_avulsos_db(connection):
    try:
        query = "SELECT id_fretes_avulsos, nf, serie, empresa_frete, valor_frete, subsidio FROM fretes_avulsos ORDER BY id_fretes_avulsos DESC LIMIT 10"
        with connection.cursor() as cursor:
            cursor.execute(query)
            records = cursor.fetchall()
            return records
    
    except Exception as e:
        connection.rollback()
        raise ValueError(f"Erro na consulta: {e}")
    
def select_frete_avulso(num_nf, serie, connection):
    try:
        query = "SELECT * FROM fretes_avulsos WHERE nf = %s AND serie = %s ORDER BY id_fretes_avulsos DESC LIMIT 10"
        with connection.cursor() as cursor:
            cursor.execute(query,(num_nf,serie))
            record = cursor.fetchone()
            print(f"select_frete_avulso - {record}")
            if record:
                return record #jsonify(success=True, valorFrete=record[0], subsidio=record[1])
    
    except Exception as e:
        connection.rollback()
        raise ValueError(f"Erro na consulta: {e}")
    
def update_frete_avulso(connection, valor_frete, subsidio, empresa, num_nf, serie):
    try:
        update_frete_avulso = '''
            UPDATE fretes_avulsos
            SET valor_frete = %s, subsidio = %s, empresa_frete = %s
            WHERE nf = %s AND serie= %s;'''
            
        UPDATE_MARGIN = '''
            UPDATE vendas
            SET
                margem = valor_produtos + subsidio - (icms + difal + pis_calculado + cofins_calculado + comissao + custo_produtos + COALESCE(frete_mktp,0))
            WHERE nf = %s AND serie= %s;

        '''
        UPDATE_PISCOFINS = '''
            UPDATE vendas 
            SET
                pis_calculado = pis - ((COALESCE(frete_mktp, 0) + custo_produtos + comissao + frete_nf - subsidio ) * 0.0165),
                cofins_calculado = cofins - ((COALESCE(frete_mktp, 0) + custo_produtos + comissao + frete_nf - subsidio ) * 0.076)
            WHERE nf = %s AND serie= %s;
            
        '''
        UPDATE_VENDA_FRETE_AVULSO = '''
            UPDATE vendas
            SET
                subsidio = %s,
                frete_mktp = %s
            WHERE nf = %s AND serie = %s;
        '''  
      
        with connection.cursor() as cursor:
            
            cursor.execute(update_frete_avulso,(valor_frete, subsidio, empresa, num_nf, serie))
            cursor.execute(UPDATE_VENDA_FRETE_AVULSO,(subsidio, valor_frete, num_nf,serie))
            
            
            
            cursor.execute(UPDATE_PISCOFINS,(num_nf,serie))
            cursor.execute(UPDATE_MARGIN,(num_nf,serie))
            connection.commit()
            print('update_frete_avulso - Valores atualizados no DB')
            return True
    except Exception as e:
        connection.rollback()
        raise ValueError(f"Erro ao atualizar o frete avulso: {e}")
   
#Produtos
def insert_kit_db(id_produto, quantidade_total, nome_kit, itens_kit, quantidade_itens, connection):
    INSERT_KIT =  '''
        INSERT INTO kits (id_kit_erp, nome_kit, quantidade_itens)
        VALUES (%(id_produto)s, %(nome_kit)s, %(quantidade_total)s) 
        RETURNING id_kit;
        '''
    try:
        with connection.cursor() as cursor:
            cursor.execute(INSERT_KIT, {
                'id_produto': id_produto,
                'nome_kit': nome_kit,
                'quantidade_total': quantidade_total
            })
            id_kit = cursor.fetchone()[0]
            
            for item, quantidade in zip(itens_kit, quantidade_itens):
                
                INSERT_ITEM_KIT = '''
                    INSERT INTO itens_kits (id_kit, id_item_kit_erp, quantidade)
                    VALUES (%(id_kit)s,%(item)s,%(quantidade)s);
                '''
                cursor.execute(INSERT_ITEM_KIT, {
                    'id_kit': id_kit,
                    'item': item,
                    'quantidade': quantidade
                })
            
            connection.commit()
            print(f"Kit {nome_kit} inserido com sucesso!")
    except psycopg2.IntegrityError as e:
        connection.rollback()
        print(f"insert_kit_db -  INTEGRITY - Erro de integridade ao inserir a nf : {e}")
    
    except psycopg2.DataError as e:
        connection.rollback()
        print(f"insert_kit_db -  DATA ERROR - Erro de dados ao inserir o KIT: {e}")
    
    except psycopg2.DatabaseError as e:
        connection.rollback()
        print(f"insert_kit_db -  DATA BASE ERROR - Erro de banco de dados ao inserir o KIT : {e}")
    
    except Exception as e:
        connection.rollback()
        print(f"insert_kit_db - Erro desconhecido no KIT : {e}")
            
        # Parou aqui - Criar tabelas kit e itens_kits no esquema de vendas e venda_produtos

def reset_kits_table_DB(connection):
    DELETE_KITS = '''
                -- Apaga todos os registros da tabela itens_kits e reinicia a sequência
                TRUNCATE TABLE itens_kits RESTART IDENTITY CASCADE;

                -- Apaga todos os registros da tabela kits e reinicia a sequência
                TRUNCATE TABLE kits RESTART IDENTITY CASCADE;

            '''
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(DELETE_KITS)
            connection.commit()
    except Exception as e:
        print(f"Erro ao resetar a tabela de kits: {e}")
        logging.error(
                            f"Erro ao resetar a tabela de kits: {e}"
                        )
 
def get_kits_dict_from_DB(connection):
    try:
        with connection.cursor() as cursor:
            SELECT_KITS = '''
                SELECT k.id_kit, ik.id_item_kit_erp, ik.quantidade
                FROM kits k
                JOIN itens_kits ik ON k.id_kit = ik.id_kit
            '''
            cursor.execute(SELECT_KITS)
            kits = cursor.fetchall()
            #print(kits)
        
        kits_dict = defaultdict(list)
        for id_kit, id_item_kit_erp, quantidade in kits:
            kits_dict[id_kit].append({
                "id_item_kit_erp": id_item_kit_erp,
                 "quantidade": quantidade
            })
        #print(kits_dict)
        return kits_dict
            
            
    except Exception as e:
        print(f"Erro ao resgatar e transformar os kits em dicionarios: {e}")               

#Vendas API

def get_vendas_db(connection):
    try:
        query = "SELECT  nf, serie, loja, valor_total, comissao, margem, subsidio, desconto, frete_mktp FROM vendas ORDER BY id DESC LIMIT 30"
        with connection.cursor() as cursor:
            cursor.execute(query)
            records = cursor.fetchall()
            return records
    
    except Exception as e:
        connection.rollback()
        raise ValueError(f"Erro na consulta: {e}")
    
def select_venda(num_nf, serie, connection):
    try:
        query = "SELECT nf, serie, loja, valor_total, comissao, margem, subsidio, desconto, frete_mktp FROM vendas WHERE nf = %s AND serie = %s ORDER BY id DESC LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(query,(num_nf,serie))
            record = cursor.fetchone()
            print(f"select_venda - {record}")
            if record:
                return record #jsonify(success=True, valorFrete=record[0], subsidio=record[1])
    
    except Exception as e:
        connection.rollback()
        raise ValueError(f"Erro na consulta: {e}")
    
def update_vendas(connection, comissao, margem, subsidio, desconto, frete_mktp, num_nf, serie):
    try:
        update = '''
            UPDATE vendas
            SET comissao = %s, margem = %s, subsidio = %s, desconto = %s, frete_mktp = %s
            WHERE nf = %s AND serie= %s;'''
            
        atualiza_margem = '''
            UPDATE vendas
            SET
                margem = valor_produtos + subsidio - (icms + difal + pis_calculado + cofins_calculado + comissao + custo_produtos + COALESCE(frete_mktp,0))
            WHERE nf = %s AND serie = %s;
        '''
        atualiza_piscofins = '''
            UPDATE vendas
            SET
                pis_calculado = pis - ((COALESCE(frete_mktp, 0) + custo_produtos + comissao + frete_nf - subsidio ) * 0.0165),
        cofins_calculado = cofins - ((COALESCE(frete_mktp, 0) + custo_produtos + comissao + frete_nf - subsidio ) * 0.076)
            WHERE nf = %s AND serie = %s;
        '''
        with connection.cursor() as cursor:
            cursor.execute(update,(comissao, margem, subsidio, desconto, frete_mktp, num_nf, serie))
            cursor.execute(atualiza_margem,(num_nf, serie))
            cursor.execute(atualiza_piscofins,(num_nf, serie))
            connection.commit()
            print('update_frete_avulso - Valores atualizados no DB')
            return True
    except Exception as e:
        connection.rollback()
        raise ValueError(f"Erro ao atualizar o frete avulso: {e}")
    
def exclude_venda(nf, serie):
    try:
        query = '''
            DELETE FROM vendas WHERE nf = %s AND serie = %s;
        '''
        with get_db_connection() as conn:
            conn.cursor().execute(query,(nf,serie))
            conn.commit()
            
        return True
    except Exception as e:
        conn.rollback()
        print(e)
        return False
        
    
    
# Dados nf pelo xml
INSERT_VENDAS_FROM_XML = '''
    INSERT INTO vendas (
        nf, 
         
        data_emissao,
        valor_total, 
        cidade, 
        pedido_ecommerce, 
        serie, 
        nome_cliente, 
        uf, 
        frete_nf, 
        desconto, 
        valor_produtos,
        pis,
        cofins,
        
        difal
        
        
    ) 
    VALUES (
    %(nf)s, %(data_emissao)s, %(valor_total)s, %(cidade)s,
    %(pedido_ecommerce)s, %(serie)s, %(nome_cliente)s, %(UF)s, %(frete_nf)s,
     %(desconto)s, %(valor_produtos)s, %(pis)s, %(cofins)s, %(difal)s )
     RETURNING id;
'''
def xml_nf_to_db(connection, dados_extraidos):
    """
    Processa uma lista de dados extraídos dos XMLs e insere no banco de dados.

    :param connection: Conexão com o banco de dados.
    :param dados_extraidos: Lista de dicionários com dados das notas fiscais.
    """
    try:
        with connection.cursor() as cursor:
            for nf_data in dados_extraidos:
                # Insere os dados da nota fiscal
                nf_query = """
                INSERT INTO vendas (data_emissao, valor_total, uf, cidade, nf, serie, frete_nf, difal, desconto, pis, cofins, valor_produtos, pedido_ecommerce, nome_cliente, icms)
                VALUES (%(data_emissao)s, %(valor_total)s, %(UF)s, %(cidade)s, %(nf)s, %(serie)s, %(frete_nf)s, %(difal)s, %(desconto)s, %(pis)s, %(cofins)s, %(valor_produtos)s, %(pedido_ecommerce)s, %(nome_cliente)s, %(icms)s)
                RETURNING id;
                """
                cursor.execute(nf_query, nf_data)
                venda_id = cursor.fetchone()[0]

                # Insere os produtos relacionados à nota fiscal
                produtos_query = """
                INSERT INTO venda_produtos (venda_id, nome, valor_unitario, quantidade, ean, valor_total)
                VALUES (%(venda_id)s, %(nome)s, %(valor)s, %(quantidade)s, %(EAN)s, %(valor_total_produtos)s);
                """
                for produto in nf_data.get("produtos", []):
                    produto["venda_id"] = venda_id
                    cursor.execute(produtos_query, produto)

                # Insere dados de frete do marketplace, se aplicável
                if nf_data.get("frete_mktp") is not None:
                    frete_query = """
                    INSERT INTO frete_mktp (frete_mktp, venda_id)
                    VALUES (%s, %s);
                    """
                    cursor.execute(frete_query, (nf_data["frete_mktp"], venda_id))
                    
            SET_VALOR_TOTAL = '''
                UPDATE venda_produtos
                SET valor_total = valor_unitario * quantidade
                WHERE valor_total = NULL
            '''
            cursor.execute(SET_VALOR_TOTAL)

            # Commita as transações
            connection.commit()
            print("Dados das notas fiscais inseridos com sucesso.")
    except psycopg2.IntegrityError as e:
        connection.rollback()
        print(f"Erro de integridade ao inserir os dados das notas fiscais: {e}")
    except psycopg2.DataError as e:
        connection.rollback()
        print(f"Erro de dados ao inserir os dados das notas fiscais: {e}")
    except psycopg2.DatabaseError as e:
        connection.rollback()
        print(f"Erro de banco de dados ao inserir os dados das notas fiscais: {e}")
    except Exception as e:
        connection.rollback()
        print(f"Erro desconhecido ao inserir os dados das notas fiscais: {e}")

def insert_product_info_from_xml(id_erp_produto,custo, ean, connection):
    print('Vai atualizar o produto pelo ean')
    try:
        with connection.cursor() as cursor:
            UPDATE_PRODUCT_BY_EAN = '''
                UPDATE venda_produtos
                SET 
                    custo_unitario = %s,
                    produto_id = %s
                WHERE ean = %s AND custo_unitario IS NULL
            '''
            cursor.execute(UPDATE_PRODUCT_BY_EAN,(custo, id_erp_produto, ean))
            connection.commit()
            print('Produtos atualizados com sucesso')
    except psycopg2.IntegrityError as e:
        connection.rollback()
        print(f"Erro de integridade ao inserir os dados das notas fiscais: {e}")
    except psycopg2.DataError as e:
        connection.rollback()
        print(f"Erro de dados ao inserir os dados das notas fiscais: {e}")
    except psycopg2.DatabaseError as e:
        connection.rollback()
        print(f"Erro de banco de dados ao inserir os dados das notas fiscais: {e}")
    except Exception as e:
        connection.rollback()
        print(f"Erro desconhecido ao inserir os dados das notas fiscais: {e}")
            
#Ferramenta para inserir os skus de vendas já escritas no banco ------------------------------------
def insert_sku_from_product_id_database(connection):
    SELECT_PRODUCTS_IDS = '''
            SELECT DISTINCT produto_id
            FROM venda_produtos;
            '''
    try:
        with connection.cursor() as cursor:
            cursor.execute(SELECT_PRODUCTS_IDS)
            ids_produtos = cursor.fetchall()
            print(f"IDS dos produtos: {ids_produtos[0][0]}")
            
        ids_with_sku = {}
        for id_tuple in ids_produtos:
            produto = get_product_by_id_api(id_tuple[0])
            dados_prod = produto.get('retorno', {}).get('produto', {})
            sku = dados_prod.get('codigo', 'ERRO')
            ids_with_sku.update({id_tuple[0]: sku})
            print(f"Adicionado o SKU {sku} ao Código {id_tuple[0]}")
        print(ids_with_sku)
        
        sku_list_file = open('lista_de_skus.txt', 'wt')
        sku_list_file.write(str(ids_with_sku))
        sku_list_file.close()
             
    except Exception as e:
        print(f"insert_sku_from_product_id_database - Deu ruim: {e}")
        
def insert_sku_to_db_database(connection):
    INSERT_SKUS_FROM_ID = '''
        UPDATE venda_produtos
        SET sku = %s
        WHERE sku IS NULL AND produto_id = %s
    '''
    id_skus = {'907257561': '0962', '813780809': '0902-1', '835584202': '792331', '907257555': '0910',
                '845565036': 'MK441', '813781389': 'MK366', '813781569': '4027', '847527755': '790726',
                '813781063': '0123', '813781019': '1420', '813780773': '0340', '907257789': '792273',
                '835584187': '791928', '828073873': 'SP12-1.3', '907257744': '790876', '830226208': 'MK399',
                '835584062': '10764', '835584299': '811080', '838848805': '792413', '822188138': '7265',
                '813781686': 'SP6-45', '822188141': '10842', '830486543': '791846', '813781426': '899551',
                '813781295': 'MK423-2', '813781146': '1172-2', '907257646': '2801', '907899252': '834014',
                '909375743': '791800', '815033648': 'MK420', '908318947': 'MK369', '813781207': '1013-3',
                '835584082': '2802', '907899248': '834013', '815033654': 'MK425', '907257587': '10783',
                '835584053': '991', '822188146': '7534', '813780835': '5175', '826718999': 'MK427',
                '813780759': '0364', '818181558': '5162', '845565033': 'MK440', '835584269': '792489',
                '822188130': '10820', '815033624': 'MK380', '813780815': '0902-2', '834809335': 'MK268',
                '907899190': '790500', '830486537': '791828', '813780821': '0902-3', '813781509': '790694',
                '907257834': '899539', '815033651': 'MK421', '813780746': '5177', '907257617': '1260',
                '830486528': '791670', '907257709': '7857', '838848790': '791827', '813781335': 'MK406',
                '907257715': '790356', '907899304': '834931', '813781310': 'MK416', '847527764': '790874',
                '838848793': '791829', '830486519': '790699', '822188162': '790716', '822188150': '7267',
                '907257686': '3003', '907257663': '2880', '835584273': '792504', '830486489': '2976',
                '813780912': '1474-1', '822188123': '10825', '907257765': '791901', '845564992': 'MK211',
                '835584126': '7266', '909375849': '899504', '907899245': '834012', '907257838': '899552',
                '813780740': '5178', '813781159': '1172-4', '823698229': '1473-3', '834809388': 'MK426',
                '830486505': '7261', '813781048': '1354-1', '838848724': '2852', '813780731': '0991',
                '813781432': '899003', '847527784': '792423', '830226232': 'XK110', '823698232': '1473-4',
                '813781621': '2202', '835584218': '792458', '830226216': 'MK414', '907257639': '2781',
                '813781190': '1013-1', '813780875': '1520', '830486456': '0907', '830226212': 'MK409',
                '813781534': '7531', '813781397': 'MK362', '907257682': '2918', '834809402': 'MK429',
                '908256009': '899501', '907257689': '3706', '813780846': '0343', '813781560': '4030',
                '813781349': 'MK390', '830486481': '2922', '835584226': '792461', '813781527': '7533',
                '835584155': '790710', '823698226': '1473-2', '907257673': '2903', '907257626': '2175',
                '835584057': '10760', '830486493': '4020', '835584289': '811077', '830486486': '2971',
                '823698239': '1473-5', '813781169': '1018', '830486472': '2817', '826719005': 'MK448',
                '813781251': '101-3', '835584067': '10794', '822188159': '791919', '908256004': '810001',
                '838848801': '791933', '847527686': '0987', '819040348': 'SP12-9E', '835584199': '791937',
                '838848761': '7715', '813781339': 'MK394', '813780927': '1474-3', '813781448': '791727',
                '813781495': '790715', '835584181': '791825', '834809395': 'MK428', '847527761': '790728',
                '822188102': '10775', '907257623': '2166', '813781113': '1172', '835584266': '792488',
                '835584160': '790722', '907257614': '1259', '909731617': 'MK264-1', '815033612': 'Mk231',
                '835584147': '7395', '835584107': '2865', '847527758': '790727', '907257774': '791922',
                '907257649': '2806', '835584279': '792530', '813780791': '1476', '909375837': '899002',
                '907257566': '0988', '907257590': '10784', '813781403': 'MK360', '907899233': '830909',
                '907257666': '2893', '835584071': '1177', '813780783': '1710', '907257786': '792264',
                '813780953': '1474-6', '844664181': '10772', '907257768': '791903', '909375696': '791174',
                '838848709': '2157', '813780754': '05156', '835584163': '790723', '835584036': '0863',
                '813781361': 'MK382', '813781456': '791288', '813781452': '791304', '813781643': '2080',
                '835584236': '792466', '813781245': '101-2', '838848735': '2857', '822188115': '10821',
                '835584295': '811079', '838848815': '792527', '822188134': '10827', '828073863': 'SP12-Alarme',
                '835584166': '790738', '835584129': '7307', '830226225': 'XK103', '907257574': '10778',
                '835584170': '791653', '908255980': '2897', '907257584': '10780', '830486547': '792430',
                '813780851': '1780', '908318963': 'MK415', '838848747': '7710', '835584042': '0935',
                '822188109': '0961', '818204200': 'SP12-5', '907257757': '791680', '835584292': '811078',
                '838848732': '2854', '835584173': '791661', '826719002': 'MK447', '822188166': '792469',
                '907257653': '2835', '830486508': '7358', '813780750': '5161', '834809409': 'MK431',
                '813781197': '1013-2', '830486460': '10806', '813781634': '2159', '813780787': '1600',
                '830486466': '2203', '907899065': '0909', '907899152': '2212', '834809346': 'MK361',
                '835584259': '792475', '847527691': '10838', '835584141': '7361', '835584111': '2866',
                '834809377': 'MK417', '907257679': '2906', '813781040': '1354-3', '830486469': '2211',
                '813781602': '2759', '813780778': '0330', '813781515': '7824', '830486550': '792510',
                '813780829': '5518', '813781385': 'MK367', '813781678': 'SP12-7S', '907257660': '2873',
                '813780942': '1474-5', '907257607': '10867', '813780935': '1474-4', '813780736': '5808',
                '813781264': '101-5', '834809359': 'MK402', '834809356': 'MK389', '835584097': '2862',
                '830486540': '791840', '907899198': '790745', '830226228': 'XK105', '813781420': 'MK169',
                '813781473': '791253', '907257760': '791707', '838848774': '790871', '907257642': '2785',
                '907899070': '0984', '909375663': '790334', '830486534': '791673', '828073876': 'SP12-5-T2',
                '830226194': 'MK282', '907257551': '0903', '907257558': '0913', '813781373': 'Mk378',
                '813780855': '1622', '838848712': '2178', '834809431': 'MK435', '907899091': '1220300011',
                '907899239': '834010', '907899261': '834016', '834809370': 'MK408', '813781504': '790708',
                '907899242': '834011', '813781578': '4026', '835584074': '2183', '909375882': '899533',
                '835584119': '6791', '823698220': '1473-1', '830486502': '7221', '830226198': 'MK348',
                '813781487': '790772', '835584116': '2978', '813781542': '7460', '835584177': '791674',
                '828073869': 'SP12-18', '813781287': 'MK423-3', '907257828': '899507', '907899267': '834019',
                '907257630': '2190', '835584135': '7359', '844664202': '2915', '907257751': '791678', '838848697': '0914',
                '830486525': '790701', '813781257': '101-4', '813781590': '4017', '813781439': '899001',
                '847527769': '791676', '907257706': '7856', '830486516': '7535', '835584250': '792471',
                '835584247': '792470', '813781153': '1172-3', '822188156': '790702', '909375702': '791340',
                '907257580': '10779', '815033645': 'MK405', '830226219': 'MK436', '813780767': '0344',
                '835584211': '792427', '909375666': '790582', '834809442': 'MK446', '909375579': '2800',
                '813780867': '1535', '907899230': '830908', '835584286': '811076', '813781410': 'MK326',
                '813781234': '101-1', '835584091': '2822', '847527714': '2205', '826718990': 'MK308',
                '847527726': '3330', '907257771': '791904', '830486478': '2910', '834809367': 'MK407',
                '907257811': '792490', '830486512': '7394', '838848715': '2201', '835584078': '2796',
                '838848721': '2828', '830486531': '791671', '909375794': '792411', '907257754': '791679',
                '845565023': 'MK418', '813781270': '101-6', '834809439': 'MK445', '844664217': '7437',
                '835584094': '2861', '907257604': '10837', '909375715': '791681', '835584087': '2803',
                '907257831': '899515', '907257722': '790696', '813781319': 'MK412', '835584206': '792417',
                '907257620': '2022', '834809332': 'MK181', '909375867': '899510', '813781055': '1327',
                '813781655': '10841', '830226204': 'MK383', '822188118': '10757', '907257820': '792528',
                '835584047': '0983', '813781647': '18564', '907899061': '0908', '834809380': 'MK419',
                '830486499': '4752', '838848694': '0904', '835584214': '792451', '835584263': '792476',
                '830486522': '790700', '907899298': '834929', '828073866': 'SP12-12', '823698215': '1473-6',
                '830226191': 'MK264', '907257748': '791650', '813780885': '1510', '907257593': '1079',
                '907257783': '792262', '838848765': '790689', '835584230': '792462', '813781480': '791091',
                '907899187': '790499', '838848703': '1178', '834809421': 'MK433', '907257731': '790729', '813781521': '7772', '907899315': '870015', '815033637': 'MK404', '907899281': '834923', '907257799': '792433', '835584222': '792459', '835584244': '792468', '815033629': 'MK381', '813781668': 'SP12-9', '830486475': '2863', '838848777': '791655', '813780763': '0363', '907899294': '834928', '838848819': '792531', '835584256': '792472', '813780841': '0345', '907257676': '2904', '813781303': 'MK423-1', '835584184': '791826', '907257780': '791941', '835584240': '792467'}
    try:
        with connection.cursor() as cursor:
                       
            cursor.executemany(INSERT_SKUS_FROM_ID, [(sku, produto_id) for produto_id, sku in id_skus.items()] )
                
            print(f"insert_sku_to_db_database - Skus inseridos com sucesso")
            connection.commit()
                
    except Exception as e:
        connection.rollback()
        print(f"insert_sku_to_db_database - Deu ruim: {e}")
        
#Info de estoque dos produtos
def insert_products_in_batch_database(products):
    COLUMN_MAPPING = {
        
        "id_produto_erp": "id",
        "sku": "codigo",
        "nome": "nome",
        "gtin": "gtin",
        "situacao": "situacao",
        "saldo": "saldo",
        "saldo_reservado": "saldo_reservado",
        "preco": "preco",
        "preco_custo": "preco_custo",
        "preco_custo_medio": "preco_custo_medio",           
            
    }
    
    try:
        columns = ", ".join(COLUMN_MAPPING.keys())
        placeholders = ", ".join(["%s"] * len(COLUMN_MAPPING))
        query = f" INSERT INTO historico_estoque ({columns}) VALUES ({placeholders})"
        
        print(f"insert_products_in_batch_database - Iniciando a inserção no banco\nquery: {query}")
        data_to_insert = []
        
        for product in products:
            row = []
            for column in COLUMN_MAPPING.values():
                row.append(product.get(column))
                  
            data_to_insert.append(row)
            
        
            
            #print(f"LINHA: {row}\nData to insert:{data_to_insert}\n\n")
       # print(f"data_to_insert: {data_to_insert}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            execute_batch(cursor, query, data_to_insert)
            conn.commit()
            print(f"{len(products)} inseridos com sucesso!")
        
        
    except Exception as e:
        print(f"insert_products_in_batch_database - Erro ao inserir os produtos na base de dados: {e}")
        #conn.rollback()
    
    
    
    query = '''
        INSERT INTO 
    ''' 