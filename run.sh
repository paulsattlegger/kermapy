#!/bin/sh
set -eu

TAG='kermapy:latest'

docker build --tag="$TAG" .
docker run --interactive --rm --tty \
--env='STORAGE_PATH=/app/data' \
--env='CLIENT_CONNECTIONS=0' \
--publish='127.0.0.1:18018:18018' \
--volume="$(pwd)/data:/app/data" \
"$TAG"