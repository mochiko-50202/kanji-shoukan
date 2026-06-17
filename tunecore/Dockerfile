FROM python:3.12-slim

WORKDIR /app

# python-magic の依存システムライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# $PORT は Railway が実行時に注入する — ハードコード厳禁
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --limit-request-body 20971520"]
