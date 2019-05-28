from contextlib import contextmanager, ExitStack, wraps
import json
import logging
import os
from uuid import uuid4

import boto3
import pytest

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)


@pytest.fixture(scope='function')
def iam_role():
    return iam_role_context


def log_call(f):
    @wraps(f)
    def inner(*args, **kwargs):
        args_str = ''
        if args:
            args_str += ', '.join(repr(a) for a in args)
        if kwargs:
            args_str += (', ' if args else '') + ', '.join(f'{k}={repr(v)}' for k, v in kwargs.items())
        LOGGER.info(f'Called {f.__class__.__name__}.{f.__name__}({args_str})')
        f(*args, **kwargs)
    return inner


@contextmanager
def iam_role_context(
        policy_arn='arn:aws:iam::aws:policy/service-role/AWSLambdaRole',
        service='lambda.amazonaws.com',
        prefix='TempRole'):
    """
    Creates a temporary IAM role
    """
    version = str(uuid4()).replace('-', '')[:10].upper()
    role_name = prefix + version
    iam_client = boto3.client('iam')

    with ExitStack() as stack:
        role_cmd = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Principal": {
                                "Service": service,
                            },
                            "Effect": "Allow",
                            "Sid": "",
                        },
                    ],
                },
            ),
        )
        LOGGER.info('Created role = %s', role_name)
        stack.callback(
            log_call(iam_client.delete_role),
            RoleName=role_name,
        )
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn,
        )
        LOGGER.info('Attached policy %s to role = %s', policy_arn, role_name)
        stack.callback(
            log_call(iam_client.detach_role_policy),
            RoleName=role_name,
            PolicyArn=policy_arn,
        )
        yield role_cmd['Role']['Arn']
