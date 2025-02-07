FROM python:3.9-slim

WORKDIR /app

COPY ./db/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./db ./db

EXPOSE 8001

CMD ["uvicorn", "db.main:app", "--host", "0.0.0.0", "--port", "8001"]
