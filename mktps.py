#from api_requests import *

 
from database import *


def get_marketplace_mktps(nf_dict,item_dict,connection, kit):
    num_pedido = str(nf_dict.get('pedido_ecommerce', 'ERRO'))
    prefix =  num_pedido[:2]
    
    print(f"get_marketplace_mktps - Antes de selecionar Pedido: {num_pedido}\nPrefixo:{prefix}\nNF: {nf_dict.get('nf', 'Erro')}")
    if prefix == '20':
        return get_comissao_ML_mktps(nf_dict,item_dict, connection, kit)
    elif prefix == '24':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
         
        return get_comissao_SHP_mktps(nf_dict,item_dict, connection, kit)
    elif prefix == '25':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
         
        return get_comissao_SHP_mktps(nf_dict,item_dict, connection, kit)
    elif prefix == '26':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
         
        return get_comissao_SHP_mktps(nf_dict,item_dict, connection, kit)
    elif prefix == '27':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
         
        return get_comissao_SHP_mktps(nf_dict,item_dict, connection, kit)
    elif prefix == '28':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
         
        return get_comissao_SHP_mktps(nf_dict,item_dict, connection, kit)  
    elif prefix == '70':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}\n Marketplace: AMAZON")
        return get_comissao_AMZ_mktps(nf_dict,item_dict,connection)
    
    elif prefix == 'Lo':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
        return get_comissao_AMR_mktps(nf_dict,item_dict,connection)
    elif prefix == 'Sh':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
        return get_comissao_AMR_mktps(nf_dict,item_dict,connection)
    elif prefix == 'Am':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
        return get_comissao_AMR_mktps(nf_dict,item_dict,connection)
    elif prefix == 'LU':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
        return get_comissao_MGL_mktps(nf_dict,item_dict,connection, kit)
    elif prefix == '10':
        print(f"get_marketplace_mktps - Numero do pedido: {num_pedido}\nNF: {nf_dict.get('nf', 'Erro')}")
        return get_comissao_exceptions_mktps(nf_dict,item_dict, connection, kit)
    
    return 0
    
    
    

