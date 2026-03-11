compose_file="${COMPOSE_FILE:-docker-compose.yml}"

docker compose -f "$compose_file" stop "$1"
docker compose -f "$compose_file" rm -f "$1"
docker compose -f "$compose_file" up --build -d "$1"
