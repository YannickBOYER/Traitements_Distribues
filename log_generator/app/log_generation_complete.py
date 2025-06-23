import time
import random
import argparse
from datetime import datetime
from kafka import KafkaProducer

# Liste de quelques URLs exemples
URLS = [
    "/index.html", "/login", "/logout",
    "/products", "/cart", "/api/data",
    "/images/logo.png", "/search", "/checkout",
    "/user/profile", "/admin/dashboard", "/help",
    "/home", "/product/chaussette1", "/product/chaussette2",
    "/product/chaussette3", "/signup", "/contact", "/about"
]
# Codes HTTP non-erronés et erronés
GOOD_STATUS = [200, 201, 301, 302]
ERROR_STATUS = [400, 401, 403, 404, 500, 502, 503]

def random_ip():
    # Ici, seulement des IPs de la plage 192.168.10.x pour avoir un nombre d'utilisateurs limité afin de créer des alertes
    return f"192.168.10.{random.randint(0, 255)}"

def parse_args():
    p = argparse.ArgumentParser(
        description="Générateur de logs Apache configurables"
    )
    p.add_argument(
        "--rate", type=float, default=1.0,
        help="Logs générés par seconde (float)"
    )
    p.add_argument(
        "--error-user-percent", type=float, default=10.0,
        help="%% d'utilisateurs (IP) qui peuvent générer des erreurs"
    )
    p.add_argument(
        "--error-rate", type=float, default=50.0,
        help="Pour les utilisateurs 'défectueux', %% de leurs requêtes sont en erreur"
    )
    p.add_argument(
        "--error-url-percent", type=float, default=20.0,
        help="%% des URLs considérées comme 'à risque' générant potentiellement des erreurs"
    )
    p.add_argument("--kafka-broker", type=str, default="localhost:9092",
                   help="Adresse du broker Kafka, ex. localhost:9092")
    p.add_argument("--topic", type=str, default="http-logs",
                   help="Nom du topic Kafka dans lequel produire les logs")
    
    return p.parse_args()

def main():
    args = parse_args()

    sleep_time = 1.0 / args.rate

    # Prépare le producer Kafka
    try:
        producer = KafkaProducer(
            bootstrap_servers=[args.kafka_broker],
            value_serializer=lambda v: str(v).encode('utf-8'),
            acks='all',
            retries=5,
            linger_ms=100,
            batch_size=16384
        )
    except Exception as e:
        print(f"Erreur lors de la connexion à Kafka: {e}")
        return

    # On choisit aléatoirement un sous-ensemble d'URLs "à risque"
    num_error_urls = max(1,
        int(len(URLS) * args.error_url_percent / 100.0)
    )
    error_urls = set(random.sample(URLS, num_error_urls))
    try:
        while True:
            ip = random_ip()
            # Déterminer si l'IP fait partie des utilisateurs "défectueux"
            random_num = (random.random() * 100)
            is_error_user = random_num < args.error_user_percent
            # Choisit une URL et décide du statut
            url = random.choice(URLS)
            if is_error_user and url in error_urls:
                # L'utilisateur et l'URL sont "à risque" : on peut produire une erreur
                status = (
                    random.choice(ERROR_STATUS)
                    if (random.random() * 100) < args.error_rate
                    else random.choice(GOOD_STATUS)
                )
            else:
                # pas d'erreur : on force un bon code
                status = random.choice(GOOD_STATUS)

            size = random.randint(200, 5000)
            timestamp = datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")
            method = random.choice(["GET", "POST", "PUT", "DELETE"])

            line = (
                f'{ip} - [{timestamp}] "{method} {url} HTTP/1.1" {status} {size}'
            )

            # print(line, flush=True)
            # Envoi du log à Kafka
            try:
                producer.send(args.topic, value=line)
            except Exception as e:
                print(f"Erreur lors de l'envoi du log à Kafka: {e}")
            
            print(f"Log envoyé: {line}")

            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nInterrompu, arrêt du générateur.")

    finally:
        producer.flush()
        producer.close()
        print("Producteur Kafka fermé.")

if __name__ == "__main__":
    main()