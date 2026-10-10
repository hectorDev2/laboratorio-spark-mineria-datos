#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

MODE="link"
if [[ "${1:-}" == "--copy" ]]; then MODE="copy"; shift; fi
[[ $# -le 1 ]] || fail "Uso: $0 [--copy] [directorio_origen]"

SOURCE_DIR="${1:-$(cd "$HERE/../.." && pwd)}"
ensure_runtime_dirs

files=(
  "$SOURCE_DIR/dataset_inmobiliario_peru_v2_parte1.csv"
  "$SOURCE_DIR/dataset_inmobiliario_peru_v2_parte2.csv"
)

for source_file in "${files[@]}"; do
  [[ -f "$source_file" ]] || fail "No se encontró: $source_file"
  destination="$DATA_DIR/$(basename "$source_file")"
  if [[ "$MODE" == "copy" ]]; then
    cp -f "$source_file" "$destination"
  else
    ln -sfn "$source_file" "$destination"
  fi
  say "Preparado: $destination"
done

say "Datos disponibles en $DATA_DIR mediante modo $MODE."
