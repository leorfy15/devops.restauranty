#!/bin/bash

set -euo pipefail

RESOURCE_GROUP="rg-restauranty-dev-tatiana"
AKS_CLUSTER="aks-restauranty-dev"
NAMESPACE="restauranty"

echo "Starting Restauranty AKS"

# Check current AKS state
AKS_STATE=$(az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query powerState.code \
  -o tsv)

echo "Current AKS state: $AKS_STATE"

# Start AKS if needed
if [ "$AKS_STATE" = "Stopped" ]; then
  echo "Starting AKS cluster..."

  az aks start \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --output none
else
  echo "AKS cluster is already running."
fi

# Wait for Azure-side AKS reconciliation
echo "Waiting for AKS operation to finish..."

for i in {1..60}; do

  STATUS=$(az aks operation show-latest \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --query status \
    -o tsv 2>/dev/null || true)

  if [ "$STATUS" = "Succeeded" ]; then
    echo "AKS operation completed."
    break
  fi

  if [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Canceled" ]; then
    echo "AKS operation failed with status: $STATUS"
    exit 1
  fi

  echo "AKS status: ${STATUS:-unknown} - waiting..."
  sleep 20

  if [ "$i" -eq 60 ]; then
    echo "Timed out waiting for AKS reconciliation."
    exit 1
  fi

done

# Get credentials
echo "Getting AKS credentials..."

az aks get-credentials \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --overwrite-existing \
  --output none

# Wait for system nodes
echo "Waiting for AKS nodes..."

kubectl wait \
  --for=condition=Ready \
  nodes \
  --all \
  --timeout=300s

kubectl get nodes

# Enable NAP
echo "Enabling Node Auto Provisioning..."

NAP_MODE=$(az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query nodeProvisioningProfile.mode \
  -o tsv)

if [ "$NAP_MODE" != "Auto" ]; then

  az aks update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --node-provisioning-mode Auto \
    --output none

else
  echo "NAP is already Auto."
fi

# Wait for NAP update
echo "Waiting for NAP configuration..."

for i in {1..60}; do

  NAP_MODE=$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --query nodeProvisioningProfile.mode \
    -o tsv)

  if [ "$NAP_MODE" = "Auto" ]; then
    echo "NAP is Auto."
    break
  fi

  sleep 10

  if [ "$i" -eq 60 ]; then
    echo "Timed out waiting for NAP Auto."
    exit 1
  fi

done

# Restore NAP NodePool limits
echo "Restoring NAP NodePool capacity..."

if kubectl get nodepool default >/dev/null 2>&1; then
  kubectl patch nodepool default \
    --type merge \
    -p '{"spec":{"limits":null}}'
fi

if kubectl get nodepool system-surge >/dev/null 2>&1; then
  kubectl patch nodepool system-surge \
    --type merge \
    -p '{"spec":{"limits":null}}'
fi

echo "NAP status:"
kubectl get nodepools || true
kubectl get nodeclaims || true

# Remove stale pods left by stopped nodes
echo "Checking for stale pods..."

STALE_PODS=$(kubectl get pods \
  -n "$NAMESPACE" \
  -o json | jq -r '
    .items[]
    | select(
        .status.phase == "Unknown"
        or any(
          .status.containerStatuses[]?;
          .state.terminated.reason == "ContainerStatusUnknown"
          or .state.waiting.reason == "ContainerStatusUnknown"
        )
      )
    | .metadata.name
  ')

if [ -n "$STALE_PODS" ]; then

  echo "Removing stale pods:"

  while read -r POD; do
    if [ -n "$POD" ]; then
      echo "Deleting $POD"
      kubectl delete pod "$POD" \
        -n "$NAMESPACE" \
        --grace-period=0 \
        --force || true
    fi
  done <<< "$STALE_PODS"

else
  echo "No stale pods found."
fi

# Wait for MongoDB
echo "Waiting for MongoDB..."

if ! kubectl rollout status deployment/mongodb \
  -n "$NAMESPACE" \
  --timeout=600s; then

  echo "MongoDB did not become ready."
  echo ""
  kubectl get pods -n "$NAMESPACE" -o wide
  echo ""
  kubectl get nodeclaims || true
  echo ""
  kubectl get events \
    -n "$NAMESPACE" \
    --sort-by=.lastTimestamp | tail -30

  exit 1
fi

echo "MongoDB is ready."

# Wait for Ollama
echo "Waiting for Ollama..."

if ! kubectl rollout status deployment/ollama \
  -n "$NAMESPACE" \
  --timeout=900s; then

  echo "Ollama did not become ready."
  echo ""
  kubectl get pods -n "$NAMESPACE" -o wide
  echo ""
  kubectl get events \
    -n "$NAMESPACE" \
    --sort-by=.lastTimestamp | tail -30

  exit 1
fi

echo "Ollama is ready."

# Wait for application deployments
echo "Waiting for Restauranty services..."

DEPLOYMENTS=(
  restauranty-auth
  restauranty-discounts
  restauranty-items
  restauranty-assistant
  restauranty-client
)

for DEPLOYMENT in "${DEPLOYMENTS[@]}"; do

  echo "Waiting for $DEPLOYMENT..."

  if ! kubectl rollout status \
    deployment/"$DEPLOYMENT" \
    -n "$NAMESPACE" \
    --timeout=600s; then

    echo "$DEPLOYMENT failed to become ready."

    kubectl get pods \
      -n "$NAMESPACE" \
      -o wide

    exit 1
  fi

done

echo ""
echo "Restauranty startup complete"
echo ""

echo "NAP:"
az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query nodeProvisioningProfile.mode \
  -o tsv

echo ""
echo "Nodes:"
kubectl get nodes

echo ""
echo "NodeClaims:"
kubectl get nodeclaims || true

echo ""
echo "Deployments:"
kubectl get deployments -n "$NAMESPACE"

echo ""
echo "Pods:"
kubectl get pods -n "$NAMESPACE"

echo ""
echo "Restauranty is ready."