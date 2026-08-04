FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fetch the embedding model at build time so the RAG upload route works without
# reaching Hugging Face at runtime (HF is unreachable in this environment).
RUN modelscope download --model AI-ModelScope/all-MiniLM-L6-v2 \
    --local_dir /app/artifacts/rag/hf_models/all-MiniLM-L6-v2

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
