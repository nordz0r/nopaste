compose_file="${COMPOSE_FILE:-docker-compose.yml}"

docker compose -f "$compose_file" logs -f --tail=50 "$1"
