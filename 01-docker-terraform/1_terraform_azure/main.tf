terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.0"
    }
  }
}

locals {
  credentials = jsondecode(file("./credentials/credentials.json"))
}

# Provides configuration details for the Azure Terraform provider
provider "azurerm" {
  features {}
}

# Retrieve subscription details
data "azurerm_subscription" "primary" {}

# Resource group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Storage account
resource "azurerm_storage_account" "sa" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  access_tier              = "Hot"
  is_hns_enabled           = "true"
  min_tls_version          = "TLS1_2"
}

# Storage Blob Contributor Role Assignment in Storage Account 
resource "azurerm_role_assignment" "role_assignment" {
  scope              = azurerm_storage_account.sa.id
  role_definition_id = "/subscriptions/${data.azurerm_subscription.primary.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe"
  principal_id       = local.credentials["principal_id"]
}

# Storage container
resource "azurerm_storage_container" "sc" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"

}

# Data Lake Gen2 filesystem for synapse
resource "azurerm_storage_data_lake_gen2_filesystem" "fs" {
  name               = var.filesystem_name
  storage_account_id = azurerm_storage_account.sa.id
}

# Synapse Workspace
resource "azurerm_synapse_workspace" "synapse" {
  name                                 = var.synapse_workspace_name
  resource_group_name                  = azurerm_resource_group.rg.name
  location                             = azurerm_resource_group.rg.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.fs.id
  sql_administrator_login              = local.credentials["synapse_sql_admin"]
  sql_administrator_login_password     = local.credentials["synapse_sql_password"]

  identity {
    type = "SystemAssigned"
  }
}

# Synapse Firewall
resource "azurerm_synapse_firewall_rule" "synapse_firewall" {
  name                 = "AllowAll"
  synapse_workspace_id = azurerm_synapse_workspace.synapse.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "255.255.255.255"
}