#!/usr/bin/env bash
# Bundle repo-root assets into /backend so the backend deploys as a self-contained
# unit (the native Fly deploy uploads only this directory). Copies are gitignored;
# the committed sources at the repo root remain the single source of truth.
set -euo pipefail
cd "$(dirname "$0")"
for d in prompts data frontend; do
  rm -rf "./$d"
  cp -r "../$d" "./$d"
done
echo "Bundled prompts/, data/, frontend/ into backend/"
