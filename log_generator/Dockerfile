FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/ 

CMD ["python", "log_generation_complete.py", "--kafka-broker", "kafka:9093", "--topic", "http-logs", "--rate", "100", "--error-user-percent", "20"]
