FROM python:3.9-slim

WORKDIR /app

COPY llm/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./llm ./llm
COPY ./rag_docs ./rag_docs

CMD ["uvicorn", "llm.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]