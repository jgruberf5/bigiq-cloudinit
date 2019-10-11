FROM ubuntu:latest
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y libguestfs-tools \
    qemu-utils \
    linux-image-generic \
    virtualbox \
    python-ipython \
    python-openstackclient \
    python-guestfs \
    python-jsonschema \
    python-yaml \
    python-pip \
    python-setuptools \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN pip install wheel
RUN git clone https://github.com/jgruberf5/bigiq-cloudinit.git
RUN pip install pycdlib

ENV LIBGUESTFS_BACKEND=direct

VOLUME ["/BIGIQImages", "/BIGIQ_usr", "/BIGIQ_config"]

ENV BIGIQ_IMAGE_DIR '/BIGIQImages'
ENV BIGIQ_CONFIG_INJECT_DIR '/bigiq-cloudinit/image_patch_files/config'
ENV BIGIQ_VAR_INJECT_DIR '/bigiq-cloudinit/image_patch_files/var'
ENV USER 'root'
ENV UPDATE_CLOUDINIT 'true'

ENTRYPOINT [ "/bigiq-cloudinit/bigiq_image_patcher/bigiq_image_patcher.py" ]