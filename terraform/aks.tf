resource "azurerm_kubernetes_cluster" "restauranty" {
  name                = var.aks_name
  location            = azurerm_resource_group.restauranty.location
  resource_group_name = azurerm_resource_group.restauranty.name

  dns_prefix = var.aks_name

  default_node_pool {
    name           = "system"
    node_count     = var.node_count
    vm_size        = var.node_vm_size
    vnet_subnet_id = azurerm_subnet.aks.id

    os_disk_size_gb = 30
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    network_policy = "azure"

    service_cidr   = "10.1.0.0/16"
    dns_service_ip = "10.1.0.10"

    outbound_type = "loadBalancer"
  }

  tags = var.tags
}


resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.restauranty.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.restauranty.id
  skip_service_principal_aad_check = true
}