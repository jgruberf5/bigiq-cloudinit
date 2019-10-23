# bigiq-cloudinit
### Cloudinit Modules and Patching for F5 BIG-IQ ###

F5 BIG-IQ is secured operating system designed for deployment as a network appliance. While BIG-IQ utilizes a CentOS-based kernel and linux-based control processes to bootstrap and configure service resources, it has been highly customized from typical linux distributions.

Linux distributions use a standard bootstrapping agent known as cloudinit to integrate cloud infrastructure metadata with the system's init processes. BIG-IQ deos not support the use of cloud-init natively. In an attempt to BIG-IQ deployments to take advantage of standard cloud infrastructure cloud-init metadata, this repository contains the needed tools to file-inject both python and Ansible based resources into BIG-IQ images. Once appropriately patch, BIG-IQ images can support onboarding via cloud-init.

## Patching BIG-IQ Virtual Edition Images to Install Cloudinit Modules - Using a Docker Instance ##

This repository includes a Dockerfile and patch scripts that enable you to build a Docker instance capable of patching standard BIG-IQ images from `downloads.f5.com` so that they will include additional cloudinit modules.

From the F5 Downloads site, download all image(s) you wish to patch with these cloudinit modules to a directory available as a volume mount to your docker instance (see mounts below).

```
ls /data/BIGIQ-7.0
BIG-IQ-7.0.0.1.0.0.6.LARGE.qcow2.zip
BIG-IQ-7.0.0.1.0.0.6.qcow2.zip
```

#### Note: do not remove the disk images from their archive containers (zip or ova). The utilities in the container do that as part of the image patching process. ####

Build the docker image from the `bigiq_image_patcher` Dockerfile.

```
$ docker build -t bigiq_image_patcher:latest bigiq_image_patcher
```

This will download a vanilla Ubuntu 18.04 container, install all the necessary open source utilities required to patch BIG-IQ images, and designate the python script which performs the image patching as the execution entry point for the container image.

After the build completes, a docker image will be available locally.

```
$ docker images | grep bigiq_image_patcher
bigiq_image_patcher    latest    baa2d957ec0d    22 seconds ago    1.4GB
```

Patched images can then be built by running a `bigiq_image_builder` docker container instance with the correct volume mounts and `image_patch_file` directory structure defined.

The `bigiq_image_builder` container uses open source tools to:

- decompress the downloaded BIG-IQ image archive for all archives found in the `/BIGIQImages` volume mount (see mounts below) directory
- bind the BIG-IQ disk image partitions
- mount the logical volumes for `/config`, `/usr`, `/var`, and `/shared` from the bound BIG-IQ file systems
- copies files specified in the `image_path_files` file directory structure into the BIG-IQ image
- creates a distribution archive ready for upload to your virtualization image storage services

When you run the `bigiq_image_patcher` container from this repository's root directory, it will find the `image_path_files` directory structure and patch your images with the files found within. This repository's `image_path_files` directory structure is designed to inject all three of `bigiq-cloudinit` modules and patch the `/config/startup` configuration file to load the `bigiq-cloudinit` modules properly when BIG-IQ boots.

The open source tools used in the container are all user space utilities, thus the container requires no special privileges other then write access to the directory where your downloaded BIG-IQ disk archives are mounted (`/BIGIQImages` see below).

#### Expected Docker Volume Mounts for the `tmos_image_builder` Container ####

The docker container uses the mount points listed below. Your BIG-IQ image archives folder should be mounted as a volume to the container's `/BIGIQImages` directory. 

| Docker Volume Mount | Required | Description |
| --------------------- | ----- | ---------- |
| /BIGIQImages   | Yes | Path to the directory with the BIG-IQ Virtual Edition archives to patch |

#### Example Mounts ####

`
-v /data/BIGIQ-7.0:/BIGIQImages 
`

You can run the image patch script with the Docker `run` command.

