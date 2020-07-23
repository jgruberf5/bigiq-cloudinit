#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2017, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

LICENSE_FILE = '/config/bigip.license'

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = r'''
---
module: write_license_file
short_description: Write out bigip.license file on BIG-IQ
description:
  - Write out the bigip.license file on BIG-IQ ignoring selinux restrictions.
version_added: "2.5"
options:
  license_text:
    description:
      - The license text content
    default: ''
extends_documentation_fragment: f5
author:
  - John Gruber (@jgruber)
'''

EXAMPLES = r'''
- name: Write License File:
  write_license_file:
    license_text: "{{ license_string }}"
'''

RETRUN = r'''
written:
  description: Did the write succeed
  type: boolean
  sample: true
length:
  description: bytes written
  type: int
  sample: 2345
'''

import os

from ansible.module_utils.basic import AnsibleModule


class ModuleManager(object):
    def __init__(self, module=None):
        self.module = module

    def exec_module(self):
        result = dict(written=False, length=0)
        state = self.module.params['state']

        if self.module.check_mode:
            if os.path.exists(LICENSE_FILE):
                result['written'] = True,
                result['length'] = os.path.getsize(LICENSE_FILE)
            if state == 'absent':
                os.unlink(LICENSE_FILE)
            return result

        license_text = self.module.params['license_text']
        with open(LICENSE_FILE, 'w+') as lf:
            lf.write(license_text)
        os.chown(LICENSE_FILE, 0, 0)
        os.chmod(LICENSE_FILE, 420)
        result['written'] = True,
        result['length'] = os.path.getsize(LICENSE_FILE)
        return result


class ArgumentSpec(object):
    def __init__(self):
        self.supports_check_mode = True
        argument_spec = dict(license_text=dict(type='str', required=True),
                             state=dict(default='present',
                                        choices=['present', 'absent']))
        self.argument_spec = {}
        self.argument_spec.update(argument_spec)


def main():
    spec = ArgumentSpec()

    module = AnsibleModule(argument_spec=spec.argument_spec,
                           supports_check_mode=spec.supports_check_mode)

    try:
        mm = ModuleManager(module=module)
        results = mm.exec_module()
        module.exit_json(**results)
    except Exception as ex:
        module.fail_json(msg=str(ex))


if __name__ == '__main__':
    main()