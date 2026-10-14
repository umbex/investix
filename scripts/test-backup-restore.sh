#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

sh -n scripts/backup.sh scripts/restore.sh scripts/prune-backups.sh
if scripts/restore.sh /tmp/missing-investix-backup.sql.gz investix >/dev/null 2>&1; then
  echo "restore protection check failed" >&2
  exit 1
fi

temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT
touch "$temporary_dir/investix-old.sql.gz" "$temporary_dir/other.sql.gz"
touch -t 202001010000 "$temporary_dir/investix-old.sql.gz"
preview=$(scripts/prune-backups.sh "$temporary_dir" 30)
printf '%s\n' "$preview" | grep -F "$temporary_dir/investix-old.sql.gz" >/dev/null
test -f "$temporary_dir/investix-old.sql.gz"

if [ "${RUN_DOCKER_TESTS:-0}" = "1" ]; then
  backup_path="$temporary_dir/investix-docker-test.sql.gz"
  target_database="investix_restore_check_$$"
  scripts/backup.sh "$backup_path"
  scripts/restore.sh "$backup_path" "$target_database"
fi

echo "Backup/restore checks passed (set RUN_DOCKER_TESTS=1 for PostgreSQL integration)."
