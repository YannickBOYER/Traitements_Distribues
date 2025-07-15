#!/bin/bash
# Simple script to generate self-signed certificates for the demo environment
set -e

mkdir -p grafana kafka

# Password used for demo keystores
PASSWORD="changeit"

# Generate CA
openssl req -new -x509 -nodes -days 365 -subj "/CN=demo-ca" \
    -keyout kafka/ca.key -out kafka/ca.crt

# Kafka server certificate
openssl req -newkey rsa:2048 -nodes -keyout kafka/server.key \
    -subj "/CN=kafka" -out kafka/server.csr
openssl x509 -req -days 365 -in kafka/server.csr -CA kafka/ca.crt \
    -CAkey kafka/ca.key -CAcreateserial -out kafka/server.crt

# Client certificate (shared for demo)
openssl req -newkey rsa:2048 -nodes -keyout kafka/client.key \
    -subj "/CN=client" -out kafka/client.csr
openssl x509 -req -days 365 -in kafka/client.csr -CA kafka/ca.crt \
    -CAkey kafka/ca.key -CAcreateserial -out kafka/client.crt

# Create server keystore (PKCS12 -> JKS)
openssl pkcs12 -export -in kafka/server.crt -inkey kafka/server.key \
    -chain -CAfile kafka/ca.crt -name kafka -out kafka/server.p12 \
    -passout pass:$PASSWORD
keytool -importkeystore -deststorepass $PASSWORD -destkeypass $PASSWORD \
    -destkeystore kafka/server.keystore.jks -srckeystore kafka/server.p12 \
    -srcstoretype PKCS12 -srcstorepass $PASSWORD -alias kafka >/dev/null
rm kafka/server.p12

# Create truststore with CA certificate
keytool -import -alias CARoot -file kafka/ca.crt \
    -keystore kafka/server.truststore.jks -storepass $PASSWORD -noprompt >/dev/null

# Credentials file used by the Kafka container
echo -n $PASSWORD > kafka/credentials.txt

# === Création du keystore client pour Kafka-UI ===

# 1. Emballer client.crt + client.key + CA dans un PKCS12
openssl pkcs12 -export \
  -in kafka/client.crt \
  -inkey kafka/client.key \
  -chain -CAfile kafka/ca.crt \
  -name kafka-ui-client \
  -out kafka/client.p12 \
  -passout pass:$PASSWORD

# 2. Convertir le PKCS12 en JKS pour Kafka-UI
keytool -importkeystore \
  -deststorepass $PASSWORD \
  -destkeypass $PASSWORD \
  -destkeystore kafka/client.keystore.jks \
  -srckeystore kafka/client.p12 \
  -srcstoretype PKCS12 \
  -srcstorepass $PASSWORD \
  -alias kafka-ui-client \
  >/dev/null

# 3. (Optionnel) Création d’un truststore client si vous voulez séparer
keytool -import \
  -alias CARoot \
  -file kafka/ca.crt \
  -keystore kafka/client.truststore.jks \
  -storepass $PASSWORD \
  -noprompt \
  >/dev/null

# Nettoyage
rm kafka/client.p12

echo "Keystore et truststore client pour Kafka-UI créés sous kafka/client.keystore.jks et kafka/client.truststore.jks"

# Grafana server certificate
openssl req -newkey rsa:2048 -nodes -keyout grafana/server.key \
    -subj "/CN=grafana" -out grafana/server.csr
openssl x509 -req -days 365 -in grafana/server.csr -CA kafka/ca.crt \
    -CAkey kafka/ca.key -CAcreateserial -out grafana/server.crt

rm kafka/server.csr grafana/server.csr kafka/client.csr

echo "Certificates generated under certs/"