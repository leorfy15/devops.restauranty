#!/bin/bash

set -e

ACR="acrrestaurantytatiana.azurecr.io"
NAMESPACE="restauranty"

TAG=$(date +%Y%m%d%H%M%S)

echo "======================================"
echo " Restauranty deployment"
echo " Tag: $TAG"
echo "======================================"

echo "Logging into ACR..."

az acr login --name acrrestaurantytatiana

echo "Building and pushing AUTH..."

docker buildx build \
  --platform linux/amd64 \
  -t "$ACR/restauranty-auth:$TAG" \
  ./backend/auth \
  --push

echo "Building and pushing DISCOUNTS..."

docker buildx build \
  --platform linux/amd64 \
  -t "$ACR/restauranty-discounts:$TAG" \
  ./backend/discounts \
  --push

echo "Building and pushing ITEMS..."

docker buildx build \
  --platform linux/amd64 \
  -t "$ACR/restauranty-items:$TAG" \
  ./backend/items \
  --push

echo "Building and pushing CLIENT..."

docker buildx build \
  --platform linux/amd64 \
  -t "$ACR/restauranty-client:$TAG" \
  ./client \
  --push

echo "Updating Kubernetes deployments..."

kubectl set image \
  deployment/restauranty-auth \
  auth="$ACR/restauranty-auth:$TAG" \
  -n "$NAMESPACE"

kubectl set image \
  deployment/restauranty-discounts \
  discounts="$ACR/restauranty-discounts:$TAG" \
  -n "$NAMESPACE"

kubectl set image \
  deployment/restauranty-items \
  items="$ACR/restauranty-items:$TAG" \
  -n "$NAMESPACE"

kubectl set image \
  deployment/restauranty-client \
  client="$ACR/restauranty-client:$TAG" \
  -n "$NAMESPACE"

echo "Waiting for rollouts..."

kubectl rollout status deployment/restauranty-auth \
  -n "$NAMESPACE" \
  --timeout=300s

kubectl rollout status deployment/restauranty-discounts \
  -n "$NAMESPACE" \
  --timeout=300s

kubectl rollout status deployment/restauranty-items \
  -n "$NAMESPACE" \
  --timeout=300s

kubectl rollout status deployment/restauranty-client \
  -n "$NAMESPACE" \
  --timeout=300s

echo ""
echo "Deployment successful."
echo "Image tag: $TAG"

kubectl get pods -n "$NAMESPACE"