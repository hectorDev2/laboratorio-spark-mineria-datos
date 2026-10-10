# Guía de ejecución

## 1. Preparar el entorno

Ubicate en la carpeta que contiene los CSV y `laboratorio_spark/`.

```bash
python3 --version
java -version
python3 -c "import pyspark; print(pyspark.__version__)"
```

El laboratorio fue diseñado para Python 3.12, Java 21 y Spark 4.2.0. Si `SPARK_HOME` no se detecta desde PySpark, exportalo manualmente.

## 2. Ejecutar validaciones sin iniciar Spark

```bash
python3 -m unittest discover -s laboratorio_spark/tests -v
bash laboratorio_spark/cluster/tests/test_cluster_files.sh
```

Estas validaciones revisan cálculos puros, reglas editoriales, sintaxis Bash, puertos, recursos y estructura del clúster.

## 3. Preparar los datos

```bash
cd laboratorio_spark/cluster
chmod +x ./*.sh tests/*.sh
./preflight.sh
./setup_data.sh
```

`setup_data.sh` crea enlaces simbólicos dentro de `cluster/data/`. Para usar copias físicas:

```bash
./setup_data.sh --copy
```

## 4. Iniciar los procesos

```bash
./start.sh
./status.sh
```

La salida esperada debe listar un master y tres workers activos. También podés revisar:

- Master: `http://127.0.0.1:8080`
- Worker 1: `http://127.0.0.1:8081`
- Worker 2: `http://127.0.0.1:8082`
- Worker 3: `http://127.0.0.1:8083`

Volvé a la raíz del proyecto:

```bash
cd ../..
```

## 5. Ejecutar el análisis

Ejecución completa:

```bash
./laboratorio_spark/cluster/submit.sh \
  laboratorio_spark/scripts/run_spark_analysis.py \
  --input-dir laboratorio_spark/cluster/data \
  --output-dir laboratorio_spark/resultados/spark \
  --graph-dir laboratorio_spark/graficos/spark
```

Para validar primero la parte descriptiva sin entrenar modelos:

```bash
./laboratorio_spark/cluster/submit.sh \
  laboratorio_spark/scripts/run_spark_analysis.py \
  --input-dir laboratorio_spark/cluster/data \
  --output-dir laboratorio_spark/resultados/spark \
  --graph-dir laboratorio_spark/graficos/spark \
  --skip-ml
```

Durante el trabajo, la interfaz de la aplicación está en `http://127.0.0.1:4040`.

### Salidas esperadas

- `resultados/spark/verificacion.json`
- `resultados/spark/comparacion_sur_norte.csv`
- `resultados/spark/sur/*.csv`
- `resultados/spark/norte/*.csv`
- `resultados/spark/cusco/*.csv`
- `resultados/spark/cusco/modelo_logistico_compra.json`
- `resultados/spark/cusco/modelo_logistico_alquila.json`
- `graficos/spark/*.png`

## 6. Medir escalabilidad

La medición debe hacerse con exactamente 1, 2 y 3 workers activos. Para cada escenario, detené el clúster, reinicialo con la cantidad indicada y confirmá el estado:

```bash
./laboratorio_spark/cluster/stop.sh
./laboratorio_spark/cluster/start.sh 1   # luego 2 y 3 en sus respectivas corridas
./laboratorio_spark/cluster/status.sh
```

Después ejecutá:

```bash
./laboratorio_spark/cluster/submit.sh \
  laboratorio_spark/scripts/run_scalability.py \
  --input-dir laboratorio_spark/cluster/data \
  --workers 1 \
  --output laboratorio_spark/resultados/escalabilidad/1-worker.json
```

Repetí el ciclo con `start.sh 2` / `--workers 2` y `start.sh 3` / `--workers 3`, cambiando también el nombre del archivo. El programa contrasta el escenario solicitado con los executors que Spark reporta y cancela la medición si no coinciden.

Cada corrida hace un calentamiento y tres mediciones. La salida registra los tiempos individuales y su mediana. No compares escenarios si cambiaste simultáneamente memoria, cores, consulta o datos.

## 7. Regenerar gráficos descriptivos e informe

Para volver a calcular los agregados base y los cinco gráficos:

```bash
python3 -m laboratorio_spark.scripts.generate_assets --input-dir .
```

Para generar el PDF:

```bash
python3 -m laboratorio_spark.scripts.generate_report
```

El archivo resultante queda en `laboratorio_spark/informe/Informe_Laboratorio_Spark.pdf`.

## 8. Detener el laboratorio

```bash
./laboratorio_spark/cluster/stop.sh
./laboratorio_spark/cluster/status.sh
```

Si algo falla, revisá `laboratorio_spark/cluster/runtime/logs/`. No borres los PID mientras los procesos estén activos.

## Criterios de interpretación

- Las tasas son proporciones observadas, no efectos causales.
- El área bajo ROC solo se informa después de ejecutar el pipeline MLlib.
- Los tiempos solo son comparables bajo el mismo protocolo.
- Un clúster local multiproceso comparte hardware; no evalúa latencia de red ni fallas de otra máquina.
