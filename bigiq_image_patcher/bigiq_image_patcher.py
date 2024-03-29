#!/usr/bin/env python3

# coding=utf-8
# pylint: disable=broad-except,unused-argument,line-too-long, unused-variable
# Copyright (c) 2016-2018, F5 Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This module contains the logic to injet files into BIGIQ classic
disk images using guestfs tools.
"""

import os
import sys
import tarfile
import zipfile
import datetime
import hashlib
import time
import logging
import subprocess
import guestfs
import re

from Crypto.Hash import SHA384
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

ARCHIVE_EXTS = {'.zip': 'zipfile', '.ova': 'tarfile'}
IMAGE_TYPES = ['.qcow2', '.vhd', '.vmdk']

VBOXMANAGE_CLI = '/usr/bin/vboxmanage'
VBOXMANAGE_CLI_FORMAT = 'vmdk'
VBOXMANAGE_CLI_PATCH_VARIANT = 'Standard'
VBOXMANAGE_CLI_OUTPUT_VARIANT = 'Stream'

DEBUG = True

LOG = logging.getLogger('bigiq_image_patcher')
LOG.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGSTREAM = logging.StreamHandler(sys.stdout)
LOGSTREAM.setFormatter(FORMATTER)
LOG.addHandler(LOGSTREAM)


def patch_images(bigiq_image_dir, bigiq_cloudinit_dir, bigiq_usr_inject_dir,
                 bigiq_var_inject_dir, bigiq_config_inject_dir,
                 bigiq_shared_inject_dir, private_pem_key_path,
                 cloud_template_file, image_overwrite, image_build_id):
    """Patch BIGIQ classic disk image"""
    if bigiq_image_dir and os.path.exists(bigiq_image_dir):
        for disk_image in scan_for_images(bigiq_image_dir, image_overwrite,
                                          image_build_id):
            (is_bigiq, config_dev, usr_dev, var_dev, shared_dev) = \
                validate_bigiq_device(disk_image)
            if is_bigiq:
                manifest_file_path = "%s.manifest" % disk_image
                if os.path.exists(manifest_file_path):
                    LOG.info('deleting previous manifest file %s',
                             manifest_file_path)
                    os.unlink(manifest_file_path)
                if usr_dev and bigiq_cloudinit_dir:
                    update_cloudinit = os.getenv('UPDATE_CLOUDINIT',
                                                 default="true")
                    if update_cloudinit == "true":
                        update_cloudinit_modules(bigiq_cloudinit_dir)
                    inject_cloudinit_modules(disk_image, bigiq_cloudinit_dir,
                                             usr_dev)
                if usr_dev and cloud_template_file:
                    inject_cloudinit_config_template(disk_image,
                                                     bigiq_cloudinit_dir,
                                                     cloud_template_file,
                                                     usr_dev)
                if usr_dev and bigiq_usr_inject_dir:
                    inject_usr_files(disk_image, bigiq_usr_inject_dir, usr_dev)
                if var_dev and bigiq_var_inject_dir:
                    inject_var_files(disk_image, bigiq_var_inject_dir, var_dev)
                if shared_dev and bigiq_shared_inject_dir:
                    inject_shared_files(disk_image, bigiq_shared_inject_dir,
                                        shared_dev)
                if config_dev and bigiq_config_inject_dir:
                    inject_config_files(disk_image, bigiq_config_inject_dir,
                                        config_dev)
                if os.path.splitext(disk_image)[1] == '.vmdk':
                    clean_up_vmdk(disk_image)
            generate_md5sum(disk_image)
            if private_pem_key_path:
                try:
                    sign_image(disk_image, private_pem_key_path)
                except Exception as ex:
                    LOG.error("could not sign %s with private key %s: %s",
                              disk_image, private_pem_key_path, ex)
            if image_build_id:
                build_split = os.path.splitext(disk_image)
                build_name = "%s-%s%s" % (build_split[0], image_build_id, build_split[1])
                os.rename(disk_image, build_name)
                os.rename("%s.md5" % disk_image, "%s.md5" % build_name)
                os.rename("%s.manifest" % disk_image, "%s.manifest" % build_name)
                sig_file = "%s.384.sig" % disk_image
                if os.path.exists(sig_file):
                    os.rename(sig_file, "%s.384.sig" % build_name)
    else:
        LOG.error("BIGIQ image directory %s does not exist.", bigiq_image_dir)
        LOG.error("Set environment variable BIGIQ_IMAGE_DIR or supply as the first argument to the script.")
        sys.exit(1)


def scan_for_images(tmos_image_dir, image_overwrite, image_build_id):
    """Scan for BIG-IQ disk images"""
    return_image_files = []
    for image_file in os.listdir(tmos_image_dir):
        filepath = "%s/%s" % (tmos_image_dir, image_file)
        if os.path.isfile(filepath):
            extract_dir = "%s/%s" % (tmos_image_dir,
                                     os.path.splitext(image_file)[0])
            if image_build_id:
                build_split = os.path.splitext(os.path.splitext(image_file)[0])
                if not build_split[0].endswith(image_build_id):
                    extract_dir = "%s/%s-%s%s" % (tmos_image_dir,
                                                  build_split[0],
                                                  image_build_id,
                                                  build_split[1])
            if os.path.exists(extract_dir):
                found_sum_files = False
                LOG.debug('examining existing patching directory %s' %
                          extract_dir)
                for existing_file in os.listdir(extract_dir):
                    if os.path.splitext(existing_file)[-1] == '.md5':
                        LOG.debug('found previous patching artifact file %s' %
                                  existing_file)
                        found_sum_files = True
                if not image_overwrite and found_sum_files:
                    LOG.info(
                        'previous patch artifacts found in %s.. skipping patching.'
                        % extract_dir)
                    continue
            else:
                LOG.debug('creating patching directory %s' % extract_dir)
                os.makedirs(extract_dir)
            arch_ext = os.path.splitext(image_file)[1]
            if arch_ext in ARCHIVE_EXTS:
                if ARCHIVE_EXTS[arch_ext] == 'zipfile':
                    extract_zip_archive(filepath, extract_dir)
                if ARCHIVE_EXTS[arch_ext] == 'tarfile':
                    extract_tar_archive(filepath, extract_dir)
            for extracted_file in os.listdir(extract_dir):
                if os.path.splitext(extracted_file)[1] in IMAGE_TYPES:
                    image_filepath = "%s/%s" % (extract_dir, extracted_file)
                    if os.path.splitext(extracted_file)[1] == '.vmdk':
                        convert_vmdk(image_filepath,
                                     VBOXMANAGE_CLI_PATCH_VARIANT)
                    return_image_files.append(image_filepath)
    return return_image_files


def extract_tar_archive(archive_file, extract_dir):
    """Extract a tar archive"""
    LOG.debug('extracting %s to %s', archive_file, extract_dir)
    archive = tarfile.TarFile(archive_file, 'r')
    archive.extractall(extract_dir)
    archive.close()


def extract_zip_archive(archive_file, extract_dir):
    """Extract a zip archive"""
    LOG.debug('extracting %s to %s', archive_file, extract_dir)
    archive = zipfile.ZipFile(archive_file, 'r')
    archive.extractall(extract_dir)
    archive.close()


def convert_vmdk(image_file, variant):
    """Force convert VMDK image files to standard format"""
    start_directory = os.getcwd()
    convert_dir = os.path.dirname(image_file)
    image_file = os.path.basename(image_file)
    LOG.warn('converting VMDK format to %s format', variant)
    os.chdir(convert_dir)
    FNULL = open(os.devnull, 'w')
    subprocess.call([
        VBOXMANAGE_CLI,
        'clonemedium',
        '--format',
        VBOXMANAGE_CLI_FORMAT,
        '--variant',
        variant,
        image_file,
        'converted.vmdk',
    ],
                    stdout=FNULL,
                    stderr=subprocess.STDOUT)
    subprocess.call(['/bin/mv', '-f', 'converted.vmdk', image_file])
    os.chdir(start_directory)


def clean_up_vmdk(disk_image):
    """Convert VMDK image to output format and remove OVF references to old image"""
    convert_vmdk(disk_image, VBOXMANAGE_CLI_OUTPUT_VARIANT)
    convert_dir = os.path.dirname(disk_image)
    for file_name in os.listdir(convert_dir):
        if file_name.endswith('.mf'):
            LOG.warn('removing mf hash file %s', file_name)
            os.remove(os.path.join(convert_dir, file_name))
    for file_name in os.listdir(convert_dir):
        if file_name.endswith('.cert'):
            LOG.warn('removing signing file %s', file_name)
            os.remove(os.path.join(convert_dir, file_name))
    ovf_file_name = None
    for file_name in os.listdir(convert_dir):
        if file_name.endswith('.ovf'):
            LOG.warn('patching OVF to remove restrictions')
            ovf_file_name = file_name
            clean_ovf(os.path.join(convert_dir, file_name))
    ova_name = "%s.ova" % os.path.basename(convert_dir)
    LOG.info('createing OVA image %s', ova_name)
    start_directory = os.getcwd()
    os.chdir(convert_dir)
    ova_file = tarfile.TarFile(ova_name, 'w')
    ova_file.add(ovf_file_name)
    ova_file.add(os.path.basename(disk_image))
    ova_file.close()
    os.remove(ovf_file_name)
    os.remove(os.path.basename(disk_image))
    os.chdir(start_directory)


def clean_ovf(ovf_file_path):
    """Remove OVF references to proprietary image"""
    working_dir = os.path.dirname(ovf_file_path)
    file_name = os.path.basename(ovf_file_path)
    os.rename(ovf_file_path, os.path.join(working_dir,
                                          "%s.backup" % file_name))
    original_ovf = open(os.path.join(working_dir, "%s.backup" % file_name),
                        'r')
    new_ovf = open(ovf_file_path, 'w')
    for line in original_ovf:
        if 'ovf:size' in line:
            new_ovf.write("%s/>\n" % line[0:line.index('ovf:size')])
        elif 'ovf:populatedSize' in line:
            new_ovf.write("%s\"/>\n" % line[0:line.index('#streamOptimized')])
        elif 'VirtualSystemType' not in line:
            new_ovf.write(line)
    original_ovf.close()
    new_ovf.close()
    os.remove(os.path.join(working_dir, "%s.backup" % file_name))


def add_to_manifest(filepath, disk_image):
    manifest_file_path = "%s.manifest" % disk_image
    disk_name = os.path.basename(disk_image)
    if not os.path.exists(manifest_file_path):
        LOG.info('creating manifest file for %s as %s', disk_name,
                 manifest_file_path)
    with open(manifest_file_path, 'a+') as mf:
        LOG.info('adding %s to %s', filepath, manifest_file_path)
        mf.write("%s\n" % filepath)


def generate_md5sum(disk_image):
    """Create MD5 sum file for the disk image"""
    md5_file_path = "%s.md5" % disk_image
    LOG.info('creating md5sum file for %s as %s', disk_image, md5_file_path)
    md5_hash = hashlib.md5()
    with open(disk_image, 'rb') as di:
        for block in iter(lambda: di.read(4096), b''):
            md5_hash.update(block)
        with open(md5_file_path, 'w+') as md5sum:
            md5sum.write(md5_hash.hexdigest())


def sign_image(disk_image, private_key):
    """Creating SHA384 signature digest for disk image"""
    sig_file_path = "%s.384.sig" % disk_image
    LOG.info('signing image %s with private key %s', disk_image, private_key)
    sha384_hash = SHA384.new()
    with open(disk_image, 'rb') as di:
        for block in iter(lambda: di.read(4096), b''):
            sha384_hash.update(block)
        pk = False
        with open(private_key, 'r') as key_file:
            pk = RSA.importKey(key_file.read())
        signer = PKCS1_v1_5.new(pk)
        digest = signer.sign(sha384_hash)
        with open(sig_file_path, 'w+') as sha384sig:
            sha384sig.write(digest)


def wait_for_gfs(gfs_handle):
    """System settle time for gfs"""
    time.sleep(5)


def validate_bigiq_device(disk_image):
    """Validate disk image has BIGIQ volumes"""
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    is_bigiq = False
    config_dev = None
    usr_dev = None
    var_dev = None
    shared_dev = None
    for file_system in gfs.list_filesystems():
        if '_config' in file_system:
            is_bigiq = True
            config_dev = file_system
        if '_usr' in file_system:
            usr_dev = file_system
        if '_var' in file_system:
            var_dev = file_system
        if 'share' in file_system:
            shared_dev = file_system
    if not is_bigiq:
        LOG.warn('%s is not a BIGIQ image file.. skipping..', disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)
    return (is_bigiq, config_dev, usr_dev, var_dev, shared_dev)


def update_cloudinit_modules(bigiq_cloudinit_dir):
    """Get latest cloudinit"""
    LOG.info('pulling latest cloudinit modules')
    start_directory = os.getcwd()
    os.chdir(bigiq_cloudinit_dir)
    gitout = subprocess.Popen("git pull", stdout=subprocess.PIPE,
                              shell=True, encoding='utf8').communicate()[0].split('\n')
    LOG.info('git returned: %s', gitout)
    os.chdir(start_directory)


def inject_cloudinit_modules(disk_image, bigiq_cloudinit_dir, dev):
    """Inject cloudinit modules into BIGIQ disk image"""
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    gfs.mount(dev, '/')
    python_system_path = '/local/lib/python2.7'
    LOG.debug('injecting files into /usr%s' % python_system_path)
    bigiq_cc_path = "%s/image_patch_files/system_python_path" % bigiq_cloudinit_dir
    bigiq_cc_files = []
    for root, dirs, files in os.walk(bigiq_cc_path):
        for file_name in files:
            bigiq_cc_files.append(
                os.path.join(root, file_name)[len(bigiq_cc_path):])
    for bigiq_cc_file in bigiq_cc_files:
        local = "%s%s" % (bigiq_cc_path, bigiq_cc_file)
        remote = "%s%s" % (python_system_path, bigiq_cc_file)
        LOG.debug('injecting %s to /usr%s', os.path.basename(local), remote)
        mkdir_path = os.path.dirname(remote)
        gfs.mkdir_p(mkdir_path)
        gfs.upload(local, remote)
        add_to_manifest("/usr%s" % remote, disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)


def inject_cloudinit_config_template(disk_image, bigiq_cloudinit_dir,
                                     cloud_template_file,dev):
    """Inject cloudinit configuration template into BIG-IQ disk image"""
    LOG.debug('injecting cloudinit configuration template %s' %
              cloud_template_file)
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    gfs.mount(dev, '/')
    mkdir_path = '/share/defaults/config/templates'
    dest_template_file = "%s/cloud-init.tmpl" % mkdir_path
    gfs.mkdir_p(mkdir_path)
    gfs.upload(cloud_template_file, dest_template_file)
    add_to_manifest("/usr%s" % dest_template_file, disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)


def inject_usr_files(disk_image, usr_dir, dev):
    """Patch /usr file system of a BIGIQ disk image"""
    LOG.debug('injecting files into /usr')
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    gfs.mount(dev, '/')
    usr_files = []
    for root, dirs, files in os.walk(usr_dir):
        for file_name in files:
            usr_files.append(os.path.join(root, file_name)[len(usr_dir):])
    for usr_file in usr_files:
        local = "%s%s" % (usr_dir, usr_file)
        LOG.debug('injecting %s to /usr%s', os.path.basename(local), usr_file)
        mkdir_path = os.path.dirname(usr_file)
        gfs.mkdir_p(mkdir_path)
        gfs.upload(local, usr_file)
        add_to_manifest("/usr%s" % usr_file, disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)


def inject_var_files(disk_image, var_dir, dev):
    """Patch /var file system of a BIGIQ disk image"""
    LOG.debug('injecting files into /var')
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    gfs.mount(dev, '/')
    var_files = []
    for root, dirs, files in os.walk(var_dir):
        for file_name in files:
            var_files.append(os.path.join(root, file_name)[len(var_dir):])
    for var_file in var_files:
        local = "%s%s" % (var_dir, var_file)
        LOG.debug('injecting %s to /var%s', os.path.basename(local), var_file)
        mkdir_path = os.path.dirname(var_file)
        gfs.mkdir_p(mkdir_path)
        gfs.upload(local, var_file)
        add_to_manifest("/var%s" % var_file, disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)


def inject_shared_files(disk_image, shared_dir, dev):
    """Patch /shared file system of a BIGIQ disk image"""
    LOG.debug('injecting files into /shared')
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    gfs.mount(dev, '/')
    shared_files = []
    for root, dirs, files in os.walk(shared_dir):
        for file_name in files:
            shared_files.append(
                os.path.join(root, file_name)[len(shared_dir):])
    for shared_file in shared_files:
        local = "%s%s" % (shared_dir, shared_file)
        LOG.debug('injecting %s to /shared%s', os.path.basename(local),
                  shared_file)
        mkdir_path = os.path.dirname(shared_file)
        gfs.mkdir_p(mkdir_path)
        gfs.upload(local, shared_file)
        add_to_manifest("/shared%s" % shared_file, disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)


def inject_config_files(disk_image, config_dir, dev):
    """Patch /config file system of a BIGIQ disk image"""
    LOG.debug('injecting files into /config')
    gfs = guestfs.GuestFS(python_return_dict=True)
    gfs.add_drive_opts(disk_image)
    gfs.launch()
    gfs.mount(dev, '/')
    config_files = []
    for root, dirs, files in os.walk(config_dir):
        for file_name in files:
            config_files.append(
                os.path.join(root, file_name)[len(config_dir):])
    for config_file in config_files:
        local = "%s%s" % (config_dir, config_file)
        LOG.debug('injecting %s to /config%s', os.path.basename(local),
                  config_file)
        mkdir_path = os.path.dirname(config_file)
        gfs.mkdir_p(mkdir_path)
        gfs.upload(local, config_file)
        add_to_manifest("/config%s" % config_file, disk_image)
    gfs.sync()
    gfs.shutdown()
    gfs.close()
    wait_for_gfs(gfs)


if __name__ == "__main__":
    if not os.environ['USER'] == 'root':
        print("Please run this script as sudo")
        sys.exit(1)
    START_TIME = time.time()
    LOG.debug(
        'process start time: %s',
        datetime.datetime.fromtimestamp(START_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"))
    BIGIQ_IMAGE_DIR = os.getenv('BIGIQ_IMAGE_DIR', None)
    BIGIQ_CLOUDINIT_DIR = os.getenv('BIGIQ_CLOUDINIT_DIR', '/bigiq-cloudinit')
    BIGIQ_USR_INJECT_DIR = os.getenv('BIGIQ_USR_INJECT_DIR', None)
    BIGIQ_VAR_INJECT_DIR = os.getenv('BIGIQ_VAR_INJECT_DIR', None)
    BIGIQ_SHARED_INJECT_DIR = os.getenv('BIGIQ_SHARED_INJECT_DIR', None)
    BIGIQ_CONFIG_INJECT_DIR = os.getenv('BIGIQ_CONFIG_INJECT_DIR', None)
    PRIVATE_PEM_KEY_DIR = os.getenv('PRIVATE_PEM_KEY_PATH', '/keys')
    PRIVATE_PEM_KEY_FILE = os.getenv('PRIVATE_PEM_KEY_FILE', None)
    IMAGE_OVERWRITE = os.getenv('IMAGE_OVERWRITE', '0')
    IMAGE_BUILD_ID = os.getenv('IMAGE_BUILD_ID', None)
    BIGIQ_CLOUDINIT_CONFIG_TEMPLATE = os.getenv(
        'BIGIQ_CLOUDINIT_CONFIG_TEMPLATE',
        '/bigiq-cloudinit/image_patch_files/cloudinit_configs/disable_cloudinit/cloud-init.tmpl')
    if len(sys.argv) > 1:
        BIGIQ_IMAGE_DIR = sys.argv[1]
    if len(sys.argv) > 2:
        BIGIQ_CLOUDINIT_DIR = sys.argv[2]
    if BIGIQ_IMAGE_DIR:
        LOG.info("Scanning for images in: %s", BIGIQ_IMAGE_DIR)
    if BIGIQ_CLOUDINIT_CONFIG_TEMPLATE:
        LOG.info("BIGIQ cloudinit template file sourced from: %s",
                 BIGIQ_CLOUDINIT_CONFIG_TEMPLATE)
    if BIGIQ_CLOUDINIT_DIR:
        LOG.info("BIGIQ cloudinit modules sourced from: %s",
                 BIGIQ_CLOUDINIT_DIR)
    if BIGIQ_USR_INJECT_DIR:
        LOG.info("Patching BIGIQ /usr file system from: %s",
                 BIGIQ_USR_INJECT_DIR)
    if BIGIQ_VAR_INJECT_DIR:
        LOG.info("Patching BIGIQ /var file system from: %s",
                 BIGIQ_VAR_INJECT_DIR)
    if BIGIQ_SHARED_INJECT_DIR:
        LOG.info("Patching BIGIQ /shared file system from: %s",
                 BIGIQ_SHARED_INJECT_DIR)
    if BIGIQ_CONFIG_INJECT_DIR:
        LOG.info("Patching BIGIQ /config file system from: %s",
                 BIGIQ_CONFIG_INJECT_DIR)
    if BIGIQ_CONFIG_INJECT_DIR:
        LOG.info("Patching TMOS /config file system from: %s",
                 BIGIQ_CONFIG_INJECT_DIR)
    PRIVATE_KEY_PATH = None
    if PRIVATE_PEM_KEY_FILE and os.path.exists(
            "%s/%s" % (PRIVATE_PEM_KEY_DIR, PRIVATE_PEM_KEY_FILE)):
        PRIVATE_KEY_PATH = "%s/%s" % (PRIVATE_PEM_KEY_DIR,
                                      PRIVATE_PEM_KEY_FILE)
    if IMAGE_OVERWRITE == "1" or IMAGE_OVERWRITE.lower(
    ) == 'yes' or IMAGE_OVERWRITE.lower() == 'true':
        IMAGE_OVERWRITE = True
        LOG.info('force overwrite of existing patch file artifacts')
    else:
        IMAGE_OVERWRITE = False
    patch_images(BIGIQ_IMAGE_DIR, BIGIQ_CLOUDINIT_DIR, BIGIQ_USR_INJECT_DIR,
                 BIGIQ_VAR_INJECT_DIR, BIGIQ_CONFIG_INJECT_DIR,
                 BIGIQ_SHARED_INJECT_DIR, PRIVATE_KEY_PATH, 
                 BIGIQ_CLOUDINIT_CONFIG_TEMPLATE, IMAGE_OVERWRITE, IMAGE_BUILD_ID)
    STOP_TIME = time.time()
    DURATION = STOP_TIME - START_TIME
    LOG.debug(
        'process end time: %s - ran %s (seconds)',
        datetime.datetime.fromtimestamp(STOP_TIME).strftime(
            "%A, %B %d, %Y %I:%M:%S"), DURATION)
