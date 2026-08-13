#!/bin/bash

set -e

RG="rg-restauranty-dev-tatiana"
AKS="aks-restauranty-dev"

echo "Starting AKS cluster..."

az aks start \
  --name "$AKS" \
  --resource-group "$RG"

echo "Getting AKS credentials..."

az aks get-credentials \
  --resource-group "$RG" \
  --name "$AKS" \
  --overwrite-existing

echo "Waiting for nodes..."

kubectl wait \
  --for=condition=Ready \
  nodes \
  --all \
  --timeout=300s

echo "AKS is ready."

kubectl get nodes
kubectl get pods -n restauranty