#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
DB_PATH="$ROOT_DIR/database/e2e.sqlite"

rm -f "$DB_PATH"
cd "$ROOT_DIR/backend"
DATABASE_URL="sqlite:///$DB_PATH" uv run python create_sample_data.py