```
$ docker run --rm -it -v /data/BIGIQ-7.0:/BIGIQImages bigiq_image_patcher:latest


...
2019-10-14 19:20:26,283 - bigiq_image_patcher - DEBUG - process start time: Monday, October 14, 2019 07:20:26
2019-10-14 19:20:26,283 - bigiq_image_patcher - INFO - Scanning for images in: /BIGIQImages
2019-10-14 19:20:26,283 - bigiq_image_patcher - INFO - BIGIQ cloudinit modules sourced from: /bigiq-cloudinit
2019-10-14 19:20:26,284 - bigiq_image_patcher - INFO - Patching BIGIQ /var file system from: /bigiq-cloudinit/image_patch_files/var
2019-10-14 19:20:26,284 - bigiq_image_patcher - INFO - Patching BIGIQ /config file system from: /bigiq-cloudinit/image_patch_files/config
2019-10-14 19:20:26,284 - bigiq_image_patcher - DEBUG - extracting /BIGIQImages/BIG-IQ-7.0.0.1.0.0.6.qcow2.zip to /BIGIQImages/BIG-IQ-7.0.0.1.0.0.6.qcow2
2019-10-14 19:20:49,497 - bigiq_image_patcher - DEBUG - extracting /BIGIQImages/BIG-IQ-7.0.0.1.0.0.6.LARGE.qcow2.zip to /BIGIQImages/BIG-IQ-7.0.0.1.0.0.6.LARGE.qcow2
2019-10-14 19:21:39,111 - bigiq_image_patcher - INFO - pulling latest cloudinit modules
2019-10-14 19:21:39,408 - bigiq_image_patcher - INFO - git returned: ['Already up to date.', '']
2019-10-14 19:21:52,804 - bigiq_image_patcher - DEBUG - injecting files into /usr/local/lib/python2.7
2019-10-14 19:21:52,805 - bigiq_image_patcher - DEBUG - injecting __init__.py to /usr/local/lib/python2.7/site-packages/cloudinit/__init__.py
2019-10-14 19:21:52,847 - bigiq_image_patcher - DEBUG - injecting bigiq_onboard_utils.py to /usr/local/lib/python2.7/site-packages/cloudinit/bigiq_onboard_utils.py
2019-10-14 19:21:52,851 - bigiq_image_patcher - DEBUG - injecting cc_set_passwords.py to /usr/local/lib/python2.7/site-packages/cloudinit/config/cc_set_passwords.py
2019-10-14 19:21:52,863 - bigiq_image_patcher - DEBUG - injecting cc_bigiq_dhcpv4_tmm.py to /usr/local/lib/python2.7/site-packages/cloudinit/config/cc_bigiq_dhcpv4_tmm.py
2019-10-14 19:21:52,867 - bigiq_image_patcher - DEBUG - injecting cc_bigiq_static_mgmt.py to /usr/local/lib/python2.7/site-packages/cloudinit/config/cc_bigiq_static_mgmt.py
2019-10-14 19:21:52,869 - bigiq_image_patcher - DEBUG - injecting __init__.py to /usr/local/lib/python2.7/site-packages/cloudinit/config/__init__.py
2019-10-14 19:21:52,871 - bigiq_image_patcher - DEBUG - injecting cc_bigiq_configdrive_openstack.py to /usr/local/lib/python2.7/site-packages/cloudinit/config/cc_bigiq_configdrive_openstack.py
2019-10-14 19:21:58,548 - bigiq_image_patcher - DEBUG - injecting files into /var
2019-10-14 19:22:11,965 - bigiq_image_patcher - DEBUG - injecting onboard.yml to /var/lib/cloud/ansible/onboard.yml
2019-10-14 19:22:11,989 - bigiq_image_patcher - DEBUG - injecting ansible.cfg to /var/lib/cloud/ansible/ansible.cfg
2019-10-14 19:22:11,992 - bigiq_image_patcher - DEBUG - injecting inventory to /var/lib/cloud/ansible/inventory
2019-10-14 19:22:11,994 - bigiq_image_patcher - DEBUG - injecting main.yml to /var/lib/cloud/ansible/roles/onboard/meta/main.yml
2019-10-14 19:22:11,997 - bigiq_image_patcher - DEBUG - injecting main.yml to /var/lib/cloud/ansible/roles/onboard/handlers/main.yml
2019-10-14 19:22:12,000 - bigiq_image_patcher - DEBUG - injecting main.yml to /var/lib/cloud/ansible/roles/onboard/vars/main.yml
2019-10-14 19:22:12,003 - bigiq_image_patcher - DEBUG - injecting main.yml to /var/lib/cloud/ansible/roles/onboard/defaults/main.yml
2019-10-14 19:22:12,005 - bigiq_image_patcher - DEBUG - injecting main.yml to /var/lib/cloud/ansible/roles/onboard/tasks/main.yml
2019-10-14 19:22:12,008 - bigiq_image_patcher - DEBUG - injecting masterpassphrase.yml to /var/lib/cloud/ansible/roles/onboard/tasks/masterpassphrase.yml
2019-10-14 19:22:12,011 - bigiq_image_patcher - DEBUG - injecting finalize.yml to /var/lib/cloud/ansible/roles/onboard/tasks/finalize.yml
2019-10-14 19:22:12,013 - bigiq_image_patcher - DEBUG - injecting discovery.yml to /var/lib/cloud/ansible/roles/onboard/tasks/discovery.yml
2019-10-14 19:22:12,018 - bigiq_image_patcher - DEBUG - injecting nodetype.yml to /var/lib/cloud/ansible/roles/onboard/tasks/nodetype.yml
2019-10-14 19:22:12,021 - bigiq_image_patcher - DEBUG - injecting license.yml to /var/lib/cloud/ansible/roles/onboard/tasks/license.yml
2019-10-14 19:22:17,571 - bigiq_image_patcher - DEBUG - injecting files into /config
2019-10-14 19:22:30,375 - bigiq_image_patcher - DEBUG - injecting startup to /config/startup

```

