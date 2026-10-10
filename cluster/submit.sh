#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

[[ $# -ge 1 ]] || fail "Uso: $0 ruta/aplicacion.py [argumentos...]"
APP="$1"
shift
[[ -f "$APP" ]] || fail "No existe la aplicación: $APP"

MASTER_STATE="$(component_state master org.apache.spark.deploy.master.Master "$MASTER_RPC_PORT")"
[[ "$MASTER_STATE" == "ACTIVO" ]] || fail "El master no está activo. Ejecutá ./start.sh primero."

SPARK_HOME_DETECTED="$(detect_spark_home)"
export SPARK_LOCAL_IP="$CLUSTER_HOST"
export PYSPARK_PYTHON
export PYSPARK_DRIVER_PYTHON="$PYSPARK_PYTHON"

exec "$SPARK_HOME_DETECTED/bin/spark-submit" \
  --master "spark://$CLUSTER_HOST:$MASTER_RPC_PORT" \
  --deploy-mode client \
  --driver-memory "$DRIVER_MEMORY" \
  --executor-memory "$EXECUTOR_MEMORY" \
  --conf "spark.cores.max=3" \
  --conf "spark.executor.cores=1" \
  --conf "spark.driver.host=$CLUSTER_HOST" \
  --conf "spark.driver.bindAddress=$CLUSTER_HOST" \
  --conf "spark.ui.port=$APP_UI_PORT" \
  "$APP" "$@"
