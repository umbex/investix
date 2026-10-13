#!/usr/bin/env sh
set -eu

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 /absolute/path/to/backup-directory retention-days [--apply]" >&2
  exit 64
fi

directory=$1
retention_days=$2
mode=${3:-}
case "$directory" in
  /*) ;;
  *) echo "The backup directory must be an absolute path." >&2; exit 64 ;;
esac
case "$retention_days" in
  ''|*[!0-9]*) echo "Retention days must be a non-negative integer." >&2; exit 64 ;;
esac
if [ "$mode" != "" ] && [ "$mode" != "--apply" ]; then
  echo "The optional third argument must be --apply." >&2
  exit 64
fi
[ -d "$directory" ] || { echo "Backup directory not found." >&2; exit 66; }

if [ "$mode" = "--apply" ]; then
  # Deletion is opt-in; the default invocation is a read-only preview.
  find "$directory" -type f -name 'investix-*.sql.gz' -mtime "+$retention_days" -print -delete
else
  find "$directory" -type f -name 'investix-*.sql.gz' -mtime "+$retention_days" -print
fi
