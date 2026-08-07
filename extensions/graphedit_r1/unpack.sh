#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE_DIR="$ROOT/archive"
ARCHIVE="$ARCHIVE_DIR/graphedit_r1_source.tar.gz"
EXPECTED="7e254475cc57448bafdbaa89da446ab8cbd68e157fdc72689e784a3f8d116af2"

shopt -s nullglob
parts=("$ARCHIVE_DIR"/graphedit_r1_source.tar.gz.b64.part*)
if (( ${#parts[@]} == 0 )); then
  echo "ERROR: archive parts not found under $ARCHIVE_DIR" >&2
  exit 1
fi

# Git may check text files out with CRLF depending on core.autocrlf or
# repository/worktree settings. GNU base64 treats CR characters as invalid
# input, so normalize all ASCII whitespace before decoding. The SHA-256 check
# below still guarantees that no corrupted archive is accepted.
cat "${parts[@]}" \
  | LC_ALL=C tr -d '\r\n\t ' \
  | base64 --decode > "$ARCHIVE"

actual="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
if [[ "$actual" != "$EXPECTED" ]]; then
  echo "ERROR: SHA-256 mismatch" >&2
  echo "expected: $EXPECTED" >&2
  echo "actual:   $actual" >&2
  rm -f "$ARCHIVE"
  exit 1
fi

rm -rf "$ROOT/source"
tar -xzf "$ARCHIVE" -C "$ROOT"

echo "GraphEdit-R1 extracted successfully."
echo "Source: $ROOT/source"
echo "Read:   $ROOT/source/README.md"
