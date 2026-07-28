# Imagem base com Python
FROM python:3.11-slim

# O pacote wkhtmltopdf foi removido dos repositórios oficiais do Debian
# (depende de uma versão "patched" do Qt que não está mais nos repos padrão).
# Por isso baixamos o .deb oficial direto do projeto no GitHub.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fontconfig \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    xfonts-75dpi \
    xfonts-base \
    fonts-liberation \
    fonts-dejavu \
    && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get install -y ./wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && rm wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependências Python primeiro (aproveita cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos do projeto
COPY . .

# Cria a pasta pública de arquivos, caso ainda não exista
RUN mkdir -p arquivos_publicos

# Railway injeta a variável PORT automaticamente — o comando abaixo usa ela.
# --workers 4 permite atender vários clientes ao mesmo tempo (cada worker
# processa um pedido de cada vez, então 4 workers = até 4 mapas sendo
# gerados em paralelo sem um cliente esperar o outro terminar).
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4"]
