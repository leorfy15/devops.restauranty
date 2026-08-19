#!/bin/bash

set -e

RG="rg-restauranty-dev-tatiana"
AKS="aks-restauranty-dev"
NAMESPACE="restauranty"

echo "======================================"
echo " Starting Restauranty AKS"
echo "======================================"

echo "Checking AKS cluster state..."

AKS_STATE=$(az aks show \
  --resource-group "$RG" \
  --name "$AKS" \
  --query "powerState.code" \
  -o tsv)

echo "Current AKS state: $AKS_STATE"

if [ "$AKS_STATE" = "Stopped" ]; then

  echo "Starting AKS cluster..."

  az aks start \
    --name "$AKS" \
    --resource-group "$RG"

elif [ "$AKS_STATE" = "Running" ]; then

  echo "AKS is already running. Skipping cluster start."

else

  echo "AKS is currently in state: $AKS_STATE"
  echo "Cannot safely continue."
  exit 1

fi


echo ""
echo "Getting AKS credentials..."

az aks get-credentials \
  --resource-group "$RG" \
  --name "$AKS" \
  --overwrite-existing


echo ""
echo "Waiting for AKS nodes..."

kubectl wait \
  --for=condition=Ready \
  nodes \
  --all \
  --timeout=300s

echo "Nodes are ready."

kubectl get nodes


echo ""
echo "Waiting for MongoDB deployment..."

kubectl rollout status \
  deployment/mongodb \
  -n "$NAMESPACE" \
  --timeout=300s


echo ""
echo "Waiting for MongoDB to accept connections..."

until kubectl exec deployment/mongodb \
  -n "$NAMESPACE" \
  -- mongosh --quiet \
  --eval 'db.adminCommand("ping").ok' \
  2>/dev/null | grep -q "1"
do
  echo "MongoDB is not ready yet..."
  sleep 5
done

echo "MongoDB is accepting connections."


echo ""
echo "Restarting backend services so they reconnect to MongoDB..."

kubectl rollout restart deployment/restauranty-auth \
  -n "$NAMESPACE"

kubectl rollout restart deployment/restauranty-discounts \
  -n "$NAMESPACE"

kubectl rollout restart deployment/restauranty-items \
  -n "$NAMESPACE"


echo ""
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


echo ""
echo "Backend deployments are healthy."

kubectl get deployment \
  restauranty-auth \
  restauranty-discounts \
  restauranty-items \
  -n "$NAMESPACE"


echo ""
echo "Waiting for frontend..."

kubectl rollout status deployment/restauranty-client \
  -n "$NAMESPACE" \
  --timeout=300s


echo ""
echo "======================================"
echo " Restauranty is ready"
echo "======================================"

echo ""
echo "Pods:"
kubectl get pods -n "$NAMESPACE"


echo ""
echo "HPA:"
kubectl get hpa -n "$NAMESPACE" || true


echo ""
echo "Ingress:"
kubectl get ingress -n "$NAMESPACE"


echo ""
echo "======================================"
echo " Startup completed successfully"
echo "======================================"