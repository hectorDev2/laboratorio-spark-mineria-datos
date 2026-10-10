#!/usr/bin/env bash

CLUSTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config.sh
source "$CLUSTER_DIR/config.sh"

RUNTIME_DIR="${SPARK_LAB_RUNTIME_DIR:-$CLUSTER_DIR/runtime}"
PID_DIR="$RUNTIME_DIR/pids"
LOG_DIR="$RUNTIME_DIR/logs"
WORK_DIR="$RUNTIME_DIR/work"
DATA_DIR="${SPARK_LAB_DATA_DIR:-$CLUSTER_DIR/data}"

say() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

ensure_runtime_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR" "$WORK_DIR" "$DATA_DIR"
}

detect_spark_home() {
  if [[ -n "${SPARK_HOME:-}" && -x "$SPARK_HOME/bin/spark-class" ]]; then
    printf '%s\n' "$SPARK_HOME"
    return
  fi

  local detected
  detected="$($PYSPARK_PYTHON -c 'import os, pyspark; print(os.path.dirname(pyspark.__file__))' 2>/dev/null || true)"
  if [[ -n "$detected" && -x "$detected/bin/spark-class" ]]; then
    printf '%s\n' "$detected"
    return
  fi

  fail "No se encontró Spark. Definí SPARK_HOME o instalá pyspark para $PYSPARK_PYTHON."
}

port_listener() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | tail -n +2
}

port_is_listening() {
  [[ -n "$(port_listener "$1")" ]]
}

pid_is_alive() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

pid_matches() {
  local pid="$1" marker="$2" command_line
  pid_is_alive "$pid" || return 1
  command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command_line" == *"$marker"* ]]
}

read_pid() {
  local name="$1" file="$PID_DIR/$name.pid"
  [[ -f "$file" ]] && tr -cd '0-9' <"$file"
}

wait_for_port() {
  local port="$1" attempts="${2:-30}" i
  for ((i = 1; i <= attempts; i++)); do
    port_is_listening "$port" && return 0
    sleep 0.5
  done
  return 1
}

require_free_port() {
  local port="$1" label="$2" listener
  listener="$(port_listener "$port")"
  [[ -z "$listener" ]] || fail "$label necesita el puerto $port, pero ya está ocupado:\n$listener"
}

component_state() {
  local name="$1" marker="$2" port="$3" pid
  pid="$(read_pid "$name")"
  if [[ -n "$pid" ]] && pid_matches "$pid" "$marker"; then
    if port_is_listening "$port"; then printf 'ACTIVO'; else printf 'INICIANDO'; fi
  elif port_is_listening "$port"; then
    printf 'PUERTO_OCUPADO'
  else
    printf 'DETENIDO'
  fi
}
