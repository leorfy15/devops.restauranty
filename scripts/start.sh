#!/bin/bash

set -e

RG="rg-restauranty-dev-tatiana"
AKS="aks-restauranty-dev"
NAMESPACE="restauranty"

echo "======================================"
echo " Starting Restauranty AKS"
echo "======================================"

echo "Starting AKS cluster..."

az aks start \
  --name "$AKS" \
  --resource-group "$RG"

echo "Getting AKS credentials..."

az aks get-credentials \
  --resource-group "$RG" \
  --name "$AKS" \
  --overwrite-existing

echo "Waiting for AKS nodes..."

kubectl wait \
  --for=condition=Ready \
  nodes \
  --all \
  --timeout=300s

echo "Nodes are ready."

kubectl get nodes

echo "Waiting for MongoDB..."

kubectl rollout status \
  deployment/mongodb \
  -n "$NAMESPACE" \
  --timeout=300s

echo "MongoDB is ready."

echo "Restarting backend services so they reconnect to MongoDB..."

kubectl rollout restart deployment/restauranty-auth -n "$NAMESPACE"
kubectl rollout restart deployment/restauranty-discounts -n "$NAMESPACE"
kubectl rollout restart deployment/restauranty-items -n "$NAMESPACE"

echo "Waiting for backend deployments..."

kubectl rollout status deployment/restauranty-auth \
  -n "$NAMESPACE" \
  --timeout=300s

kubectl rollout status deployment/restauranty-discounts \
  -n "$NAMESPACE" \
  --timeout=300s

kubectl rollout status deployment/restauranty-items \
  -n "$NAMESPACE" \
  --timeout=300s

echo "Waiting for frontend..."

kubectl rollout status deployment/restauranty-client \
  -n "$NAMESPACE" \
  --timeout=300s

echo ""
echo "======================================"
echo " Restauranty is ready"
echo "======================================"

kubectl get pods -n "$NAMESPACE"

echo ""
echo "Ingress:"
kubectl get ingress -n "$NAMESPACE"