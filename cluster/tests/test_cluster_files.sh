#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required=(
  config.sh lib/common.sh preflight.sh start.sh stop.sh status.sh
  submit.sh setup_data.sh README.md diagrama/topologia.json
)

for file in "${required[@]}"; do
  [[ -f "$ROOT/$file" ]] || { printf 'Falta: %s\n' "$file" >&2; exit 1; }
done

for file in "$ROOT"/*.sh "$ROOT"/lib/*.sh; do
  bash -n "$file"
done

python3 -m json.tool "$ROOT/diagrama/topologia.json" >/dev/null

grep -q 'MASTER_RPC_PORT=7077' "$ROOT/config.sh"
grep -q 'WORKER_RPC_PORTS=(7078 7079 7080)' "$ROOT/config.sh"
grep -q 'WORKER_UI_PORTS=(8081 8082 8083)' "$ROOT/config.sh"
grep -q 'WORKER_MEMORY="768m"' "$ROOT/config.sh"
grep -q 'EXPECTED_SPARK_VERSION="4.2.0"' "$ROOT/config.sh"
grep -q 'EXPECTED_JAVA_MAJOR=21' "$ROOT/config.sh"
grep -q 'EXPECTED_PYTHON_MINOR="3.12"' "$ROOT/config.sh"
grep -q 'org.apache.spark.deploy.master.Master' "$ROOT/start.sh"
grep -q 'org.apache.spark.deploy.worker.Worker' "$ROOT/start.sh"
grep -q 'WORKER_COUNT="${1:-3}"' "$ROOT/start.sh"
grep -q 'spark://127.0.0.1:7077' "$ROOT/README.md"

printf 'OK: estructura y sintaxis del clúster\n'
