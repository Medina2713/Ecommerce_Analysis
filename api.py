from flask import Flask, jsonify, render_template, request, abort
from main import *
from database import *
from utils import *
import logging
#from flask_cors import CORS
from collections import defaultdict
from dotenv import load_dotenv
import os
import ipaddress

load_dotenv()
ALLOWED_IPS = os.getenv('ALLOWED_IPS','').split(',')

ALLOWED_NETWORKS = [
    ipaddress.ip_network('187.19.17.0/24'),
    ipaddress.ip_network('191.177.187.0/24'),
    ipaddress.ip_network('177.126.235.0/24'),
    ipaddress.ip_network('177.126.233.0/24'),
    #ipaddress.ip_network('145.223.29.0/24')
    ipaddress.ip_network('127.0.0.0/24')
]

def is_ip_allowed(ip):
    try:
        for network in ALLOWED_NETWORKS:
            if ipaddress.ip_address(ip) in network:
                return True
        return False
    except Exception as e:
        print(f"Erro ao validar o IP: {e}") 
        
app = Flask(__name__)
#CORS(app)


dominios = set()

@app.before_request
def limit_remote_network():
    client_ip = request.remote_addr
    if is_ip_allowed(client_ip):
        print(f"IP {client_ip} permitido!")
        return
    print(f"IP {client_ip} com acesso negado")
    abort(403)

'''@app.before_request
def before_request():
    if 'X-Forwarded-Prefix' in request.headers:
        request.path = request.headers['X-Forwarded-Prefix'] + request.path '''
        
'''@app.before_request
def limit_remote_addr():
    client_ip =request.remote_addr
    if client_ip not in ALLOWED_IPS:
        abort(403)'''


@app.before_request
def log_origin():
    referer = request.headers.get('Referer')
    if referer:
        dominios.add(referer)
        print(f"Requisição recebida do domínio: {referer}")

@app.route('/dominios')
def listar_dominios():
    return {"dominios": list(dominios)}

executando = False

@app.route('/')
def index():
    # Rendeiriza a página HTML
    return render_template('index.html')

@app.route('/fretes_avulsos')
def fretes_avulsos():
    # Rendeiriza a página HTML
    return render_template('fretes_avulsos.html')

@app.route('/vendas')
def vendas():
    return render_template('vendas.html')

@app.route('/crud_geral')
def crud_geral():
    return render_template('crud_geral.html')



@app.route('/get_vendas', methods=['GET'])  
def get_vendas_api(): 
    '''Melhorias Futuras:
        Tempo Limite: Use timeout para evitar que a função fique bloqueada indefinidamente.
        Controle mais robusto: Substitua o controle global por sistemas mais avançados, como queues (por exemplo, Celery).
    '''
    global executando

    if executando:
        return jsonify({'mensagem': f'A função já está em execução. Aguarde!'}), 429
    
    try:
        executando = True

        # Chama a função do backend
        with get_db_connection() as conn:
            resultado = get_all_vendas_utils(conn,69)

    
        # Retorna o resultado em formato JSON
        return jsonify({'mensagem': 'Vendas puxadas com sucesso', 'resultado': resultado})
    
    except Exception as e:
        return jsonify({'mensagem': 'Erro interno', 'detalhes': str(e)}), 500
    
    finally:
        executando = False
        
# Fretes_avulsos
@app.route('/add-record-frete-avulso', methods=['POST'])
def add_record():
    try:
        # Pega os dados do request
        data = request.json
        num_nf = data.get('numNF')
        serie_nf = data.get('serieNF')
        id_nf = data.get('ID')
        empresa = data.get('empresa')
        valor_frete = float(data.get('valorFrete'))
        subsidio = float(data.get('subsidio'))
        
        with get_db_connection() as conn:

            # Validações adicionais, se necessário
            if not (num_nf or id_nf):  # Pelo menos um campo deve ser preenchido
                return jsonify({"error": "Campos obrigatórios estão faltando."}), 400
            
            if check_record_exists(id_nf, num_nf, serie_nf, conn):
                return jsonify({"error": "Nota fiscal já cadastrada."}), 400

            # Insere os dados no banco
            new_id = insert_record_front_db(num_nf, serie_nf, id_nf, empresa, valor_frete, subsidio, conn)

            if new_id:
                return jsonify({"message": "Registro adicionado com sucesso!", "id": new_id}), 201
            else:
                return jsonify({"error": "Erro ao adicionar registro."}), 500
    except Exception as e:
        print("Erro na API:", e)
        return jsonify({"error": "Erro interno do servidor."}), 500

@app.route('/get_last_fretes_avulsos', methods=['GET'])
def get_last_fretes_avulsos():
    # Substitua pelo nome real da tabela e colunas
    with get_db_connection() as conn:    
        records = get_fretes_avulsos_db(conn)
        # Converta os registros para JSON
        result = [
            {
                "id": row[0],
                "nf": row[1],
                "serie": row[2],
                "empresa": row[3],
                "subsidio": row[5],
                "valor_frete": row[4],
            }
            for row in records
        ]
        
    
    
    return jsonify(result)

