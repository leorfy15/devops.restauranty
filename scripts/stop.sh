#!/bin/bash

set -e

RG="rg-restauranty-dev-tatiana"
AKS="aks-restauranty-dev"

echo "Stopping AKS cluster..."

az aks stop \
  --name "$AKS" \
  --resource-group "$RG"

echo "AKS cluster stopped."