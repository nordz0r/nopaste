docker compose stop $1
docker compose rm -f $1
docker compose up --build -d $1
