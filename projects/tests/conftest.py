import logging

import pytest


@pytest.fixture(autouse=True)
def disable_logging():
    """ Do not log anything at any point of tests run """
    logging.disable(50)
    yield
    logging.disable(0)
