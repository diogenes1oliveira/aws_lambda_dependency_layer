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


def get_temp_path():
    return os.getenv(
        'MOLECULE_EPHEMERAL_DIRECTORY',
        '/tmp/molecule/lambda-dependency-layer/default/',
    )


def get_temp_suffix():
    with open(os.path.join(get_temp_path(), 'temp-suffix.txt')) as fp:
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


def test_layer_deployment(iam_role):
    suffix = get_temp_suffix()
    function_name = 'temp-function-' + suffix
    layer_name = 'temp-layer-' + suffix
    bucket_name = 'temp-bucket-' + suffix
    object_key = upload_sample_bundle(bucket_name)

    connection_args = {}
    if os.getenv('LAMBDA_URL', None):
        connection_args['endpoint_url'] = os.environ['LAMBDA_URL']
    if os.getenv('AWS_DEFAULT_REGION', None):
        connection_args['region_name'] = os.environ['AWS_DEFAULT_REGION']
    lambda_client = boto3.client('lambda', **connection_args)

    versions = lambda_client.list_layer_versions(
        LayerName=layer_name)['LayerVersions']
    LOGGER.info('versions of layer %s = %s', layer_name, versions)
    last_version = sorted(versions, reverse=True,
                          key=lambda v: v['Version'])[0]
    layer_version_arn = last_version['LayerVersionArn']

    layer_info = lambda_client.get_layer_version(
        LayerName=layer_name,
        VersionNumber=last_version['Version'],
    )

    with open(os.path.join(get_temp_path(), 'role-variables-main.json')) as fp:
        main_vars = json.load(fp)

    assert main_vars['aws_lambda_dependency_layer_state'] == 'present'
    assert main_vars['aws_lambda_dependency_layer_name'] == layer_name
    assert main_vars['aws_lambda_dependency_layer_arn'] == layer_info['LayerArn']
    assert main_vars['aws_lambda_dependency_layer_version'] == str(
        last_version['Version'])
    assert main_vars['aws_lambda_dependency_layer_version_arn'] == layer_version_arn

    with ExitStack() as stack:
        role_arn = stack.enter_context(iam_role())

        for i in range(6):
            try:
                lambda_client.create_function(
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
                        layer_version_arn,
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


def test_exported_variables():
    suffix = get_temp_suffix()
    layer_name = 'temp-layer-2-' + suffix

    connection_args = {}
    if os.getenv('LAMBDA_URL', None):
        connection_args['endpoint_url'] = os.environ['LAMBDA_URL']
    if os.getenv('AWS_DEFAULT_REGION', None):
        connection_args['region_name'] = os.environ['AWS_DEFAULT_REGION']
    lambda_client = boto3.client('lambda', **connection_args)

    response = lambda_client.list_layer_versions(
        LayerName=layer_name,
    )

    assert not response.get('LayerVersions', [])

    with open(os.path.join(get_temp_path(), 'role-variables-side-effects-present.json')) as fp:
        vars_presence = json.load(fp)
    with open(os.path.join(get_temp_path(), 'role-variables-side-effects-absent.json')) as fp:
        vars_absence = json.load(fp)
    with open(os.path.join(get_temp_path(), 'role-variables-check-present.json')) as fp:
        vars_presence_check = json.load(fp)
    with open(os.path.join(get_temp_path(), 'role-variables-check-absent.json')) as fp:
        vars_absence_check = json.load(fp)

    assert vars_presence['aws_lambda_dependency_layer_name'] == layer_name
    assert vars_absence['aws_lambda_dependency_layer_name'] == layer_name
    assert vars_presence['aws_lambda_dependency_layer_state'] == 'present'
    assert vars_absence['aws_lambda_dependency_layer_state'] == 'absent'

    assert vars_presence.get('aws_lambda_dependency_layer_arn', None)
    assert not vars_absence.get('aws_lambda_dependency_layer_arn', None)
    assert vars_presence.get('aws_lambda_dependency_layer_version', None)
    assert not vars_absence.get('aws_lambda_dependency_layer_version', None)
    assert vars_presence.get('aws_lambda_dependency_layer_version_arn', None)
    assert not vars_absence.get(
        'aws_lambda_dependency_layer_version_arn', None)

    assert vars_presence_check['aws_lambda_dependency_layer_state'] == 'present'
    assert vars_absence_check['aws_lambda_dependency_layer_state'] == 'absent'
