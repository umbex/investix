#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 /absolute/path/to/backup.sql.gz target_database" >&2
  exit 64
fi

source=$1
target=$2
case "$source" in
  /*) ;;
  *) echo "The backup source must be an absolute path." >&2; exit 64 ;;
esac
[ -f "$source" ] || { echo "Backup file not found." >&2; exit 66; }
case "$target" in
  investix|postgres|template0|template1) echo "Refusing to restore into a protected database." >&2; exit 64 ;;
esac

environment_file=${INVESTIX_ENV_FILE:-.env}
docker compose --env-file "$environment_file" exec -T db createdb -U "${POSTGRES_USER:-investix}" "$target"
gzip -dc "$source" | docker compose --env-file "$environment_file" exec -T db psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-investix}" -d "$target"
echo "Restore verified into temporary database $target"
