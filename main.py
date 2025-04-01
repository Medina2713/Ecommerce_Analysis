from api_requests import *
from utils import *
from database import *
from dotenv import load_dotenv
import sys
from logging_config import configure_logging



load_dotenv() # Carrega dados do .env 
#Forma de conexão antiga INICIO
# Cria a conexão com o Banco de dados ---------------------------------------------
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')

connection = psycopg2.connect(
    f'dbname={db_name} '
    f'user={db_user} '
    f'password={db_password} '
    f'host={db_host} '
    f'port={db_port}'
)
#FOrma de conezão antiga FIM ---------------------------
# -----------------------------------------------
#LOGGING
configure_logging()



def teste_connect_db():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT data_emissao, nf, serie FROM vendas LIMIT 10;')
            results = cursor.fetchall()
            for row in results:
                print(row)  
                
def atualiza_dash():
    with get_db_connection() as conn:
        get_all_vendas_utils(conn, 62)
        print(conn)

    print(conn)
    
def update_margin_vendas_fretes_avulsos():
    
    try:
        SELECT_LAST_FRETES_AVULSOS = '''
            SELECT nf, serie, empresa_frete, valor_frete, subsidio
            FROM fretes_avulsos
            ORDER BY id_fretes_avulsos DESC
            LIMIT 20; 
        '''
        update_fretes_avulsos = '''
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
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_LAST_FRETES_AVULSOS)
            fretes = cursor.fetchall() 
           # print(f"10 últimos fretes avulsos: {fretes}")
            for nf, serie, empresa_frete, valor_frete, subsidio in fretes:
                print(f"nf: {nf} - serie: {serie} - empresa: {empresa_frete} - valor frete: {valor_frete} - subsidio: {subsidio}")
                update_frete_avulso(conn, valor_frete, subsidio, empresa_frete, nf, serie)
                #cursor.execute(update,(valor_frete, subsidio, empresa_frete, nf, serie))
                #cursor.execute(UPDATE_PISCOFINS,(nf, serie))
                #cursor.execute(UPDATE_MARGIN,(nf, serie))
                conn.commit()
    except Exception as e:
        connection.rollback()
        print(f"Update de margem fracassado erro: {e}")
        

#get_products_stock_info()