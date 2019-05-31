#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright: (c) 2019, Diógenes Oliveira <diogenes1oliveira@gmail.com>
# The MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from __future__ import print_function

from base64 import b64encode
import hashlib
import os
from shutil import rmtree
from tempfile import mkdtemp
from zipfile import ZipFile

import boto3

from ansible.module_utils.basic import AnsibleModule
ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}

DOCUMENTATION = '''
---
module: layer_search

short_description: Look up a Lambda layer

version_added: "2.4"

description:
    - Returns details about a layer with the given name, failing
      if such image does not exist.

options:
    name:
        description:
            - Name of the layer to be searched
        required: True

author:
    - Diógenes Oliveira (@diogenes1oliveira)
'''

EXAMPLES = '''
- name: Fetch details about the layer 'my-layer', if it exists
  layer_search:
    name: my-layer
  register: layer
'''

RETURN = '''
found:
    description: whether such layer was found
    type: bool
name:
    description: name of the layer
    type: str
version:
    description: last version of this layer
    returned: found
    type: list
arn:
    description: ARNs of the last version of this layer
    returned: found
    type: list
'''


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(type='str', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    result = dict(
        changed=False,
        failed=False,
    )

    if module.check_mode:
        return result

    connection_args = {}
    if os.getenv('LAMBDA_URL', None):
        connection_args['endpoint_url'] = os.environ['LAMBDA_URL']
    if os.getenv('AWS_DEFAULT_REGION', None):
        connection_args['region_name'] = os.environ['AWS_DEFAULT_REGION']
    client = boto3.client('lambda', **connection_args)

    try:
        cmd = client.list_layer_versions(
            LayerName=module.params['name'],
        )
        versions = sorted(cmd['LayerVersions'], key=(
            lambda v: v['Version']), reverse=True)
    except Exception as e:
        error = str(e)
        result['stderr'] = error
        result['failed'] = True
        module.fail_json(msg=error, **result)
    else:
        result['name'] = module.params['name']
        result['found'] = len(versions) > 0
        if result['found']:
            result['version'] = versions[0]['Version']
            result['arn'] = versions[0]['LayerVersionArn']

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
