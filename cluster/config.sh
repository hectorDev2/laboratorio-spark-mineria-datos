#!/usr/bin/env bash

# Topología: un master y tres workers JVM, todos limitados a loopback.
CLUSTER_HOST="127.0.0.1"
MASTER_RPC_PORT=7077
MASTER_UI_PORT=8080
WORKER_RPC_PORTS=(7078 7079 7080)
WORKER_UI_PORTS=(8081 8082 8083)

# Valores moderados para un Apple M1 con 8 GiB.
EXPECTED_SPARK_VERSION="4.2.0"
EXPECTED_JAVA_MAJOR=21
EXPECTED_PYTHON_MINOR="3.12"
WORKER_CORES=1
WORKER_MEMORY="768m"
DRIVER_MEMORY="1g"
EXECUTOR_MEMORY="512m"
APP_UI_PORT=4040

# Puede sobreescribirse antes de invocar cualquier script.
PYSPARK_PYTHON="${PYSPARK_PYTHON:-python3}"
