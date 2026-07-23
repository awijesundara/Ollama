#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
exec alembic -x "database_url=${DATABASE_URL}" upgrade head

