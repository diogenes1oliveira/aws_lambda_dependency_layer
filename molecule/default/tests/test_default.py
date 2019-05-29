from contextlib import ExitStack
import logging
import json
import os
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import boto3

from common import log_call

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)
MY_PATH = os.path.dirname(os.path.abspath(__file__))


def get_temp_suffix():
    temp_path = os.getenv('MOLECULE_EPHEMERAL_DIRECTORY')
    with open(os.path.join(temp_path, 'temp-suffix.txt')) as fp:
        return fp.read().strip()


def upload_sample_bundle(bucket):
    s3_client = boto3.client('s3')
    object_key = 'lambda-bundle.zip'
    sample_path = os.path.join(MY_PATH, 'sample-data/sample.rb')

    os.system('ls -lah')
    with TemporaryDirectory() as tempdir:
        zip_path = os.path.join(tempdir, 'lambda-bundle.zip')

        with ZipFile(zip_path, 'w') as zip_fp:
            zip_fp.write(sample_path, arcname='sample.zip')

        with open(zip_path, 'rb') as fp:
            s3_client.put_object(
                Body=fp,
                Bucket=bucket,
                Key=object_key,
            )
    return object_key


def test(iam_role):
    suffix = get_temp_suffix()
    function_name = 'temp-function-' + suffix
    layer_name = 'temp-layer-' + suffix
    bucket_name = 'temp-bucket-' + suffix
    object_key = upload_sample_bundle(bucket_name)

    lambda_client = boto3.client('lambda')

    with ExitStack() as stack:
        role_arn = stack.enter_context(iam_role())
        cmd = lambda_client.create_function(
            FunctionName=function_name,
            Role=role_arn,
            Runtime='ruby2.5',
            Handler='sample.handler',
            Publish=True,
            Code={
                'S3Bucket': bucket_name,
                'S3Key': object_key,
            },
            Layers=[
                layer_name,
            ],
        )
        version = cmd['Version']
        stack.callback(
            log_call(LOGGER, lambda_client.delete_function),
            FunctionName=function_name,
            Qualifier=version,
        )
        invocation = lambda_client.invoke(
            FunctionName=function_name,
            LogType=None,
        )
        payload = invocation['Payload'].read().decode('utf-8')
        LOGGER.info('payload = %s', payload)

        response = json.loads(json.loads(payload)['body'])
        assert response['version'] == '5.2.0'