@app.route('/get_frete_avulso', methods=['GET'])
def get_frete_avulso():
    try:
         # Obter parâmetros da URL
        num_nf = request.args.get('numNF')
        serie_nf = request.args.get('serieNF')
        
        print(f"Parâmetros recebidos: numNF={num_nf}, serieNF={serie_nf}")

        # Verificar se os parâmetros foram fornecidos
        if not num_nf or not serie_nf:
            return jsonify({"error": "Parâmetros 'numNF' e 'serieNF' são obrigatórios"}), 400
        
        with get_db_connection() as conn:    
            record = select_frete_avulso(num_nf, serie_nf, conn)
        if record:
            frete_avulso = {
                "success": True,
                "id": record[7],
                "nf": record[1],
                "serie": record[2],
                "empresa": record[3],
                "subsidio": record[5],
                "valor_frete": record[4],
            }
            print(f"get_frete_avulso API: {frete_avulso}")
            return jsonify(frete_avulso)
        else:
            print("Nenhum registro encontrado.")
            return jsonify({"message": "Nenhum registro encontrado."}), 404
    except Exception as e:
        print(f"API get_frete_avulso - Erro: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

@app.route('/salvarFreteAvulso', methods=['POST'])
def save_change_frete_avulso():
    try:
        data = request.json
        print(f"Dados recebidos: {data}")
        num_nf = data['numNF']
        serie_nf = data['serieNF']
        valor_frete = data['valorFrete']
        subsidio = data['subsidio']
        empresa = data['empresa']
        with get_db_connection() as conn:
            update_frete_avulso(conn, valor_frete, subsidio, empresa, num_nf, serie_nf)
        return jsonify(success=True)
    except Exception as e:
        print(f"save_change_frete_avulso - Erro ao salvar alterações: {e}")
        return jsonify(success=False, error=str(e)), 500
#Vendas

@app.route('/busca_vendas', methods=['GET'])
def busca_vendas():
    # Substitua pelo nome real da tabela e colunas
    with get_db_connection() as conn:
        records = get_vendas_db(conn)
    
    # Converta os registros para JSON
    result = [
        {
            
            "nf": row[0],
            "serie": row[1],
            "loja": row[2],
            "valor_nf": row[3],
            "comissao": row[4],
            "margem_mktp": row[5],
            "subsidio": row[6],
            "desconto": row[7],
            "frete_mktp": row[8]
        }
        for row in records
    ]
    
    print(jsonify(result))
    
    return jsonify(result)

@app.route('/buscar_venda', methods=['GET'])
def buscar_venda():
    try:
         # Obter parâmetros da URL
        num_nf = request.args.get('numNF')
        serie_nf = request.args.get('serieNF')
        
        print(f" buscar_venda - Parâmetros recebidos: numNF={num_nf}, serieNF={serie_nf}")

        # Verificar se os parâmetros foram fornecidos
        if not num_nf or not serie_nf:
            return jsonify({"error": "Parâmetros 'numNF' e 'serieNF' são obrigatórios"}), 400
        
        with get_db_connection() as conn:
            record = select_venda(num_nf, serie_nf, conn)
        if record:
            venda = {
                "success": True,
                
                "nf": record[0],
                "serie": record[1],
                "loja": record[2],
                "valor_nf": record[3],
                "comissao": record[4],
                "margem_mktp": record[5],
                "subsidio": record[6],
                "desconto": record[7],
                "frete_mktp": record[8]
            }
            #print(f"get_frete_avulso API: {frete_avulso}")
            return jsonify(venda)
        else:
            print("Nenhum registro encontrado.")
            return jsonify({"message": "Nenhum registro encontrado."}), 404
    except Exception as e:
        print(f"API busca_venda - Erro: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

@app.route('/salvar_venda', methods=['POST'])
def salvar_venda():
    try:
        data = request.json
        print(f"Dados recebidos: {data}")
        num_nf = data['numNF']
        serie_nf = data['serieNF']
        loja = data['loja']
        valor_nf = data['valor_nf']
        comissao = data['comissao']
        margem_mktp = data['margem_mktp']
        frete_mktp = data['frete_mktp']
        subsidio = data['subsidio']
        desconto = data['desconto']
        with get_db_connection() as conn:
            update_vendas(conn, comissao, margem_mktp, subsidio, desconto, frete_mktp, num_nf, serie_nf)
        return jsonify(success=True)
    except Exception as e:
        print(f"salvar_venda - Erro ao salvar alterações: {e}")
        return jsonify(success=False, error=str(e)), 500
    
@app.route('/excluir_venda', methods=['DELETE'])
def excluir_venda():
    try:
        '''data = request.get_json()
        num_nf = data.get('numNF')
        serie_nf = data.get('serieNF') Forma de receber um JSON'''
        num_nf = request.args.get('numNF')
        serie_nf = request.args.get('serieNF')
        if num_nf and serie_nf:
           excluido = exclude_venda(num_nf,serie_nf)
           if excluido:
               return jsonify({
                   'success': True,
                   'message': f'Venda da NF {num_nf} serie {serie_nf} excluida com sucesso!'
               }), 200
           else:
               return jsonify({
                   'success': False,
                   'message': f'Erro ao excluir a venda: Problema no Banco'
               }), 400
        else:
            return jsonify({
                   'success': False,
                   'message': f'Número e série obrigatórios!'
               }), 400
    except Exception as e:
        
        print(e)
        return jsonify({
                   'success': False,
                   'message': f'Erro ao excluir a venda: {e}'
               }), 400
    
@app.route('/teste_conexao')
def teste_conn():
    return jsonify({
                   'success': True,
                   'message': f'Teste bem sucedido'
               }), 200    
# Inicia o servidor
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)