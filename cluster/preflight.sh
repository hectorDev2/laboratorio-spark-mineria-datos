#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

CHECK_PORTS=false
[[ "${1:-}" == "--for-start" ]] && CHECK_PORTS=true
[[ $# -le 1 ]] || fail "Uso: $0 [--for-start]"

ensure_runtime_dirs

command -v java >/dev/null || fail "Java no está disponible en PATH."
command -v "$PYSPARK_PYTHON" >/dev/null || fail "$PYSPARK_PYTHON no está disponible en PATH."
command -v lsof >/dev/null || fail "lsof es necesario para validar puertos."

SPARK_HOME_DETECTED="$(detect_spark_home)"
SPARK_VERSION="$($SPARK_HOME_DETECTED/bin/spark-submit --version 2>&1 | sed -n 's/.*version \([0-9][^ ]*\).*/\1/p' | head -1)"
JAVA_VERSION="$(java -version 2>&1 | head -1)"
PYTHON_VERSION="$($PYSPARK_PYTHON --version 2>&1)"
JAVA_MAJOR="$(java -version 2>&1 | sed -n '1s/.*version "\([0-9][0-9]*\).*/\1/p')"
PYTHON_MINOR="$($PYSPARK_PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

[[ -x "$SPARK_HOME_DETECTED/bin/spark-class" ]] || fail "Falta bin/spark-class en $SPARK_HOME_DETECTED."
[[ "$SPARK_VERSION" == "$EXPECTED_SPARK_VERSION" ]] || fail "Se requiere Spark $EXPECTED_SPARK_VERSION; se detectó ${SPARK_VERSION:-una versión no identificada}."
[[ "$JAVA_MAJOR" == "$EXPECTED_JAVA_MAJOR" ]] || fail "Se requiere Java $EXPECTED_JAVA_MAJOR; se detectó: $JAVA_VERSION."
[[ "$PYTHON_MINOR" == "$EXPECTED_PYTHON_MINOR" ]] || fail "Se requiere Python $EXPECTED_PYTHON_MINOR.x; se detectó: $PYTHON_VERSION."

if $CHECK_PORTS; then
  require_free_port "$MASTER_RPC_PORT" "Spark Master RPC"
  require_free_port "$MASTER_UI_PORT" "Spark Master UI"
  require_free_port "$APP_UI_PORT" "Spark Application UI"
  for i in 0 1 2; do
    require_free_port "${WORKER_RPC_PORTS[$i]}" "Worker $((i + 1)) RPC"
    require_free_port "${WORKER_UI_PORTS[$i]}" "Worker $((i + 1)) UI"
  done
fi

CSV_COUNT="$(find -L "$DATA_DIR" -maxdepth 1 -type f -name '*.csv' 2>/dev/null | wc -l | tr -d ' ')"

cat <<EOF
Preflight correcto
  Spark home : $SPARK_HOME_DETECTED
  Spark      : ${SPARK_VERSION:-versión no extraída}
  Java       : $JAVA_VERSION
  Python     : $PYTHON_VERSION
  Datos      : $DATA_DIR ($CSV_COUNT CSV)
  Runtime    : $RUNTIME_DIR
EOF

if [[ "$CSV_COUNT" -lt 2 ]]; then
  say "AVISO: ejecutá ./setup_data.sh para preparar los dos CSV."
fi
