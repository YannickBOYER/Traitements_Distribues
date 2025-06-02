import sys
import re
from datetime import datetime
from pyspark import SparkContext
from pyspark.streaming import StreamingContext

if len(sys.argv) != 4:
    print("Usage: spark-submit log_analysis_minimal.py <host> <port> <output_file>")
    sys.exit(1)

host = sys.argv[1]
port = int(sys.argv[2])
output_path = sys.argv[3]

sc = SparkContext(appName="LogAnalysisMinimal")
ssc = StreamingContext(sc, batchDuration=1)

lines = ssc.socketTextStream(host, port)

# Fenêtre glissante de 60 s, pas de chevauchement (slide=60)
windowed = lines.window(windowDuration=60, slideDuration=60)

def process_rdd(rdd):
    """
    Pour chaque RDD de 60 s : compte total et erreurs, calcule le taux,
    et écrit une ligne horodatée dans output_path.
    """
    count_total = rdd.count()
    if count_total == 0:
        return

    # Extraction du code HTTP via split sur les guillemets
    def is_error(line):
        try:
            parts = line.split('"')
            status = int(parts[2].strip().split()[0])
            return status >= 400
        except:
            return False

    count_err = rdd.filter(is_error).count()
    rate = count_err / count_total * 100

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_line = f"{timestamp}, total={count_total}, errors={count_err}, error_rate={rate:.2f}%\n"

    with open(output_path, "a") as f:
        f.write(output_line)

windowed.foreachRDD(process_rdd)

ssc.start()
ssc.awaitTermination()