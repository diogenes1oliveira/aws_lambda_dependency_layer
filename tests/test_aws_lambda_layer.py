import logging
import os
import sys
from uuid import uuid4
from zipfile import ZipFile

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)
MY_PATH = os.path.dirname(os.path.abspath(__file__))


def create_zip(path, suffix):
    with ZipFile(path, 'w') as zip_fp:
        with zip_fp.open('bin/layer.sh', 'w') as fp:
            fp.write(f'echo "{suffix}"'.encode('ascii'))


def test_layer_creation(temp_bucket, tmp_path):
    suffix = str(uuid4()).replace('-', '')[:10]
    name = 'temp-lambda-layer-' + suffix
    object_key = 'layer.zip'

    # Create the layer bundle
    path = str(tmp_path / 'layer.zip')
    create_zip(path, suffix)

    # Import the library
    library_path = os.path.join(os.path.dirname(MY_PATH), 'library')
    if sys.path[0] != library_path:
        sys.path.insert(0, library_path)
    from aws_lambda_layer import manage_lambda_layer, get_layer_version_info

    with temp_bucket() as bucket:
        state = 'present'
        # First deployed version
        result1 = manage_lambda_layer(
            name, bucket, object_key, None, path, 'present')
        assert result1['version'] == 1
        assert result1['version_arn']

        # Trying to deploy the same version
        result2 = manage_lambda_layer(
            name, bucket, object_key, None, path, 'present')
        assert result2['version_arn'] == result1['version_arn']
        assert result1['version_checksum'] == result2['version_checksum']
        assert not result2['changed']
        assert not result2['downloaded']

        # Trying to deploy the same version with a different metadata key
        result3 = manage_lambda_layer(
            name, bucket, object_key, None, path, 'present', metadata='unique')
        assert result3['version_arn'] == result2['version_arn']
        assert not result3['changed']
        assert result3['downloaded']

        # Deploying a different bundle
        create_zip(path, suffix)
        result4 = manage_lambda_layer(
            name, bucket, object_key, None, path, 'present')
        assert result4['version_arn'] == result1['version_arn']
        assert result1['version_checksum'] == result4['version_checksum']
        assert not result4['changed']
        assert not result4['downloaded']

        assert get_layer_version_info(name)
        manage_lambda_layer(name, None, None, None, None, 'absent')
        assert not get_layer_version_info(name)
