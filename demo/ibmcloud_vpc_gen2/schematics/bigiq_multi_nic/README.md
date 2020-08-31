# F5 Networks BIG-IQ™ Instance Creation using Catalog image

This directory contains the terraform module to create BIG-IQ™ VPC Gen2 instances using catalog input from the user.

Use this template to create BIG-IQ™ virtual edition instnaces using catalog image from your IBM Cloud account in IBM Cloud [VPC Gen2](https://cloud.ibm.com/vpc-ext/overview) by using Terraform or IBM Cloud Schematics.  Schematics uses Terraform as the infrastructure-as-code engine.  With this template, you can create and manage infrastructure as a single unit as follows. For more information about how to use this template, see the IBM Cloud [Schematics documentation](https://cloud.ibm.com/docs/schematics).

## IBM Cloud IaaS Support

You're provided free technical support through the IBM Cloud™ community and Stack Overflow, which you can access from the Support Center. The level of support that you select determines the severity that you can assign to support cases and your level of access to the tools available in the Support Center. Choose a Basic, Advanced, or Premium support plan to customize your IBM Cloud™ support experience for your business needs.

Learn more: https://www.ibm.com/cloud/support

## Prerequisites

- Have access to [Gen 2 VPC](https://cloud.ibm.com/vpc-ext/).
- The given VPC must have at least one subnet with one IP address unassigned (up to 5 are supported)
- The BIG-IQ™ image name can reference the name of a custom image in your region or the public TMOS images available on IBM cloud.

## BIG-IQ™ images in IBM Cloud

BIG-IQ images are created as custom VPC images using the tools in the ```bigiq-cloudinit``` git hub repo. Once the custom BIG-IQ images are created in a VPC, use your BIG-IQ image name in the Schematics template.

For information on creating custom images for IBM cloud see [BIG-IQ Cloudinit](https://github.com/jgruberf5/bigiq-cloudinit)

**User variable:** ```bigiq_image_name```

If your regional custom image has the same name as the public image, your custom image will be used.

By default the BIG-IQ™ virtual edition instnace will be unlicensed. The user can choose to include a ```license_basekey``` to activate their BIG-IQ instance.

**User variable:** ```license_basekey```

## Device authentication

The user should create an SSH key in the IBM cloud region. The SSH key name should be included as a user variable.

**User Variable:** ```ssh_key_name```

Once the images completes onboarding, SSH access to the ```root``` user is available on the defined management Floating IP.

The user must also provide an ```admin``` user password.

**User Variable:** ```bigiq_admin_password```

If no ```bigiq_admin_password``` is provided, a randomized lengthy password will be set. The user can then access the device via SSH authorized key and set the ```admin``` password by using ```passwd admin```.

## Device Network Connectivity

Currently, IBM terraform resources do not provide the ability to obtain VPC subnets by their name. The user will have to know the subnet UUID as input variables.

At least one VPC subnet must be defined:

**User Variable:** ```management_subnet_id```

If only the ```management_subnet_id``` id defined, the BIG-IQ™ will be create as a 1NIC instance. The management UI and APIs can then be reached on port 8443 instead of the standard 443.

Up to five network interfaces can be added to a IBM VPC instnace. If you define additional subnet IDs, these will be mapped to BIG-IQ™ data interfaces starting with inteface ```1.1```

**User Variables:**

```data_1_1_subnet_id```
```data_1_2_subnet_id```
```data_1_3_subnet_id```
```data_1_4_subnet_id```

## CI Integration via Webhooks

When onboarding is complete, including optional licensing and network interface provisioning, the BIG-IQ™ can issue an HTTP(s) POST request to an URL specified by the user.

*User Variables:*

```phone_home_url```

The POST body will be JSON encoded and supply basic instance information:

```json
{
    "status": "SUCCESS",
    "product": "BIG-IQ",
    "version": "7.0.0.1.0.0.6",
    "hostname": "f5-test-bigiq-01.local",
    "id": "27096838-e85f-11ea-ac1c-feff0b2c5217",
    "management": "10.243.0.7/24",
    "metadata": {
        "template_source": "jgruberf5/bigiq-cloudinit/demo/ibmcloud_vpc_gen2/schematics/bigiq_multi_nic",
        "template_version": 20200825,
        "zone": "eu-de-1",
        "vpc": "r010-e27c516a-22ff-41f5-96b8-e8ea833fd39f",
        "app_id": "undefined"
    }
}
```

The user can optionally defined an ```app_id``` variable to tie this instnace for reference.

*User Variables:*

```app_id```

Once onboarding is complete, the user can than access the BIG-IQ™ Web UI, use iControl™ and REST API endpoints.

## Costs

When you apply template, the infrastructure resources that you create incur charges as follows. To clean up the resources, you can [delete your Schematics workspace or your instance](https://cloud.ibm.com/docs/schematics?topic=schematics-manage-lifecycle#destroy-resources). Removing the workspace or the instance cannot be undone. Make sure that you back up any data that you must keep before you start the deletion process.

*_VPC_: VPC charges are incurred for the infrastructure resources within the VPC, as well as network traffic for internet data transfer. For more information, see [Pricing for VPC](https://cloud.ibm.com/docs/vpc-on-classic?topic=vpc-on-classic-pricing-for-vpc).

## Dependencies

Before you can apply the template in IBM Cloud, complete the following steps.

1.  Ensure that you have the following permissions in IBM Cloud Identity and Access Management:
    * `Manager` service access role for IBM Cloud Schematics
    * `Operator` platform role for VPC Infrastructure
2.  Ensure the following resources exist in your VPC Gen 2 environment
    - VPC
    - SSH Key
    - VPC with multiple subnets
    - _(Optional):_ A Floating IP Address to assign to the management interface of Ubuntu 18.04 instance post deployment

## Configuring your deployment values

Create a schematics workspace and provide the github repository url (https://github.com/f5devcentral/tmos-cloudinit/tree/master/demo/ibmcloud_vpc_gen2/schematics/tmos_multi_nic) under settings to pull the latest code, so that you can set up your deployment variables from the `Create` page. Once the template is applied, IBM Cloud Schematics  provisions the resources based on the values that were specified for the deployment variables.

### Required values
Fill in the following values, based on the steps that you completed before you began.

| Key | Definition | Value Example |
| --- | ---------- | ------------- |
| `region` | The VPC region that you want your BIG-IQ™ to be provisioned. | us-south |
| `instance_name` | The name of the VNF instance to be provisioned. | f5-bigiq-01 |
| `bigiq_image_name` | The name of the VNF image  | big-iq-7-0-0-1-0-0-6 |
| `bigiq_admin_password` | The password to set for the BIG-IQ™ admin user. | valid BIG-IQ password |
| `instance_profile` | The profile of compute CPU and memory resources to be used when provisioning the BIG-IQ™ instance. To list available profiles, run `ibmcloud is instance-profiles`. | bx2-4x16 |
| `ssh_key_name` | The name of your public SSH key to be used. Follow [Public SSH Key Doc](https://cloud.ibm.com/docs/vpc-on-classic-vsi?topic=vpc-on-classic-vsi-ssh-keys) for creating and managing ssh key. | linux-ssh-key |
| `management_subnet_id` | The ID of the management subnet where the instance will be deployed. Click on the subnet details in the VPC Subnet Listing to determine this value | 0717-xxxxxx-xxxx-xxxxx-8fae-xxxxx |

### Optional values
Fill in the following values, based on the steps that you completed before you began.

| Key | Definition | Value Example |
| --- | ---------- | ------------- |
| `license_basekey` | The emailed license basekey from F5 for this BIG-IQ™ instance. | XXXXX-XXXXX-XXXXX-XXXXX-XXXXXXX |
| `data_1_1_subnet_id` | The ID of the first data subnet where the instance will be deployed. Click on the subnet details in the VPC Subnet Listing to determine this value | 0717-xxxxxx-xxxx-xxxxx-8fae-xxxxx |
| `data_1_2_subnet_id` | The ID of the first data subnet where the instance will be deployed. Click on the subnet details in the VPC Subnet Listing to determine this value | 0717-xxxxxx-xxxx-xxxxx-8fae-xxxxx |
| `data_1_3_subnet_id` | The ID of the first data subnet where the instance will be deployed. Click on the subnet details in the VPC Subnet Listing to determine this value | 0717-xxxxxx-xxxx-xxxxx-8fae-xxxxx |
| `data_1_4_subnet_id` | The ID of the first data subnet where the instance will be deployed. Click on the subnet details in the VPC Subnet Listing to determine this value | 0717-xxxxxx-xxxx-xxxxx-8fae-xxxxx |
| `phone_home_url` | The URL for post onboarding web hook  | https://webhook.site/#!/8c71ed42-da62-48ea-a2a5-265caf420a3b |
| `app_id` | Application ID used for CI integration | a044b708-66c4-4f50-a5c8-2b54eff5f9b5 |

## Notes

If there is any failure during VPC instance creation, the created resources must be destroyed before attempting to instantiate again. To destroy resources go to `Schematics -> Workspaces -> [Your Workspace] -> Actions -> Delete` to delete  all associated resources.

## Post F5 BIG-IQ™ Onboarding

1. From the VPC list, confirm the F5 BIG-IQ™ is powered ON with green button
2. From the CLI, run `ssh root@<Floating IP>`.
3. Enter 'yes' for continue connecting using ssh your key. This is the ssh key value, you specified in ssh_key variable.
