from contextlib import contextmanager, ExitStack, wraps
from itertools import chain
import json
import logging
import os
from uuid import uuid4

import boto3
import pytest

from common import log_call

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)


@pytest.fixture(scope='function')
def iam_role():
    return temp_iam_role_context


@contextmanager
def temp_iam_role_context(
        policy_arn='arn:aws:iam::aws:policy/service-role/AWSLambdaRole',
        service='lambda.amazonaws.com',
        prefix='TempRole'):
    """
    Creates a temporary IAM role
    """
    version = str(uuid4()).replace('-', '')[:10].upper()
    role_name = prefix + version
    connection_args = {}
    if os.getenv('IAM_URL', None):
        connection_args['endpoint_url'] = os.environ['IAM_URL']
    if os.getenv('AWS_DEFAULT_REGION', None):
        connection_args['region_name'] = os.environ['AWS_DEFAULT_REGION']
    iam_client = boto3.client('iam', **connection_args)

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
            log_call(LOGGER, iam_client.delete_role),
            RoleName=role_name,
        )
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn,
        )
        LOGGER.info('Attached policy %s to role = %s', policy_arn, role_name)
        stack.callback(
            log_call(LOGGER, iam_client.detach_role_policy),
            RoleName=role_name,
            PolicyArn=policy_arn,
        )
        yield role_cmd['Role']['Arn']


@pytest.fixture(scope='function')
def temp_bucket():
    return temp_bucket_context


@contextmanager
def temp_bucket_context(prefix='temp-bucket-'):
    """
    Creates a temporary bucket
    """
    connection_args = {}
    if os.getenv('S3_URL', None):
        connection_args['endpoint_url'] = os.environ['S3_URL']
    if os.getenv('AWS_DEFAULT_REGION', None):
        connection_args['region_name'] = os.environ['AWS_DEFAULT_REGION']

    version = str(uuid4()).replace('-', '')[:10].lower()
    bucket_name = prefix + version
    s3_client = boto3.client('s3', **connection_args)

    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={
            'LocationConstraint': s3_client.meta.region_name,
        },
    )
    LOGGER.info('Created bucket %s', bucket_name)

    try:
        yield bucket_name
    finally:
        LOGGER.info('Deleted bucket %s', bucket_name)
        versions = s3_client.list_object_versions(
            Bucket=bucket_name, MaxKeys=100)

        objects = []
        all_versions = chain(
            versions.get('Versions', None) or [],
            versions.get('DeleteMarkers', None) or [],
        )

        for version in all_versions:
            objects.append({
                'Key': version['Key'],
                'VersionId': version['VersionId'],
            })

        if objects:
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={
                    'Objects': objects,
                },
            )
        s3_client.delete_bucket(Bucket=bucket_name)