Each BIG-IQ image archive will be expanded into a folder containing the patched image. The folder will have the same name as the archive file without the extension. The patched image, in the expanded folder, will be in the same format as the original. You can utilize the patched images just as you would the originals.

<pre>
> $ tree /data/BIGIQ-7.0
/data/BIGIQ-7.0/
├── BIG-IQ-7.0.0.1.0.0.6.LARGE.qcow2
│   ├── BIG-IQ-7.0.0.1.0.0.6.DATASTOR.ALL.qcow2
│   └── BIG-IQ-7.0.0.1.0.0.6.qcow2
├── BIG-IQ-7.0.0.1.0.0.6.LARGE.qcow2.zip
├── BIG-IQ-7.0.0.1.0.0.6.qcow2
│   └── BIG-IQ-7.0.0.1.0.0.6.qcow2
└── BIG-IQ-7.0.0.1.0.0.6.qcow2.zip
</pre>

As an example, your patched image could then be uploaded for use in an OpenStack private cloud.

```
$ openstack image create --disk-format qcow2 --container-format bare --file /data/BIGIQ-7.0/BIG-IQ-7.0.0.1.0.0.6.qcow2/BIG-IQ-7.0.0.1.0.0.6.qcow2 OpenStack_BIG-IQ-7.0.0.1.0.0.6
+------------------+------------------------------------------------------+
| Field            | Value                                                |
+------------------+------------------------------------------------------+
| checksum         | 091479c864d1086a66b51891c7b20fbb                     |
| container_format | bare                                                 |
| created_at       | 2019-10-14T19:26:51Z                                 |
| disk_format      | qcow2                                                |
| file             | /v2/images/cd5a5bef-c208-4465-98be-dcb2149f870d/file |
| id               | cd5a5bef-c208-4465-98be-dcb2149f870d                 |
| min_disk         | 0                                                    |
| min_ram          | 0                                                    |
| name             | OpenStack_BIG-IQ-7.0.0.1.0.0.6                       |
| owner            | e99a23ab9e004975a3ea09a2b8037257                     |
| protected        | False                                                |
| schema           | /v2/schemas/image                                    |
| size             | 4294705152                                           |
| status           | active                                               |
| tags             |                                                      |
| updated_at       | 2019-10-14T19:27:28Z                                 |
| virtual_size     | None                                                 |
| visibility       | shared                                               |
+------------------+------------------------------------------------------+

```