# Mercado Livre inicio --------------------
def get_comissao_ML_mktps(nf_dict, item_dict, connection, kit):
    data_emissao = nf_dict.get('data_emissao', 'ERRO - get_comissao_ML_mktps')
    serie = nf_dict.get('serie', 'ERRO - get_comissao_ML_mktps')
    try:
        kit_aplicado = False
        for item_key, item_data in item_dict.items():
            if isinstance(item_data, dict):  # Verifica se item_data é um dicionário
                categoria = item_data.get('categoria', 'ERRO')
                valor_unitario = item_data.get('valor_unitario', 0)
                quantidade = item_data.get('quantidade', 0)
                valor_total = item_data.get('valor_total', 0)
                
            
                #print(f"get_comissao_ML_mktps - item_key analisada: {item_key}\n item Data: { item_data}")

                if serie == '4': 
                    if 'bateria' in categoria.lower():
                        categoria = 'Bateria'
                        taxas = select_taxa_mktp_from_db_database('Full ML Baterias', data_emissao, connection)

                        if valor_unitario < 79.00:
                            if kit > 0:
                                if not kit_aplicado:
                                    comissao = (valor_total * taxas.get('taxa', 0)) + (taxas.get('acrescimo', 0) * kit)
                                else:
                                    comissao = (valor_total * taxas.get('taxa', 0))
                            else:
                                comissao = (valor_total * taxas.get('taxa', 0)) + (quantidade * taxas.get('acrescimo', 0))
                        else:
                            comissao = valor_total * taxas.get('taxa', 0)

                    else:
                        categoria = 'Brinquedo'
                        taxas = select_taxa_mktp_from_db_database('Full ML Brinquedos', data_emissao, connection)
                        taxa_comissao = taxas.get('taxa', 0.0)
                        acrescimo = taxas.get('acrescimo', 0.0)

                        if valor_unitario < 79:
                            data_emissao_dt = datetime.strptime(data_emissao, '%Y-%m-%d')
                            data_referencia = datetime(2025, 1, 16)
                            if data_emissao_dt >= data_referencia:
                                if 0 < valor_unitario < 29:
                                    acrescimo = 6.50
                                elif 29 <= valor_unitario < 50:
                                    acrescimo = 6.50
                                elif 50 <= valor_unitario < 79:
                                    acrescimo = 6.75
                            print(f"Acréscimos depois dos ifs e antes de aplicar {acrescimo}")
                            if kit > 0:
                                if not kit_aplicado:
                                    comissao = (valor_total * taxa_comissao) + (acrescimo * kit)
                                    kit_aplicado = True
                                else:
                                    comissao = (valor_total * taxa_comissao)
                            else:
                                print(f"ACréscimo de {acrescimo}")
                                comissao = (valor_total * taxa_comissao) + (quantidade * acrescimo)
                        else:
                            comissao = valor_total * taxa_comissao
                    print(f"\nItem_key {item_key}\nComissao{comissao}\nAcréscimo {acrescimo}")
                    item_data['comissao_mktp'] = float(comissao)

                else:
                    if 'bateria' in categoria.lower():
                        categoria = 'Bateria'
                        taxas = select_taxa_mktp_from_db_database('Mercado Livre Baterias', data_emissao, connection)
                        taxa_comissao = taxas.get('taxa', 0.0)
                        acrescimo = taxas.get('acrescimo', 0.0)

                        if valor_unitario < 79:
                            data_emissao_dt = datetime.strptime(data_emissao, '%Y-%m-%d')
                            data_referencia = datetime(2025, 1, 16)
                            if data_emissao_dt >= data_referencia:
                                if 0 < valor_unitario <= 29:
                                    acrescimo = 6.25
                                elif 29 < valor_unitario <= 50:
                                    acrescimo = 6.50
                                elif 50 < valor_unitario <= 79:
                                    acrescimo = 6.75

                            if kit:
                                if not kit_aplicado:
                                    comissao = (valor_total * taxa_comissao) + acrescimo
                                    kit_aplicado = True
                                else:
                                    comissao = (valor_total * taxa_comissao)
                            else:
                                comissao = valor_total * taxa_comissao + (quantidade * acrescimo)

                        else:
                            comissao = valor_total * taxa_comissao

                    else:
                        categoria = 'Brinquedo'
                        taxas = select_taxa_mktp_from_db_database('Mercado Livre Brinquedos', data_emissao, connection)
                        taxa_comissao = taxas.get('taxa', 0.0)
                        acrescimo = taxas.get('acrescimo', 0.0)

                        if valor_unitario < 79:
                            data_emissao_dt = datetime.strptime(data_emissao, '%Y-%m-%d')
                            data_referencia = datetime(2025, 1, 16)
                            if data_emissao_dt >= data_referencia:
                                if 0 < valor_unitario <= 29:
                                    acrescimo = 6.50
                                elif 29 < valor_unitario <= 50:
                                    acrescimo = 6.50
                                elif 50 < valor_unitario <= 79:
                                    acrescimo = 6.75

                            if kit > 0:
                                if not kit_aplicado:
                                    print(f"Vai aplicar taxas do kit kit_aplicado false")
                                    comissao = (valor_total * taxa_comissao) + (acrescimo * kit)
                                    kit_aplicado = True
                                else:
                                    print(f"Aplica comissão sem acréscimo")
                                    comissao = (valor_total * taxa_comissao)
                            else:
                                print(f"Produtos não fazem parte de Kit")
                                comissao = valor_total * taxa_comissao + (quantidade * acrescimo)
                        else:
                            print(f"Sem acréscimo pelo valor do pedido")
                            comissao = valor_total * taxa_comissao

                    print(f"\nItem_key {item_key}\n Valor Total {valor_total}\nComissao {comissao}\nAcréscimo {acrescimo}\nTaxa de comissão {taxa_comissao}")
                    item_data['comissao_mktp'] = float(comissao)

            else:
                print(f"Item não é um dicionário")
                pass
        return item_dict

    except Exception as e:
        print(f"Erro ao paresear as comissões: {e}")

# Mercado Livre fim -----------------------

# SHOPEE ------------------------
def get_comissao_SHP_mktps(nf_dict, item_dict, connection, kit):
    try:
        data_emissao = nf_dict.get('data_emissao', 'ERRO - get_comissao_ML_mktps')
        kit_aplicado = False
        
        for item_key, item_data in item_dict.items():
            
            if not isinstance(item_data, dict):
               # print(f"Erro: item_data não é um dicionário. Valor recebido: {item_data}")
                continue  # Ignora este item e passa para o próximo
            quantidade = item_data.get('quantidade',0)
            valor_total = item_data.get('valor_total',0)
            
            taxas = select_taxa_mktp_from_db_database('Shopee',data_emissao,connection)
            taxa_comissao = taxas.get('taxa',0.0)
            acrescimo = taxas.get('acrescimo',0.0)
            if kit > 0:
                
                if kit_aplicado == False:
                    comissao = valor_total * taxa_comissao + (acrescimo * kit)
                    kit_aplicado = True
                    
                elif kit_aplicado:
                    comissao = valor_total * taxa_comissao 
                        
                print(f"get_comissao_SHP_mktps - KIT SHOPEE Comissão total: {comissao}\n Comissão: {valor_total*taxa_comissao}\nValor Total:{valor_total}  Acréscimo: {acrescimo * kit}\n Quantidade de kits: {kit} ")
            else:    
                comissao = valor_total * taxa_comissao + (acrescimo * quantidade)
           # print(f"get_comissao_SHP_mktps - Comissão: {comissao}")
            item_data['comissao_mktp'] = float(comissao)
            #print(f"get_comissao_SHP_mktps - item_data comissao: {item_data['comissao_mktp']}")
            #print(f"get_comissao_SHP_mktps - Item_dict: {item_dict}")
        #print(f"get_comissao_SHP_mktps - Item_dict antes do retorno: {item_dict}")   
        return item_dict
    except Exception as e:
        print(f"get_comissao_SHP-MKTPs - Erro ao atualizar o item dict: {e}")     
          

