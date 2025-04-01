# Sistema de BI para E-commerce (Dashboard + Backend Integrado)

Projeto completo para análise de dados de e-commerce, evoluindo de rotinas manuais no Google Apps Script para uma infraestrutura automatizada com:

- Python (ETL e API Flask)
- PostgreSQL (cálculos de margens)
- Grafana (visualização)
- Frontend HTML/CSS/JS puro
- NGINX como proxy reverso para segurança e controle de acesso.
- Servidor de linha de comando Ubuntu 24.04

## 📋 Funcionalidades

### 🧠 Núcleo de Processamento
- Consumo da API do ERP com autenticação OAuth
- Cálculo automático de:
  - Margens líquidas/brutas
  - Taxas por marketplace (Mercado Livre, Shopee, etc)
  - Impostos federais/estaduais
- Sincronização incremental de vendas

### 📊 Dashboard (Grafana)
![image](https://github.com/user-attachments/assets/708685de-a891-48bf-aad8-463bd3919e83)

Demonstração Dashboard <https://youtu.be/qJEXVIHbxAc>
- Visualização em tempo real de:
  - Performance por canal
  - Comparativo de margens
  - Análise de indicadores por múiltiplas categorias
- Filtros de visualização personalizados (Produto, categoria, Fornecedor, loja, etc)

### Front-end
Demonsração Front <https://youtu.be/Z0kY-Ym2kgY>
- Interface para atualização de vendas utilizando a API do ERP
- Alteração e exclusão de vendas




# Glossário


Principais ferramentas utilizadas



## Comandos PSQL para manipulação do DB (Win 10):

### limpar banco e reiniciar identidades
```sql
TRUNCATE TABLE venda_produtos, vendas RESTART IDENTITY CASCADE;
```

### Acessar o PSQL
```sql
a```

### Verificar as Tabelas no Banco de Dados Atual
Para listar todas as tabelas disponíveis no banco de dados:
```sql
\dt
```

### Mostrar a Estrutura de uma Tabela
Para exibir a definição de uma tabela (colunas, tipos, chaves, etc.):
```sql
\d nome_da_tabela
```

### Listar todos os Bancos
Para exibir todos os bancos de dados cadastrados:
```sql
\l
```

### Sair do PSQL
```sql
\q
```

### Criar arquivo de backup pelo pg_dump
Vá até o diretório onde se deseja guardar o backup e digite o comando:
```sql
pg_dump -U usuario -d nome_do_banco -f caminho_do_arquivo.sql
```
### Restaurar um banco a partir de um arquivo de backup
Vá até o diretório onde esta guardado o arquivo de bkcp e digite o comando:
```sql
psql -U usuario -d nome_do_banco -f caminho_do_arquivo.bkp
```
### Cria ou atualiza lista de dependencias
Cria ou atualiza a lista com as bibliotecas necessária para o projeto.
```sql
pip freeze > requirements.txt
```
Depois para instalar as dependencias:
```sql
pip install -r requirements.txt
```

### Ativa o ambiente virtual
Ativa o ambiente virtual com as dependencias baixadas.
```sql
source seu_ambiente_virtual/bin/activate
```
Para desaivar:
```sql
deactivate
```

### Gerenciador de processos tmux
Permite criar sessões de terminal persistentes. Utilizamos para rodar o flask, dessa forma ele não cai ao nos desconectarmos da VPS.
Instalar o tmux:
```sql
sudo apt-get install tmux  # Para Debian/Ubuntu

```
Para criar uma nova sessão:
```sql
tmux new-session -s <process_name>
```
Dentro da sessão tmux, execute seu servidor Flask:
```sql
python api.py

```
Para sair da sessão tmux sem encerrar o processo, pressione Ctrl + B, depois D (isso desconecta você da sessão tmux, mas o processo continua rodando).

Para voltar à sessão tmux a qualquer momento, execute:
```sql
tmux attach-session -t <nome_do_processo>

```
### CRONTABS
Para pesquisar um bash que roda no cronjob específico, execute:
```sql
journalctl -u cron | grep "<nome_do_bash_script>"

```
