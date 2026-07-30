#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
project_root="$repo_root/bilibili-radio"
output="${1:-$repo_root/bilibili-radio-deploy.tar.gz}"

cd "$project_root"

dirty="$(git status --short -- . || true)"
if [[ -n "$dirty" ]]; then
  echo "WARNING: working tree has uncommitted project changes; the archive is generated from HEAD only." >&2
  echo "$dirty" >&2
fi

git -C "$repo_root" archive \
  --format=tar.gz \
  --prefix=bilibili-radio/ \
  --output="$output" \
  HEAD:bilibili-radio

echo "Wrote $output"
tar -tzf "$output" | sed -n '1,20p'
