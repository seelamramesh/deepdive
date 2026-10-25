#!/usr/bin/env bash
set -euo pipefail

: "${DEEPDIVE_PUBLIC_HOST:?Set deployment hostname}"
cd /docker/deepdive

if docker container inspect deepdive-rollback >/dev/null 2>&1; then
  echo "deepdive-rollback already exists; refusing to overwrite rollback"
  exit 1
fi

docker build -t deepdive:candidate .
docker stop deepdive
docker rename deepdive deepdive-rollback

rollback() {
  docker rm -f deepdive >/dev/null 2>&1 || true
  docker rename deepdive-rollback deepdive
  docker start deepdive >/dev/null
}

trap rollback ERR

docker run -d \
  --name deepdive \
  --restart unless-stopped \
  --env-file .env \
  --volume /docker/deepdive/data:/app/data \
  --network n8n_n8n_network \
  --label 'traefik.enable=true' \
  --label "traefik.http.routers.deepdive.rule=Host(\`$DEEPDIVE_PUBLIC_HOST\`)" \
  --label 'traefik.http.routers.deepdive.entrypoints=web,websecure' \
  --label 'traefik.http.routers.deepdive.tls=true' \
  --label 'traefik.http.routers.deepdive.tls.certresolver=mytlschallenge' \
  --label 'traefik.http.services.deepdive.loadbalancer.server.port=8000' \
  deepdive:candidate >/dev/null

for _ in $(seq 1 20); do
  status=$(docker inspect deepdive --format '{{.State.Health.Status}}' 2>/dev/null || true)
  if [ "$status" = "healthy" ]; then
    trap - ERR
    echo "candidate healthy; rollback preserved as deepdive-rollback"
    exit 0
  fi
  if [ "$status" = "unhealthy" ]; then
    false
  fi
  sleep 3
done

false
