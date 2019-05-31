from contextlib import ExitStack
import logging
import json
import os
from tempfile import TemporaryDirectory
import time
from zipfile import ZipFile

import boto3

from common import log_call

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)
MY_PATH = os.path.dirname(os.path.abspath(__file__))


def get_temp_suffix():
    temp_path = os.getenv(
        'MOLECULE_EPHEMERAL_DIRECTORY',
        '/tmp/molecule/lambda-dependency-layer/default/',
    )

    with open(os.path.join(temp_path, 'temp-suffix.txt')) as fp:
        return fp.read().strip()


def upload_sample_bundle(bucket):
    s3_client = boto3.client('s3')
    object_key = 'lambda-bundle.zip'
    sample_path = os.path.join(MY_PATH, 'sample-data/ruby2.5/sample.rb')

    with TemporaryDirectory() as tempdir:
        zip_path = os.path.join(tempdir, 'lambda-bundle.zip')

        with ZipFile(zip_path, 'w') as zip_fp:
            zip_fp.write(sample_path, arcname='sample.rb')

        with open(zip_path, 'rb') as fp:
            s3_client.put_object(
                Body=fp,
                Bucket=bucket,
                Key=object_key,
            )
    return object_key


def destroy_function(function_name, lambda_client=None):
    lambda_client = lambda_client or boto3.client('lambda')

    def destroy_function_versions(versions):
        for v in versions:
            if v['Version'] == '$LATEST':
                continue
            LOGGER.info('Destroying version %s of function %s', v['Version'], function_name)
            lambda_client.delete_function(
                FunctionName=function_name,
                Qualifier=v['Version'],
            )

    response = lambda_client.list_versions_by_function(FunctionName=function_name)
    destroy_function_versions(response.get('Versions', []))
    while response.get('NextMarker', None):
        response = lambda_client.list_versions_by_function(
            FunctionName=function_name,
            Marker=response['NextMarker'],
        )
        destroy_function_versions(response.get('Versions', []))

    import pytest
    pytest.set_trace()
    lambda_client.delete_function(
        FunctionName=function_name,
        Qualifier='$LATEST',
    )


def test_layer_deployment(iam_role):
    suffix = get_temp_suffix()
    function_name = 'temp-function-' + suffix
    layer_name = 'temp-layer-' + suffix
    bucket_name = 'temp-bucket-' + suffix
    object_key = upload_sample_bundle(bucket_name)

    lambda_client = boto3.client('lambda')

    versions = lambda_client.list_layer_versions(
        LayerName=layer_name)['LayerVersions']
    LOGGER.info('versions of layer %s = %s', layer_name, versions)
    last_version = sorted(versions, reverse=True, key=lambda v: v['Version'])[0]
    layer_arn = last_version['LayerVersionArn']

    with ExitStack() as stack:
        role_arn = stack.enter_context(iam_role())

        for i in range(6):
            try:
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
                        layer_arn,
                    ],
                )
            except lambda_client.exceptions.ClientError as e:
                LOGGER.error('Lambda error: %s', str(e))
                time.sleep(3)
            else:
                LOGGER.info('Function %s created', function_name)
                break
        else:
            raise Exception('Too many attempts')

        stack.callback(
            log_call(LOGGER, lambda_client.delete_function),
            FunctionName=function_name,
        )
        invocation = lambda_client.invoke(
            FunctionName=function_name,
            LogType='None',
        )
        payload = invocation['Payload'].read().decode('utf-8')
        LOGGER.info('payload = %s', payload)

        response = json.loads(json.loads(payload)['body'])
        assert response['rails'] == '5.2.3'
