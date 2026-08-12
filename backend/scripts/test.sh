#!/usr/bin/env bash
# Docker 기반 백엔드 테스트 실행기 (Linux/macOS/Git Bash 공용).
#
#   ./backend/scripts/test.sh                       # 전체 테스트
#   ./backend/scripts/test.sh tests/grading -k lint # pytest 인자 그대로 전달
#   SERVICE=coverage ./backend/scripts/test.sh      # 커버리지 리포트
#   SERVICE=format ./backend/scripts/test.sh        # black --check
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
service="${SERVICE:-tests}"

exec docker compose -f "${repo_root}/docker-compose.test.yml" \
  run --rm --build "${service}" "$@"
