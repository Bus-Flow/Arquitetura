variable "public_subnet_cidrs" {
    type            = list(string)
    description     = "Public Subnet CIDR values"
    default         = ["10.0.0.0/26", "10.0.0.64/26"]
}
variable "private_subnet_cidrs" {
    type            = list(string)
    description     = "Private Subnet CIDR values"
    default         = ["10.0.0.128/26", "10.0.0.192/26"]
}
variable "a_zones" {
    type            = list(string)
    description     = "Availability Zones"
    default         = ["us-east-1a", "us-east-1b"]
}
