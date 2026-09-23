#!/usr/bin/env bash
# Builds the custom Plane component images from this repo's Dockerfiles
# (same build contexts as build-images.sh) and pushes them to a Docker Hub
# namespace. All tags share a single IMAGE_TAG.
#
# Usage:
#   DOCKERHUB_NAMESPACE=<namespace> [IMAGE_TAG=<tag>] ./build-and-push-dockerhub.sh
#
# `proxy` is not built here; it is only needed for the docker-compose
# deployment shape (docker-compose-ecr.yml).
set -euo pipefail

DOCKERHUB_NAMESPACE="${DOCKERHUB_NAMESPACE:?DOCKERHUB_NAMESPACE must be set}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

build_and_push() {
  local component="$1" dockerfile="$2" context="$3"
  local ref="${DOCKERHUB_NAMESPACE}/plane-${component}:${IMAGE_TAG}"
  echo "Building ${ref} from ${dockerfile} (context: ${context})"
  docker build -f "$dockerfile" -t "$ref" "$context"
  echo "Pushing ${ref}"
  docker push "$ref"
}

build_and_push web apps/web/Dockerfile.web .
build_and_push admin apps/admin/Dockerfile.admin .
build_and_push space apps/space/Dockerfile.space .
build_and_push api apps/api/Dockerfile.api apps/api
build_and_push live apps/live/Dockerfile.live .

echo "Done. Pushed:"
for c in web admin space api live; do
  echo "  ${DOCKERHUB_NAMESPACE}/plane-${c}:${IMAGE_TAG}"
done
