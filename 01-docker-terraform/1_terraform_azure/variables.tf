variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
  default     = "ali-de-zoomcamp"
}

variable "location" {
  description = "The location of the resources"
  type        = string
  default     = "eastus"
}

variable "storage_account_name" {
  description = "The name of the storage account"
  type        = string
  default     = "alizoomcampsa"
}

variable "container_name" {
  description = "The name of the storage container"
  type        = string
  default     = "zoomcampcontainer"
}

variable "filesystem_name" {
  description = "The name of the Data Lake Gen2 filesystem"
  type        = string
  default     = "zoomcampfilesystem"
}

variable "synapse_workspace_name" {
  description = "The name of the Synapse workspace"
  type        = string
  default     = "alizoomcampsynapse"
}

variable "tags" {
  description = "Tags for the resources"
  type        = map(string)
  default = {
    environment = "dev"
    source      = "Terraform"
    owner       = "ali"
  }
}