Once your patched images are deployed in your virtualized environment, you can use cloudinit userdata to handle initial device and service provisioning.


## Which Cloudinit Module Should You Use? ##

Each module handles very specific use cases. Each use case aquires the per-instance configuration data from different resources.

| Module | Aquires Per-Instance Config From | Provisions |
| --------------------- | ----------------- | ---------- |
| bigiq_static_mgmt   | cloudinit YAML declaration | Provisions the management interface statically from cloudinit YAML. |
| bigiq_configdrive_openstack  | OpenStack metadata, and cloudinit YAML declaration | Provisions the management interface and TMM interfaces from OpenStack metadata. |
| biqiq_dhcpv4_tmm   | DHCPv4 requests on all interfaces, and cloudinit YAML declaration | Provisions the management interface and TMM interfacs from DHCPv4 lease information.|

You should use the module which matches your sources of per-instance configuration data.

## The bigiq_static_mgmt Cloudinit Module ##

This cloudinit module extends BIG-IQ Virtual Edition to allow for static address assignment provided through cloudinit userdata.

This modules create initialization scripts containing `tmsh` commands to fulfill the specified configurations. The generated initialization scripts are created in the `/opt/cloud/bigiq_static_mgmt` directory on the BIG-IP device.

| Module Attribute | Default | Description|
| --------------------- | -----------| ---------------|
| enabled              | false      | Activates ths module|
| ip         | none (required)        | The management IP address or CIDR. |
| netmask | none | The management IP netmask, only required if the IP is not CIDR. |
| gw | none | The management default gateway IP address. |
| mtu | 1500 | The management link MTU. |
| hostname | none | The hostname in FQDN format (host and domain) to assign. |
| nameservers | list | List of DNS server IP addresses. |
| searchdomain | none | A single search domain to assign. |
| ntpservers | list | List of NTP server FQDNs or IP addresses. |
| license_key | None | Will auto license the BIG-IQ - requires Internet connection |
| node_type | None | Can define the BIG-IQ as either 'cm' or 'dcd' |
| post_onboard_enabled | false | Enabled the attempt to run a list of commands after onboarding completes. |
| post_onboard_commands | list | List of CLI commands to run in order. Execution will halt at the point a CLI command fails. |
| phone_home_url | url | Reachable URL to report completion of this modules onboarding. |
| phone_home_url_verify_tls | true | If the phone_home_url uses TLS, verify the host certificate. |
| phone_home_cli | cli command | CLI command to run when this modules completes successfully. |

#### Note: The `bigiq_static_mgmt` module can be used in conjunction with the `tmos_dhcpv4_tmm` module to add managment interface provisioning before DHCP v4 requests are made. ####


### userdata usage ###

```
#cloud-config
bigiq_static_mgmt:
  enabled: true
  ip: 192.168.245.100
  netmask: 255.255.255.0
  gw: 192.168.245.1
  mtu: 1450
  license_key: QDLSY-UKPYSP-PCG-GVYMYGH-BZPZMUR
  node_type: cm
  post_onboard_enabled: true
  post_onboard_commands:
    - tmsh save sys config
  phone_home_url: https://webhook.site/5f8cd8a7-b051-4648-9296-8f6afad34c93
  phone_home_cli: "curl -i -X POST -H 'X-Auth-Token: gAAAAABc5UscwS1py5XfC3yPcyN8KcgD7hYtEZ2-xHw95o4YIh0j5IDjAu9qId3JgMOp9hnHwP42mYA7oPPP0yl-OQXvCaCS3OezKlO7MsS-ZCTJzuS3sSysIMHTA78fGsXbMgCQZCi5G-evLG9xUNrYp5d3blhMnpHR0dlHPz6VMacNkPhyrQI' -H 'Content-Type: application/json' -H 'Accept: application/json' http://192.168.0.121:8004/v1/d3779c949b57403bb7f703016e91a425/stacks/demo_waf/3dd6ce45-bb8c-400d-a48c-87ac9e46e60e/resources/wait_handle/signal"
```

