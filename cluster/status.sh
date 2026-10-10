#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

ensure_runtime_dirs
printf '%-12s %-16s %-8s %-8s\n' COMPONENTE ESTADO RPC UI
printf '%-12s %-16s %-8s %-8s\n' master \
  "$(component_state master org.apache.spark.deploy.master.Master "$MASTER_RPC_PORT")" \
  "$MASTER_RPC_PORT" "$MASTER_UI_PORT"
for i in 0 1 2; do
  number=$((i + 1))
  printf '%-12s %-16s %-8s %-8s\n' "worker-$number" \
    "$(component_state "worker-$number" org.apache.spark.deploy.worker.Worker "${WORKER_RPC_PORTS[$i]}")" \
    "${WORKER_RPC_PORTS[$i]}" "${WORKER_UI_PORTS[$i]}"
done

say ""
say "Master UI:      http://$CLUSTER_HOST:$MASTER_UI_PORT"
say "Application UI: http://$CLUSTER_HOST:$APP_UI_PORT (durante un trabajo)"
say "Logs:            $LOG_DIR"
