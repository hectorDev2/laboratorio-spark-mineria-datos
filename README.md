# Práctica de laboratorio — Clúster Spark local multiproceso

Laboratorio reproducible de Minería de Datos sobre 500 000 registros inmobiliarios del Perú. La arquitectura ejecuta un **Spark Master y tres Spark Workers como procesos JVM independientes** en una Mac, todos ligados a `127.0.0.1`.

## Contenido

- `cluster/`: ciclo de vida del clúster, configuración, validaciones y logs.
- `scripts/run_spark_analysis.py`: carga, control de calidad, EDA Sur/Norte, segmentación de Cusco y modelos MLlib.
- `scripts/run_scalability.py`: protocolo temporal con 1, 2 o 3 workers.
- `scripts/generate_assets.py`: cálculo descriptivo fila a fila y gráficos base.
- `scripts/generate_report.py`: composición del informe PDF.
- `resultados/agregados_descriptivos.json`: agregados calculados sobre ambos CSV.
- `graficos/`: visualizaciones incluidas en el informe.
- `informe/Informe_Laboratorio_Spark.pdf`: documento técnico.
- `GUIA_EJECUCION.md`: procedimiento completo.
- `tests/`: pruebas unitarias y validaciones del clúster.

## Inicio rápido

Desde la raíz que contiene `laboratorio_spark/` y los dos CSV:

```bash
python3 -m unittest discover -s laboratorio_spark/tests -v
bash laboratorio_spark/cluster/tests/test_cluster_files.sh

cd laboratorio_spark/cluster
./preflight.sh
./setup_data.sh
./start.sh
./status.sh
cd ../..

./laboratorio_spark/cluster/submit.sh \
  laboratorio_spark/scripts/run_spark_analysis.py \
  --input-dir laboratorio_spark/cluster/data \
  --output-dir laboratorio_spark/resultados/spark \
  --graph-dir laboratorio_spark/graficos/spark

python3 -m laboratorio_spark.scripts.generate_report
./laboratorio_spark/cluster/stop.sh
```

La interfaz del master está en `http://127.0.0.1:8080`; las de workers en `8081`, `8082` y `8083`; la interfaz de una aplicación activa aparece en `http://127.0.0.1:4040`.

## Trazabilidad de resultados

Los números descriptivos del informe provienen de `agregados_descriptivos.json`, generado por un recorrido secuencial de los CSV sin materializar el dataset completo en pandas. La ejecución PySpark escribe su propia salida en `resultados/spark/`, permitiendo comparar ambas rutas de cálculo.

No se incluyen valores de AUC, tiempos de escalabilidad ni capturas de interfaces hasta que sean producidos por una ejecución real del laboratorio.

## Requisitos

- macOS Apple Silicon, 8 GiB o más.
- Java 21.
- Python 3.12.
- Spark/PySpark 4.2.0.
- Dependencias Python: `pyspark`, `matplotlib`, `numpy`, `pandas`, `reportlab`.

Los recursos están deliberadamente limitados: 1 core y 768 MiB por worker, 512 MiB por executor y 1 GiB para el driver.