## The bigiq_configdrive_openstack Cloudinit Module ##

This cloudinit module requries the use of a ConfigDrive data source and OpenStack file formatted meta_data.json and network_data.json metadata files. This module extends BIG-IQ functionality to include static provisioning of all interfaces (management and TMM) via either network metadata or the use of DHCPv4.

There are implicit declarations of the TMM interfaces names to use for the data plane default route and the device discovery interfaces. If these declarations are omitted, the module will attempt to assign them dynamically based on available network configuration data.

This module creates initialization scripts containing `tmsh` commands to fulfil the specified configurations. The generated initialization scripts will be created in the `/opt/cloud/bigiq_configdrive_openstack` directory on the device.


| Module Attribute | Default | Description|
| --------------------- | -----------| ---------------|
| enabled              | false      | Activates ths module|
| rd_enabled         | true        | Automatically create route domains when needed |
| device_discovery_interface | 1.1 | Sets the TMM interface name to use for device discovery |
| default_route_interface | none | Explicitly define the TMM interface to use for the default route. If unspecified, one will be determined automatically |
| dhcp_timeout | 120 | Seconds to wait for a DHCP response when using DHCP for resource discovery |
| inject_routes | true | Creates static routes from discovered route resources |
| license_key | None | Will auto license the BIG-IQ - requires Internet connection |
| node_type | None | Can define the BIG-IQ as either 'cm' or 'dcd' |
| post_onboard_enabled | false | Enable the attempt to run a list of commands after onboarding completes |
| post_onboard_commands | list | List of CLI commands to run in order. Execution will halt at the point a CLI command fails. |
| phone_home_url | url | Reachable URL to report completion of this modules onboarding. |
| phone_home_url_verify_tls | true | If the phone_home_url uses TLS, verify the host certificate. |
| phone_home_cli | cli command | CLI command to run when this modules completes successfully. |

SSH keys found in the OpenStack meta_data.json file will also be injected as authorized_keys for the root account.

### userdata usage ###

```
#cloud-config
bigiq_configdrive_openstack:
  enabled: true
  rd_enabled: false
  device_discovery_interface: 1.1
  default_route_interface: 1.3
  dhcp_timeout: 120
  inject_routes: true
  license_key: QDLSY-UKPYSP-PCG-GVYMYGH-BZPZMUR
  node_type: cm
  post_onboard_enabled: false
  phone_home_url: https://webhook.site/5f8cd8a7-b051-4648-9296-8f6afad34c93
  phone_home_cli: "curl -i -X POST -H 'X-Auth-Token: gAAAAABc5UscwS1py5XfC3yPcyN8KcgD7hYtEZ2-xHw95o4YIh0j5IDjAu9qId3JgMOp9hnHwP42mYA7oPPP0yl-OQXvCaCS3OezKlO7MsS-ZCTJzuS3sSysIMHTA78fGsXbMgCQZCi5G-evLG9xUNrYp5d3blhMnpHR0dlHPz6VMacNkPhyrQI' -H 'Content-Type: application/json' -H 'Accept: application/json' http://192.168.0.121:8004/v1/d3779c949b57403bb7f703016e91a425/stacks/demo_waf/3dd6ce45-bb8c-400d-a48c-87ac9e46e60e/resources/wait_handle/signal"
```

In addition to the declared elements, this module also supports `cloud-config` declarations for `ssh_authorized_keys`. Any declared keys will be authorized for the BIG-IQ root account.

