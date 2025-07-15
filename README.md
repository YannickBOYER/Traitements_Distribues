# Traitements distribués

Ce dépôt contient un projet d'analyse de logs HTTP à l'aide de Kafka et de Spark Streaming.

## Prérequis

- **Docker** et **Docker&nbsp;Compose** pour lancer l'architecture complète.
- Python 3 et `spark-submit` si vous souhaitez exécuter les scripts seuls.

## Démarrage rapide avec Docker

1. Construisez et démarrez l'ensemble des services :

   ```bash
   docker compose up -d --build
   ```

   Les conteneurs suivants seront lancés :

   - Zookeeper et Kafka pour la messagerie.
   - `log-generator` qui produit en continu des lignes de logs dans Kafka.
   - `spark-streaming` qui lit ces logs, calcule des métriques et envoie des alertes.

2. Les messages d'alerte sont publiés dans le topic Kafka `alerts`.

Arrêtez l'environnement avec `Ctrl+C` puis `docker compose down`.

## Exécution manuelle

Il est également possible de tester les scripts sans Docker :

1. Générez des logs et exposez-les sur un port :

   ```bash
   python log_generation_complete.py
   ```

2. Dans une autre fenêtre, lancez l'analyse en streaming :

   ```bash
   spark-submit log_analysis_complete.py
   ```

Les statistiques seront ajoutées dans le fichier `results.txt` toutes les minutes.

## Configuration de l'authentification Kafka

Les services utilisent désormais l'authentification SASL/PLAIN en plus du SSL. Les identifiants sont renseignés dans le fichier `.env` :

```bash
KAFKA_USERNAME=admin
KAFKA_PASSWORD=admin-secret
```

Docker Compose charge automatiquement ces variables pour les conteneurs ayant besoin de se connecter à Kafka.

## Arborescence

- `log_generation.py` : générateur de logs simple envoyé sur la sortie standard.
- `log_analysis.py` : version minimale d'analyse des logs en Spark Streaming.
- `log_generator/` : image Docker plus avancée de génération de logs (production vers Kafka).
- `spark/` : image Docker contenant différents scripts d'analyse avec Spark.
- `docker-compose.yml` : orchestration complète Zookeeper/Kafka + générateur + analyseur.

