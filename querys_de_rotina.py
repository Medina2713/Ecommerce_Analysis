#Retorna os produtos com mais de im nome em venda_produtos e quantidade de nomes
SELECT_NAME_DUPLICATES_VENDA_PRODUTOS = '''
SELECT produto_id, COUNT(DISTINCT nome) AS quantidade_nomes_diferentes
FROM venda_produtos
GROUP BY produto_id
HAVING COUNT(DISTINCT nome) > 1
ORDER BY quantidade_nomes_diferentes DESC;
'''

#Renomeia os produtos com nomes duplicados para o nome mais recente
UPDATE_DUPLICATE_NAMES_VENDA_PRODUTOS = '''
UPDATE venda_produtos vp
SET nome = (
    SELECT nome 
    FROM venda_produtos vp1
    WHERE vp1.produto_id = vp.produto_id
    ORDER BY vp1.venda_produtos_id DESC
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1 
    FROM venda_produtos vp2
    WHERE vp2.produto_id = vp.produto_id
    AND vp2.nome <> vp.nome
);
'''