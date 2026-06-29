# Cliente Python do Experimento D (litellm + pymupdf). Nada instalado no base do host.
# Build (contexto = experimentos/d_texto_local):
#   docker build -t trct-d-client -f experimentos/d_texto_local/client/Dockerfile experimentos/d_texto_local
FROM python:3.11-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /app
