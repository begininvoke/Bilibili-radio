#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mode="${1:-http-ip}"
compose_files=(-f docker-compose.yml)

case "$mode" in
  http-ip)
    compose_files+=(-f docker-compose.http-ip.yml)
    env_template="deploy/env.http-ip.example"
    ;;
  production)
    compose_files+=(-f docker-compose.monitoring.yml -f docker-compose.production.yml)
    env_template=".env.example"
    ;;
  monitoring)
    compose_files+=(-f docker-compose.monitoring.yml)
    env_template=".env.example"
    ;;
  base)
    env_template=".env.example"
    ;;
  *)
    echo "Usage: bash deploy/deploy.sh [http-ip|production|monitoring|base]" >&2
    exit 2
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose v2 is required" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp "$env_template" .env
  echo "Created .env from $env_template"
  if [[ "$mode" != "http-ip" ]]; then
    echo "Edit .env first, then rerun: bash deploy/deploy.sh $mode" >&2
    exit 1
  fi
fi

mkdir -p server-data

if [[ "$mode" == "http-ip" ]]; then
  echo "WARNING: http-ip mode disables app login and must be protected by firewall, VPN, or security group." >&2
fi

docker compose --env-file .env "${compose_files[@]}" config --quiet
docker compose --env-file .env "${compose_files[@]}" up -d --build --remove-orphans
docker compose --env-file .env "${compose_files[@]}" ps
