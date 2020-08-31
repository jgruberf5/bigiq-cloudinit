# lookup SSH public keys by name
data "ibm_is_ssh_key" "ssh_pub_key" {
  name = "${var.ssh_key_name}"
}

# lookup compute profile by name
data "ibm_is_instance_profile" "instance_profile" {
  name = "${var.instance_profile}"
}

# create a random password if we need it
resource "random_password" "password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

# lookup image name for a custom image in region if we need it
data "ibm_is_image" "bigiq_custom_image" {
  name = "${var.bigiq_image_name}"
}

locals {
  # there are no public bigiq images
  public_image_map = {

  }
}

locals {
  admin_password = var.bigiq_admin_password == "" ? random_password.password.result : var.bigiq_admin_password
  # set user_data YAML values or else set them to null for templating
  phone_home_url          = var.phone_home_url == "" ? "null" : var.phone_home_url
  license_basekey         = var.license_basekey == "none" ? "null" : var.license_basekey
}

data "template_file" "user_data" {
  template = "${file("${path.module}/user_data.yaml")}"
  vars = {
    bigiq_admin_password    = local.admin_password
    license_basekey         = local.license_basekey
    phone_home_url          = local.phone_home_url
    template_source         = var.template_source
    template_version        = var.template_version
    zone                    = data.ibm_is_subnet.f5_managment_subnet.zone
    vpc                     = data.ibm_is_subnet.f5_managment_subnet.vpc
    app_id                  = var.app_id
  }
}

# create compute instance
resource "ibm_is_instance" "f5_ve_instance" {
  name    = var.instance_name
  image   = data.ibm_is_image.bigiq_custom_image.id
  profile = data.ibm_is_instance_profile.instance_profile.id
  primary_network_interface {
    name            = "management"
    subnet          = data.ibm_is_subnet.f5_managment_subnet.id
    security_groups = [ibm_is_security_group.f5_open_sg.id]
  }
  dynamic "network_interfaces" {
    for_each = local.secondary_subnets
    content {
      name            = format("data-1-%d", (network_interfaces.key + 1))
      subnet          = network_interfaces.value
      security_groups = [ibm_is_security_group.f5_open_sg.id]
    }

  }
  vpc        = data.ibm_is_subnet.f5_managment_subnet.vpc
  zone       = data.ibm_is_subnet.f5_managment_subnet.zone
  keys       = [data.ibm_is_ssh_key.ssh_pub_key.id]
  user_data  = data.template_file.user_data.rendered
  depends_on = [ibm_is_security_group_rule.f5_allow_outbound]
}

# create floating IP for management access
resource "ibm_is_floating_ip" "f5_management_floating_ip" {
  name   = "f0-${random_uuid.namer.result}"
  target = ibm_is_instance.f5_ve_instance.primary_network_interface.0.id
}

# create 1:1 floating IPs to vNICs - Not supported by IBM yet
#resource "ibm_is_floating_ip" "f5_data_floating_ips" {
#  count = length(local.secondary_subnets)
#  name   = format("f%d-%s", (count.index+1), random_uuid.namer.result)
#  target = ibm_is_instance.f5_ve_instance.network_interfaces[count.index].id
#}

output "resource_name" {
  value = ibm_is_instance.f5_ve_instance.name
}

output "resource_status" {
  value = ibm_is_instance.f5_ve_instance.status
}

output "VPC" {
  value = ibm_is_instance.f5_ve_instance.vpc
}

output "image_id" {
  value = data.ibm_is_image.bigiq_custom_image.id
}

output "instance_id" {
  value = ibm_is_instance.f5_ve_instance.id
}

output "profile_id" {
  value = data.ibm_is_instance_profile.instance_profile.id
}

output "f5_shell_access" {
  value = "ssh://root@${ibm_is_floating_ip.f5_management_floating_ip.address}"
}

output "f5_phone_home_url" {
  value = var.phone_home_url
}
