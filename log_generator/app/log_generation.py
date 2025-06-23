import random
from datetime import datetime
import time

# Liste d'exemples d'URLs
URLS = [
    "/home", "/product/chaussette1", "/product/chaussette2",
    "/cart", "/login", "/signup", "/checkout"
]

STATUS_CODES = [200, 201, 301, 302, 400, 401, 403, 404, 500, 502, 503]

def random_ip():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))

def random_url():
    return "http://localhost" + random.choice(URLS)

def generate_log_line():
    ip = random_ip()
    timestamp = datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")
    method = random.choice(["GET", "POST", "PUT", "DELETE"])
    url = random_url()
    status = random.choice(STATUS_CODES)
    return f'{ip} - [{timestamp}] "{method} {url} HTTP/1.1" {status}'

def main():
    print("Générateur de logs démarré (CTRL+C pour arrêter)")
    try:
        while True:
            log_line = generate_log_line()
            print(log_line)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt du générateur de logs.")

if __name__ == "__main__":
    main()
