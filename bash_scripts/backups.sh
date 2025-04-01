#!/bin/bash

echo "DEU BOA PORRA"

# Diretório de backup
BACKUP_DIR="/root/Documents/API/API_PYTHON/bash_scripts/BCKPs"

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

# Arquivo de plugins
PLUGINS_FILE="$BACKUP_DIR/plugins_grafana.txt"

# Obter lista de plugins e salvar no arquivo
grafana-cli plugins ls | grep @ | sed 'N;s/\n/;/' | sed 's/ @ / /g' > "$PLUGINS_FILE"

# Verificar se o arquivo foi criado com sucesso
if [ ! -f "$PLUGINS_FILE" ]; then
    echo "Erro: Não foi possível criar o arquivo de plugins."
    exit 1
fi

# Nome do arquivo de backup com data
BACKUP_FILE="$BACKUP_DIR/bckps_grafana_$(date +%Y%m%d).tar.gz"

# Criar arquivo tar.gz com os backups
tar -czf "$BACKUP_FILE" /etc/grafana/grafana.ini /var/lib/grafana/grafana.db "$PLUGINS_FILE"

# Verificar se o arquivo tar.gz foi criado com sucesso
if [ -f "$BACKUP_FILE" ]; then
    echo "Backup criado com sucesso: $BACKUP_FILE"
else
    echo "Erro: Não foi possível criar o arquivo de backup."
    exit 1
fi