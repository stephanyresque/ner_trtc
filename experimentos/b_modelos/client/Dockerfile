# Cliente Python do Experimento B (litellm + pymupdf). Nada instalado no base do host.
# Build (contexto = experimentos/b_modelos):
#   docker build -t trct-b-client -f experimentos/b_modelos/client/Dockerfile experimentos/b_modelos
FROM python:3.11-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /app
