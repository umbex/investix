#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /absolute/path/to/backup.sql.gz" >&2
  exit 64
fi

destination=$1
case "$destination" in
  /*) ;;
  *) echo "The backup destination must be an absolute path." >&2; exit 64 ;;
esac

mkdir -p "$(dirname "$destination")"
environment_file=${INVESTIX_ENV_FILE:-.env}
temporary="${destination}.partial"
trap 'rm -f "$temporary"' EXIT
docker compose --env-file "$environment_file" exec -T db pg_dump -U "${POSTGRES_USER:-investix}" "${POSTGRES_DB:-investix}" > "$temporary"
gzip -c "$temporary" > "$destination"
rm -f "$temporary"
trap - EXIT
echo "Backup written to $destination"
