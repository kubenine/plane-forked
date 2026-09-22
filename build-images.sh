#!/usr/bin/env bash
set -euo pipefail

# Local build only — no push. Tags images as ECR_REGISTRY:<component>-IMAGE_TAG
# (single shared repo, component-prefixed tags) so they line up with
# docker-compose-ecr.yml once you're ready to push.

ECR_REGISTRY="${ECR_REGISTRY:-local/plane-staging}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "Building images as ${ECR_REGISTRY}:<component>-${IMAGE_TAG}"

docker build \
  -f apps/web/Dockerfile.web \
  -t "${ECR_REGISTRY}:web-${IMAGE_TAG}" \
  .

docker build \
  -f apps/admin/Dockerfile.admin \
  -t "${ECR_REGISTRY}:admin-${IMAGE_TAG}" \
  .

docker build \
  -f apps/space/Dockerfile.space \
  -t "${ECR_REGISTRY}:space-${IMAGE_TAG}" \
  .

docker build \
  -f apps/api/Dockerfile.api \
  -t "${ECR_REGISTRY}:api-${IMAGE_TAG}" \
  apps/api

docker build \
  -f apps/live/Dockerfile.live \
  -t "${ECR_REGISTRY}:live-${IMAGE_TAG}" \
  .

docker build \
  -f apps/proxy/Dockerfile.ce \
  -t "${ECR_REGISTRY}:proxy-${IMAGE_TAG}" \
  apps/proxy

echo "Done. Images built locally, nothing pushed."
docker images | grep "plane-staging" || true
