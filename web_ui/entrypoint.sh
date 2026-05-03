#!/bin/sh
# Bootstrap persistent state on the Fly volume, then exec the server.
#
# /data is the volume mount (see fly.toml). We point the registry's two on-disk
# locations — users.json and users/ — at the volume via symlinks so that user
# registrations and per-user token caches survive image redeploys.
set -e

mkdir -p /data/users
[ -f /data/users.json ] || printf '{"users": []}\n' > /data/users.json

ln -sfn /data/users.json /app/users.json
rm -rf /app/users
ln -sfn /data/users /app/users

exec "$@"
