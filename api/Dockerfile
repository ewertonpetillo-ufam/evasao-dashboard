# Imagem base leve com Python
FROM python:3.10-slim

# Define variáveis de ambiente
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_19_3

# Copia o Instant Client para o container
COPY instantclient-basic-linux.x64-19.3.0.0.0dbru.zip .

# Instala dependências do sistema
RUN apt-get update && \
    apt-get install -y libaio1 wget unzip gcc git && \
    mkdir -p /opt/oracle && \
    mv instantclient-basic-linux.x64-19.3.0.0.0dbru.zip /opt/oracle/ && \
    cd /opt/oracle/ && \
    unzip instantclient-basic-linux.x64-19.3.0.0.0dbru.zip && \
    echo "/opt/oracle/instantclient_19_3/" > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig && \
    rm -f /opt/oracle/instantclient-basic-linux.x64-19.3.0.0.0dbru.zip

# Atualiza o pip e instala dependências do Python
RUN pip install --upgrade pip setuptools wheel
RUN pip install cx_oracle==7.0.0

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos para o container
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponha a porta que a aplicação usará
EXPOSE 8000

# Comando para iniciar a API
CMD ["python", "app.py"]