```
#cloud-config
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAGEA3FSyQwBI6Z+nCSjUUk8EEAnnkhXlukKoUPND/RRClWz2s5TCzIkd3Ou5+Cyz71X0XmazM3l5WgeErvtIwQMyT1KjNoMhoJMrJnWqQPOt5Q8zWd9qG7PBl9+eiH5qV7NZ mykey@host
```

## The bigiq_dhcpv4_tmm Cloudinit Module ##

This cloudinit module resolves configuration data for all interfaces (management and TMM) through DHCPv4. All interfaces should be connected to networks with DHCPv4 services.

There are implicit declarations of the TMM inteface names to use for the data plane default route and the device discovery interfaces. If these declarations are omitted, the module will attempt to assign them dynamically based on available network configuration data.

This module creates initialization scripts containing BIG-IQ `tmsh` commands to fulfil the specified configurations. The generated initialization scripts are created in the `/opt/cloud/bigiq_dhcpv4_tmm` directory on the device.

| Module Attribute | Default | Description|
| --------------------- | -----------| ---------------|
| enabled              | false      | Activates ths module|
| rd_enabled         | true        | Automatically create route domains when needed |
| device_discovery_interface | 1.1 | Sets the TMM interface name to use for configsync |
| default_route_interface | none | Explicitly define the TMM interface to use for the default route. Otherwise one will be determined automatically |
| dhcp_timeout | 120 | Seconds to wait for a DHCP response when using DHCP for resource discovery |
| inject_routes | true | Creates static routes from discovered route resources |
| license_key | None | Will auto license the BIG-IQ - requires Internet connection |
| node_type | None | Can define the BIG-IQ as either 'cm' or 'dcd' |
| post_onboard_enabled | false | Enable the attempt to run a list of commands after onboarding completes |
| post_onboard_commands | list | List of CLI commands to run in order. Execution will halt at the point a CLI command fails. |
| phone_home_url | url | Reachable URL to report completion of this modules onboarding. |
| phone_home_url_verify_tls | true | If the phone_home_url uses TLS, verify the host certificate. |
| phone_home_cli | cli command | CLI command to run when this modules completes successfully. |

### userdata usage ###

```
#cloud-config
bigiq_dhcpv4_tmm:
  enabled: true
  rd_enabled: false
  device_discovery_interface: 1.1
  default_route_interface: 1.3
  dhcp_timeout: 120
  inject_routes: true
  license_key: QDLSY-UKPYSP-PCG-GVYMYGH-BZPZMUR
  node_type: cm
  post_onboard_enabled: true
  post_onboard_commands:
    - tmsh save sys config
  phone_home_url: https://webhook.site/5f8cd8a7-b051-4648-9296-8f6afad34c93
  phone_home_cli: "curl -i -X POST -H 'X-Auth-Token: gAAAAABc5UscwS1py5XfC3yPcyN8KcgD7hYtEZ2-xHw95o4YIh0j5IDjAu9qId3JgMOp9hnHwP42mYA7oPPP0yl-OQXvCaCS3OezKlO7MsS-ZCTJzuS3sSysIMHTA78fGsXbMgCQZCi5G-evLG9xUNrYp5d3blhMnpHR0dlHPz6VMacNkPhyrQI' -H 'Content-Type: application/json' -H 'Accept: application/json' http://192.168.0.121:8004/v1/d3779c949b57403bb7f703016e91a425/stacks/demo_waf/3dd6ce45-bb8c-400d-a48c-87ac9e46e60e/resources/wait_handle/signal"
```

In addition to the declared elements, this module also supports `cloud-config` declarations for `ssh_authorized_keys`. Any declared keys will be authorized for the BIG-IQ root account.

```
#cloud-config
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAGEA3FSyQwBI6Z+nCSjUUk8EEAnnkhXlukKoUPND/RRClWz2s5TCzIkd3Ou5+Cyz71X0XmazM3l5WgeErvtIwQMyT1KjNoMhoJMrJnWqQPOt5Q8zWd9qG7PBl9+eiH5qV7NZ mykey@host
```