#MAGALU -------------------------

def get_comissao_MGL_mktps(nf_dict, item_dict, connection, kit):
    
    try:
        data_emissao = nf_dict.get('data_emissao', 'ERRO - get_comissao_ML_mktps')
        serie = nf_dict.get('serie','ERRO - get_comissao_ML_mktps')
        kit_aplicado = False
        
        for item_key, item_data in item_dict.items():
            
            if not isinstance(item_data, dict):
               # print(f"Erro: item_data não é um dicionário. Valor recebido: {item_data}")
                continue  # Ignora este item e passa para o próximo
            
                
            quantidade = item_data.get('quantidade',0)
            valor_total = item_data.get('valor_total',0)
            
            taxas = select_taxa_mktp_from_db_database('Magalu',data_emissao,connection)
            taxa_comissao = taxas.get('taxa',0.0)
            acrescimo = taxas.get('acrescimo',0.0)
            if kit > 0:
                
                if kit_aplicado == False:
                    comissao = valor_total * taxa_comissao + (acrescimo * kit)
                    kit_aplicado = True
                    
                elif kit_aplicado:
                    comissao = valor_total * taxa_comissao 
                        
                print(f"get_comissao_MGL_mktps - KIT MGL Comissão total: {comissao}\n Comissão: {valor_total*taxa_comissao}\nValor Total:{valor_total}  Acréscimo: {acrescimo * kit}\n Quantidade de kits: {kit} ")
            else:    
                comissao = valor_total * taxa_comissao + (acrescimo * quantidade)
            
            #print(f"get_comissao_MGL_mktps - Comissão: {comissao}")
            item_data['comissao_mktp'] = float(comissao)
            #print(f"get_comissao_MGL_mktps - item_data comissao: {item_data['comissao_mktp']}")
            #print(f"get_comissao_MGL_mktps - Item_dict: {item_dict}")
            #print(f"get_comissao_MGL_mktps - Item_dict antes do retorno: {item_dict}")   
        return item_dict
    except Exception as e:
        print(f"get_comissao_SHP-MKTPs - Erro ao atualizar o item dict: {e}")  
        
# Americanas --------------------------------

def get_comissao_AMR_mktps(nf_dict, item_dict, connection):
    
    try:
        data_emissao = nf_dict.get('data_emissao', 'ERRO - get_comissao_AMR_mktps')
        
        for item_key, item_data in item_dict.items():
            
            if not isinstance(item_data, dict):
                #print(f"Erro: item_data não é um dicionário. Valor recebido: {item_data}")
                continue  # Ignora este item e passa para o próximo
            quantidade = item_data.get('quantidade',0)
            valor_total = item_data.get('valor_total',0)
                
            taxas = select_taxa_mktp_from_db_database('Americanas',data_emissao,connection)
            taxa_comissao = taxas.get('taxa',0.0)
            acrescimo = taxas.get('acrescimo',0.0)
            comissao = (valor_total * taxa_comissao) + acrescimo
            #print(f"get_comissao_AMR_mktps - Comissão: {comissao}")
            item_data['comissao_mktp'] = float(comissao)
            #print(f"get_comissao_AMR_mktps - item_data comissao: {item_data['comissao_mktp']}")
            #print(f"get_comissao_AMR_mktps - Item_dict: {item_dict}")
        #print(f"get_comissao_AMR_mktps - Item_dict antes do retorno: {item_dict}")   
        return item_dict
    except Exception as e:
        print(f"get_comissao_AMR-MKTPs - Erro ao atualizar o item dict: {e}") 
        
