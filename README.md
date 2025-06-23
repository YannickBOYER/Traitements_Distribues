# Traitements distribués

Ce dépôt contient un exemple complet de génération et d'analyse de logs HTTP à l'aide de Kafka et de Spark Streaming.

## Prérequis

- **Docker** et **Docker&nbsp;Compose** pour lancer l'architecture complète.
- Python 3 et `spark-submit` si vous souhaitez exécuter les scripts seuls.

## Démarrage rapide avec Docker

1. Construisez et démarrez l'ensemble des services :

   ```bash
   docker compose up --build
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
   python log_generation.py | nc -lk 9999
   ```

2. Dans une autre fenêtre, lancez l'analyse en streaming :

   ```bash
   spark-submit log_analysis.py localhost 9999 results.txt
   ```

Les statistiques seront ajoutées dans le fichier `results.txt` toutes les minutes.

## Arborescence

- `log_generation.py` : générateur de logs simple envoyé sur la sortie standard.
- `log_analysis.py` : version minimale d'analyse des logs en Spark Streaming.
- `log_generator/` : image Docker plus avancée de génération de logs (production vers Kafka).
- `spark/` : image Docker contenant différents scripts d'analyse avec Spark.
- `docker-compose.yml` : orchestration complète Zookeeper/Kafka + générateur + analyseur.

## Documentation

Le document `07_projet.pdf` décrit plus en détail l'objectif et la mise en œuvre du projet.

## Licence

Ce projet est distribué sous la licence MIT.
