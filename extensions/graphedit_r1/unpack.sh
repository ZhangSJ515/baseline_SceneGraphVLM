#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$ROOT/source"

if [[ -f "$SOURCE/pyproject.toml" && -f "$SOURCE/graphedit_r1/__init__.py" ]]; then
  echo "GraphEdit-R1 source is already present as plaintext; no archive extraction is required."
  echo "Source: $SOURCE"
  echo "Install: pip install -e $SOURCE"
  exit 0
fi

echo "ERROR: plaintext GraphEdit-R1 source is missing." >&2
echo "Run:" >&2
echo "  git fetch origin" >&2
echo "  git pull --ff-only origin agent/graphedit-r1-supplement" >&2
echo "and retry." >&2
exit 1
