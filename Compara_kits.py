from collections import defaultdict, Counter
import psycopg2

def verificar_venda_kit(venda, connection):
    """
    Verifica se a venda corresponde a algum kit definido no banco de dados.

    Args:
        venda (dict): Dicionário com os itens da venda.
        connection (psycopg2.connection): Conexão com o banco de dados PostgreSQL.

    Returns:
        int or None: ID do kit correspondente, se encontrado. Caso contrário, None.
    """
    try:
        with connection.cursor() as cursor:
            # Consulta os kits e seus itens no banco de dados
            query_kits = '''
            SELECT k.id_kit, ik.id_item_kit_erp, ik.quantidade
            FROM kits k
            JOIN itens_kits ik ON k.id_kit = ik.id_kit;
            '''
            cursor.execute(query_kits)
            kits = cursor.fetchall()

            # Organiza os itens dos kits em um dicionário por ID do kit
            kits_dict = defaultdict(list)
            for id_kit, id_item_kit_erp, quantidade in kits:
                kits_dict[id_kit].append({
                    "id_item_kit_erp": id_item_kit_erp,
                    "quantidade": quantidade
                })

            # Converte os itens da venda para o formato esperado
            venda_itens = [
                {"id_item_kit_erp": details['produto_id'], "quantidade": details['quantidade']}
                for key, details in venda.items()
                if isinstance(details, dict)  # Ignorar campos como 'quantidade_total'
            ]

            # Verifica se a venda corresponde a algum kit
            for id_kit, itens_kit in kits_dict.items():
                if comparar_itens(itens_kit, venda_itens):
                    return id_kit  # Retorna o ID do kit encontrado

            return None  # Se nenhum kit corresponder, retorna None

    except Exception as e:
        print(f"Erro ao verificar kits: {e}")
        return None


def comparar_itens(itens_kit, itens_venda):
    """
    Compara os itens de um kit com os itens de uma venda.

    Args:
        itens_kit (list): Lista de itens do kit (cada item é um dicionário com ID e quantidade).
        itens_venda (list): Lista de itens da venda (mesmo formato que os itens do kit).

    Returns:
        bool: True se a venda contém os itens e as quantidades do kit, False caso contrário.
    """
    # Cria contadores para os itens do kit e da venda
    kit_counter = Counter({item["id_item_kit_erp"]: item["quantidade"] for item in itens_kit})
    venda_counter = Counter({item["id_item_kit_erp"]: item["quantidade"] for item in itens_venda})
    
    print(f"comparar_itens - kits: {kit_counter}\nVenda: {venda_counter}")

    # Verifica se todos os itens e quantidades do kit estão na venda
    for id_item, quantidade in kit_counter.items():
        if venda_counter[id_item] < quantidade:
            return False
    return True


