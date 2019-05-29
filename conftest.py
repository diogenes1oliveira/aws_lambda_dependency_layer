from contextlib import contextmanager
from itertools import chain
import logging
import os
from uuid import uuid4

import boto3
import pytest

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)


@pytest.fixture(scope='function')
def temp_bucket():
    return temp_bucket_context


@contextmanager
def temp_bucket_context(prefix='temp-bucket-'):
    """
    Creates a temporary bucket
    """
    version = str(uuid4()).replace('-', '')[:10].lower()
    bucket_name = prefix + version
    s3_client = boto3.client('s3')

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
