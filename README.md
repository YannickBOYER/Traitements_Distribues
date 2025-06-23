# Traitements_Distribues

python log_generation.py | nc -lk 9999

puis:
spark_submit log_analysis.py localhost 9999 results.txt