## The bigiq_playbooks Cloudinit Module ##

BIG-IQ 7.0 and above includes an installation of Ansible. This means onboarding tasks can be accomplished via Ansible playbooks.

In the bigiq-cloudinit modules above, an embedded onboarding playbook is run to license and onboard the target BIGIQ device.

In addition to the embedded onboard playbook, additional playbooks can be injected with image patching. You can do this by including them in the `image_patch_files/var/lib/cloud/ansible` directory from this repository. A sample Ansible playbook named `license_pool` is includes which will add a device RegKey license pool and populate it with RegKey license offers. 

The `bigiq_playbooks` cloudinit module requires your playbook to follow a naming convention. The userdata declaration for our sample `license_pool` playbook looks like the following:

```
bigiq_playbooks:
  enabled: True
  playbooks:
    - name: license_pool
      vars:
        license_pool_name: REGKEYPOOL
        license_offerings:
          - XINGV-LNNLH-SARPH-GCTRI-IHCGTJZ
          - JCLMK-ZDGDW-KTRGU-PAVVY-GHVOAYV
```

Like all bigiq-cloudinit modules, you must include the `enabled` attribute or the module will simply return without performing any action. 

For the `bigiq_playbooks` cloudinit module, the declaration should include a list of playbooks to run defined with the `playbooks` attribute.

Each playbook declared must have a `name` attritbute and optionally can supply `vars` for your playbook roles. 

From the above declaration, the `bigiq_playbooks` module will:

- attempt to find your playbook in the `/var/lib/cloud/ansible/[name]` directory.
- the optional `vars` declaration YAML will be copied to `/var/lib/cloud/ansible/[name]/[name]_vars.yml` file.
- `ansible-playbook` will be called to exectute the `/var/lib/cloud/ansible/[name]/[name].yml playbook.

Playbooks are run in the order defined in the `playbooks` declaration.

For the above example, the `bigiq_playbooks` cloudinit module would write the `vars` attributes to the `/var/lib/cloud/ansible/license_pool/license_pool_vars.yml` file and would attempt to run the playbook found at `/var/lib/cloud/ansible/license_pool/license_pool.yml`. You must inject your playbook, via image patching, to this location or the module will not be able to find your playbook. 

In order for your injected playbook to read the declared `vars` correctly, your playbook would start with a task like the following:

```
tasks:
    - include_vars:
        file: /var/lib/cloud/ansible/license_pool/license_pool_vars.yml
```

Once included, declared `vars` can be utilized throughout your playbook roles.


# BIG-IQ Cloudinit Modules Support for SSH Keys and Passwords #

In addition to the declared elements, these modules also support `cloud-config` declarations for `ssh_authorized_keys` using the standard cloudinit `cloud-config` declaration syntax. Any declared keys will be authorized for the BIG-IQ root account.

### additional userdata ###

```
#cloud-config
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAGEA3FSyQwBI6Z+nCSjUUk8EEAnnkhXlukKoUPND/RRClWz2s5TCzIkd3Ou5+Cyz71X0XmazM3l5WgeErvtIwQMyT1KjNoMhoJMrJnWqQPOt5Q8zWd9qG7PBl9+eiH5qV7NZ mykey@host
```

### Support Cloudinit set-password ###

The patched VE image cloudinit configurations template has been altered to support the standard cloudinit `set_password` module as well. You can change the built-in BIG-IQ `admin` and  `root` passwords using the following cloudinit `cloud-config` declarations.

```
#cloud-config
chpasswd:
  list: |
    root:f5str0ngPa$$word
    admin:f5str0ngPa$$word
```

If the well-known `admin` and `root` BIG-IQ accounts do not have password sets, the accounts will be locked via the BIG-IQ OS. To enable the `admin` or `root` account, SSH into the device, with an injected SSH key, and enable the account:

```
usermod -U admin
```