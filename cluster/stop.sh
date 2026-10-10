#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

ensure_runtime_dirs

stop_component() {
  local name="$1" marker="$2" pid file="$PID_DIR/$name.pid"
  pid="$(read_pid "$name")"
  if [[ -z "$pid" ]]; then
    say "$name: sin PID registrado"
    return
  fi
  if ! pid_matches "$pid" "$marker"; then
    say "$name: PID $pid no corresponde; no se envía ninguna señal"
    rm -f "$file"
    return
  fi

  kill "$pid"
  for _ in {1..20}; do
    pid_is_alive "$pid" || break
    sleep 0.25
  done
  if pid_is_alive "$pid" && pid_matches "$pid" "$marker"; then
    say "$name: cierre normal agotado; enviando KILL"
    kill -KILL "$pid" 2>/dev/null || true
    for _ in {1..8}; do
      pid_is_alive "$pid" || break
      sleep 0.25
    done
  fi
  pid_is_alive "$pid" && fail "$name continúa activo con PID $pid."
  rm -f "$file"
  say "$name: detenido"
}

# Primero se retiran los workers; luego, el coordinador.
for number in 3 2 1; do
  stop_component "worker-$number" org.apache.spark.deploy.worker.Worker
done
stop_component master org.apache.spark.deploy.master.Master
