resource "azurerm_virtual_network" "restauranty" {
  name                = var.vnet_name
  location            = azurerm_resource_group.restauranty.location
  resource_group_name = azurerm_resource_group.restauranty.name

  address_space = [
    "10.0.0.0/16"
  ]

  tags = var.tags
}

resource "azurerm_subnet" "aks" {
  name                 = var.aks_subnet_name
  resource_group_name  = azurerm_resource_group.restauranty.name
  virtual_network_name = azurerm_virtual_network.restauranty.name

  address_prefixes = [
    "10.0.1.0/24"
  ]
}