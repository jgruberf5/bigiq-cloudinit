FROM ubuntu:latest
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y libguestfs-tools \
    qemu-utils \
    linux-image-generic \
    virtualbox \
    python3-guestfs \
    python3-crypto \
    python3-jsonschema \
    python3-yaml \
    python3-pip \
    python3-setuptools \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN pip3 install wheel
RUN git clone https://github.com/jgruberf5/bigiq-cloudinit.git
RUN pip3 install pycdlib

ENV LIBGUESTFS_BACKEND=direct

VOLUME ["/BIGIQImages", "/BIGIQ_usr", "/BIGIQ_config"]

ENV BIGIQ_IMAGE_DIR '/BIGIQImages'
ENV BIGIQ_CONFIG_INJECT_DIR '/bigiq-cloudinit/image_patch_files/config'
ENV BIGIQ_VAR_INJECT_DIR '/bigiq-cloudinit/image_patch_files/var'
ENV BIQIQ_CLOUDINIT_CONFIG_TEMPLATE '/bigiq-cloudinit/image_patch_files/cloudinit_configs/disable_cloudinit/cloud-init.tmpl'
ENV USER 'root'
ENV UPDATE_CLOUDINIT 'true'
ENV IMAGE_OVERWRITE = 'no'

ENTRYPOINT [ "/bigiq-cloudinit/bigiq_image_patcher/bigiq_image_patcher.py" ]