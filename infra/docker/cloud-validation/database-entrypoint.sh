set -euo pipefail
mkdir -p "$PGDATA"
if [[ ! -f "$PGDATA/PG_VERSION" ]]; then
  password_file=$(mktemp)
  chmod 600 "$password_file"
  printf '%s' "$POSTGRES_PASSWORD" > "$password_file"
  initdb --username="$POSTGRES_USER" --pwfile="$password_file" --auth-host=scram-sha-256 --auth-local=trust
  rm "$password_file"
  printf 'host all all all scram-sha-256\n' >> "$PGDATA/pg_hba.conf"
  pg_ctl -w start -o '-c listen_addresses=localhost -c shared_preload_libraries=timescaledb'
  createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
  pg_ctl -m fast -w stop
fi
exec postgres -c listen_addresses=0.0.0.0 -c shared_preload_libraries=timescaledb
