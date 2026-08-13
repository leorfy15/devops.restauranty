output "resource_group_name" {
  description = "Resource Group name"
  value       = azurerm_resource_group.restauranty.name
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.restauranty.name
}

output "acr_name" {
  description = "Azure Container Registry name"
  value       = azurerm_container_registry.restauranty.name
}

output "acr_login_server" {
  description = "ACR login server"
  value       = azurerm_container_registry.restauranty.login_server
}

output "aks_subnet_id" {
  description = "AKS subnet ID"
  value       = azurerm_subnet.aks.id
}