def get_comissao_AMZ_mktps(nf_dict, item_dict, connection):
    
    try:
        #print('get_comissao_AMZ_mktps - Inicia estimativa AMAZON')
        data_emissao = nf_dict.get('data_emissao', 'ERRO - get_comissao_AMZ_mktps')
        cubagem = item_dict['cubagem_total']
        #print(f"Verificando o ITEM dict antes: {item_dict}")
        
        for item_key, item_value in item_dict.items():
            
            if not isinstance(item_value, dict):
               # print(f"Erro: item_value não é um dicionário. Valor recebido: {item_value}")
                continue  # Ignora este item e passa para o próximo
            quantidade = item_value.get('quantidade',0)
            valor_total = item_value.get('valor_total',0)
                
            taxas = select_taxa_mktp_from_db_database('Amazon',data_emissao,connection)
            taxa_comissao = taxas.get('taxa',0.0)
            
            comissao = (valor_total * taxa_comissao)
            #print(f"get_comissao_AMZ_mktps - Comissão: {comissao}")
            item_value['comissao_mktp'] = float(comissao)
            #print(f"get_comissao_AMZ_mktps - item_value comissao: {item_value['comissao_mktp']}")
            #print(f"get_comissao_AMZ_mktps - item_value: {item_value}")
            #print(f"get_comissao_AMZ_mktps - item_value antes do retorno: {item_value}")
        '''if not isinstance(item_value, dict):
                    print(f"Skipping {item_key} porque não é um dicionário. Tipo atual: {type(item_value)}")
                    if item_key == 'frete_mktp':
                        #item_value['frete_mktp']
                        frete = get_frete_amazon(cubagem)
                        print(f"FRETE DEPOIS DA FUNÇÂO: {item_value['frete_mktp']}")'''
        valor_unitario = valor_total/quantidade   # Inicio gambiarra frete Amazon                
        if valor_unitario < 79:
            if valor_unitario > 30:
                frete_mktp = quantidade * 8
            if valor_unitario < 30:
                frete_mktp = quantidade * 4.5 # Final gambiarra frete Amazon
        else:
            frete_mktp = get_frete_amazon(cubagem) #
        item_dict['frete_mktp'] = frete_mktp
        #print(frete_mktp)
        #print(f"get_comissao_AMZ_mktps - Frete AMZ calculado: {item_dict['frete_mktp']}")  
        return item_dict
    except Exception as e:
        print(f"get_comissao_AMZ-MKTPs - Erro ao atualizar o item dict: {e}")
        
def get_frete_amazon(cubagem):
    try:
        #print(f"get_frete_amazon - Calculando frete.\nCubagem = {cubagem}")
        intervalos_peso = [0, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        precos = [18.95, 19.45, 21.45, 22.45, 23.45, 24.95, 27.95, 34.95, 37.45, 38.45, 46.95, 63.95]
        
        for i in range(len(intervalos_peso) - 1):
            if intervalos_peso[i] <= cubagem < intervalos_peso[i+1]:
                #print(f"get_frete_amazon - Frete calculado: {precos[i]}")
                return precos[i]
            
        if cubagem > 10.00:
            excesso = cubagem - 10
           # print(f"get_frete_amazon - Frete calculado: {precos[-1] +(excesso * 4.00)}")
            return precos[-1] +(excesso * 4.00)
        
    except Exception as e:
        print(f"get_frete_amazon - Erro ao calcular o frete Amazon: {e}") 

def get_comissao_exceptions_mktps(nf_dict, item_dict, connection, kit):
    try:
        data_emissao = nf_dict.get('data_emissao', 'ERRO - get_comissao_exceptions_mktps')
        kit_aplicado = False
        
        for item_key, item_data in item_dict.items():
            
            if not isinstance(item_data, dict):
               # print(f"Erro: item_data não é um dicionário. Valor recebido: {item_data}")
                continue  # Ignora este item e passa para o próximo
            quantidade = item_data.get('quantidade',0)
            valor_total = item_data.get('valor_total',0)
            
            
            taxa_comissao = 0.10
            acrescimo = 0
            if kit:
                if kit_aplicado == False:
                    comissao = valor_total * taxa_comissao + (acrescimo)
                    kit_aplicado = True
                else:
                    comissao = valor_total * taxa_comissao 
                    
                print(f"get_comissao_exceptions_mktps - Acréscimo considerado apenas uma vez por ser um KIT\nComissão normal: {valor_total * taxa_comissao + (acrescimo * quantidade)}\nComissão kit: {valor_total * taxa_comissao + (acrescimo)}")
            else:    
                comissao = valor_total * taxa_comissao + (acrescimo * quantidade)
           # print(f"get_comissao_SHP_mktps - Comissão: {comissao}")
            item_data['comissao_mktp'] = float(comissao)
            #print(f"get_comissao_SHP_mktps - item_data comissao: {item_data['comissao_mktp']}")
            #print(f"get_comissao_SHP_mktps - Item_dict: {item_dict}")
        #print(f"get_comissao_SHP_mktps - Item_dict antes do retorno: {item_dict}")   
        return item_dict
    except Exception as e:
        print(f"get_comissao_exceptions_mktps - Erro ao atualizar o item dict: {e}")  