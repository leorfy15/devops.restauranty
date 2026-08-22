#!/bin/bash

set -euo pipefail

RESOURCE_GROUP="rg-restauranty-dev-tatiana"
AKS_CLUSTER="aks-restauranty-dev"

echo "Stopping Restauranty AKS"

# Check AKS state
AKS_STATE=$(az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query powerState.code \
  -o tsv)

if [ "$AKS_STATE" = "Stopped" ]; then
  echo "AKS is already stopped."
  exit 0
fi

echo "Current AKS state: $AKS_STATE"

# Check NAP
NAP_MODE=$(az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query nodeProvisioningProfile.mode \
  -o tsv)

echo "Current NAP mode: $NAP_MODE"

if [ "$NAP_MODE" = "Auto" ]; then

  echo "Preventing NAP from creating new nodes..."

  if kubectl get nodepool default >/dev/null 2>&1; then
    kubectl patch nodepool default \
      --type merge \
      -p '{"spec":{"limits":{"cpu":"0"}}}'
  fi

  if kubectl get nodepool system-surge >/dev/null 2>&1; then
    kubectl patch nodepool system-surge \
      --type merge \
      -p '{"spec":{"limits":{"cpu":"0"}}}'
  fi

  echo "Waiting for NAP NodeClaims to disappear..."

  for i in {1..60}; do

    CLAIM_COUNT=$(kubectl get nodeclaims \
      --no-headers 2>/dev/null | wc -l | tr -d ' ')

    if [ "$CLAIM_COUNT" = "0" ]; then
      echo "All NAP NodeClaims removed."
      break
    fi

    echo "$CLAIM_COUNT NodeClaim(s) still present."

    kubectl get nodeclaims || true

    sleep 10

    if [ "$i" -eq 60 ]; then
      echo ""
      echo "NAP NodeClaims did not disappear within 10 minutes."
      echo "AKS will NOT be changed to Manual automatically."
      echo ""
      echo "Current NodeClaims:"
      kubectl get nodeclaims || true
      echo ""
      echo "Investigate before continuing shutdown."
      exit 1
    fi

  done

  echo "Switching NAP to Manual..."

  az aks update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --node-provisioning-mode Manual \
    --output none

fi

# Verify Manual mode
echo "Verifying NAP mode..."

for i in {1..60}; do

  NAP_MODE=$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --query nodeProvisioningProfile.mode \
    -o tsv)

  if [ "$NAP_MODE" = "Manual" ]; then
    echo "NAP is Manual."
    break
  fi

  echo "NAP mode: $NAP_MODE - waiting..."

  sleep 10

  if [ "$i" -eq 60 ]; then
    echo "Timed out waiting for NAP Manual."
    exit 1
  fi

done

# Stop AKS
echo "Stopping AKS cluster..."

az aks stop \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --output none

# Verify stopped
echo "Waiting for AKS to stop..."

for i in {1..60}; do

  AKS_STATE=$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --query powerState.code \
    -o tsv)

  echo "AKS state: $AKS_STATE"

  if [ "$AKS_STATE" = "Stopped" ]; then
    echo ""
    echo "Restauranty AKS stopped successfully."
    exit 0
  fi

  sleep 15

done

echo "Timed out waiting for AKS to stop."
exit 1