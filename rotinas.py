from main import *
import logging
from database import *
from querys_de_rotina import UPDATE_DUPLICATE_NAMES_VENDA_PRODUTOS, SELECT_NAME_DUPLICATES_VENDA_PRODUTOS
logging.basicConfig(filename='/root/Documents/API/API_PYTHON/log_rotinas.log', level=logging.INFO)



if __name__ == "__main__":
    logging.info("Execução iniciada.")
    inicio = datetime.now()
    print(f"Inicio da execução da rotina: {inicio}")
    with get_db_connection() as conn:
        
        get_all_kits_to_DB(conn)
        time.sleep(60)
    get_all_products_stock_info()
    
    print(f"Inicio da rotina: {inicio}\nFinal da rotina {datetime.now()}")
        
        
        
    
    logging.info("Execução finalizada.")