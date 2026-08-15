#!/bin/bash

set -e

RG="rg-restauranty-dev-tatiana"
AKS="aks-restauranty-dev"

echo "Stopping Restauranty AKS..."

az aks stop \
  --name "$AKS" \
  --resource-group "$RG"

echo "AKS stopped."