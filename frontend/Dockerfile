FROM python:3.9-slim

WORKDIR /app

COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./frontend ./frontend

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py"]