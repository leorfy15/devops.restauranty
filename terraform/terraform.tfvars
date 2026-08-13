resource_group_name = "rg-restauranty-dev-tatiana"
location            = "westeurope"

vnet_name       = "vnet-restauranty-dev"
aks_subnet_name = "snet-aks"

aks_name = "aks-restauranty-dev"

acr_name = "acrrestaurantytatiana"

node_count   = 2
node_vm_size = "Standard_B2s"

tags = {
  project     = "restauranty"
  environment = "dev"
  managed_by  = "terraform"
}