#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

WORKER_COUNT="${1:-3}"
[[ $# -le 1 && "$WORKER_COUNT" =~ ^[123]$ ]] || fail "Uso: $0 [1|2|3]"

ensure_runtime_dirs
"$HERE/preflight.sh" --for-start
SPARK_HOME_DETECTED="$(detect_spark_home)"
SPARK_CLASS="$SPARK_HOME_DETECTED/bin/spark-class"

export SPARK_LOCAL_IP="$CLUSTER_HOST"
export PYSPARK_PYTHON

start_component() {
  local name="$1" port="$2" marker="$3"
  shift 3
  local log="$LOG_DIR/$name.log" pid

  say "Iniciando $name..."
  nohup "$SPARK_CLASS" "$marker" "$@" >"$log" 2>&1 &
  pid=$!
  printf '%s\n' "$pid" >"$PID_DIR/$name.pid"

  if ! wait_for_port "$port"; then
    say "No se abrió el puerto $port. Últimas líneas de $log:" >&2
    tail -20 "$log" >&2 || true
    "$HERE/stop.sh" >/dev/null 2>&1 || true
    exit 1
  fi
  say "  $name activo (PID $pid, puerto $port)"
}

start_component master "$MASTER_RPC_PORT" org.apache.spark.deploy.master.Master \
  --host "$CLUSTER_HOST" --port "$MASTER_RPC_PORT" --webui-port "$MASTER_UI_PORT"

for ((i = 0; i < WORKER_COUNT; i++)); do
  number=$((i + 1))
  start_component "worker-$number" "${WORKER_RPC_PORTS[$i]}" org.apache.spark.deploy.worker.Worker \
    --host "$CLUSTER_HOST" \
    --port "${WORKER_RPC_PORTS[$i]}" \
    --webui-port "${WORKER_UI_PORTS[$i]}" \
    --cores "$WORKER_CORES" \
    --memory "$WORKER_MEMORY" \
    --work-dir "$WORK_DIR/worker-$number" \
    "spark://$CLUSTER_HOST:$MASTER_RPC_PORT"
done

say ""
say "Clúster iniciado con $WORKER_COUNT worker(s)."
say "Master UI: http://$CLUSTER_HOST:$MASTER_UI_PORT"
"$HERE/status.sh"
