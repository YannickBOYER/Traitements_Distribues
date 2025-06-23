# Dockerfile for my spark image
FROM bitnami/spark:3.5.5

WORKDIR /app
USER root

RUN apt-get update && apt-get install -y python3-pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

CMD ["spark-submit", "log_analysis_complete.py"]
