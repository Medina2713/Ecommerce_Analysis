import requests
import time
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

rest = 2

# Pegando o token da variável de ambiente
token = os.getenv('TINY_API_TOKEN')
if not token:
    raise ValueError("Token não encontrado. Verifique o arquivo '.env'.")

def get_nf_by_id_api(id): #Faz uma requisição da NF detalhada pelo ID no Tiny
    url = 'https://api.tiny.com.br/api2/nota.fiscal.obter.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'id': id
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    
    return {
        'id_nf_request': id,
        'data': data
            }

def get_nfs_saida_api(pagina): #Faz uma requisição de todas as NFs resumidas cadastradas no Tiny
    url = 'https://api.tiny.com.br/api2/notas.fiscais.pesquisa.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'tipoNota': 'S',
        'dataInicial': '21/03/2024',# PND - Precisa tirar a data inicial setada. Deverá ser passada a data como parâmetro.
        'pagina' : pagina
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
       
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    
    return data

def get_xml_nf_by_id_api(id_tiny):
    url = 'https://api.tiny.com.br/api2/nota.fiscal.obter.xml.php'


    
    params = {
        'token': token,
        'id' : id_tiny
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        xml_data = response.text
        #print(f" XML - {response.text}")

        try:
            #Parseando o XML
            tree = ET.ElementTree(ET.fromstring(xml_data))
            return tree
        except ET.ParseError as e:
            print(f"Erro ao parsear o XML: {e}")
            return None
    else:
        print(f"Erro na requisição: {response.status_code}")
        return None
    
 
    time.sleep(rest)
    
def get_product_by_id_api(id_tiny): #Retorna o JSON com os dados do produto
    url = 'https://api.tiny.com.br/api2/produto.obter.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'id': id_tiny
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    #print(f"get_product_by_id_api - {data}")
    return data

def get_product_by_EAN(ean):
    url = 'https://api.tiny.com.br/api2/produtos.pesquisa.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'pesquisa': '',
        'gtin': ean
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    
    return data

def get_products_kits_api(pagina): #Retorna o JSON com os dados do produto
    url = 'https://api.tiny.com.br/api2/produtos.pesquisa.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'pesquisa': 'Kit ',
        'pagina': pagina
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    #print(f"get_product_by_id_api - {data}")
    return data

def get_products_api(pagina): #Retorna o JSON com os dados do produto
    url = 'https://api.tiny.com.br/api2/produtos.pesquisa.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'pesquisa': '',
        'pagina': pagina
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    #print(f"get_product_by_id_api - {data}")
    return data

def get_notas_entrada_api(data, pagina):
    url = 'https://api.tiny.com.br/api2/notas.fiscais.pesquisa.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'tipoNota': 'E',
        'dataInicial': data,
        'pagina' : pagina
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
       
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    
    return data

def get_pedido_by_id_api_requests(id):
    url = 'https://api.tiny.com.br/api2/pedido.obter.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'id': id
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
       
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    
    return data

def get_product_stock_by_id(id_tiny):
    url = 'https://api.tiny.com.br/api2/produto.obter.estoque.php'


    
    params = {
        'token': token,
        'formato': 'json',
        'id': id_tiny
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    
    time.sleep(rest)
    #print(f"get_product_by_id_api - {data}")
    return data