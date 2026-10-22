#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f data/catalogue.sqlite || { echo 'Build the catalogue first; see README.md.' >&2; exit 1; }
uv export --locked --no-dev --no-emit-project -o requirements.lock
npm --prefix frontend ci
npm --prefix frontend run build
docker build -t starcoach-torob:local .
