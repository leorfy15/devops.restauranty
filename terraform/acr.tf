resource "azurerm_container_registry" "restauranty" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.restauranty.name
  location            = azurerm_resource_group.restauranty.location

  sku           = "Basic"
  admin_enabled = false

  tags = var.tags
}