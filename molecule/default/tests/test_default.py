import logging
import os

LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(os.getenv('LOGGING_LEVEL') or logging.INFO)


def test(iam_role):
    with iam_role() as role:
        LOGGER.info(role)
