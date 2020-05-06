""" Storage for logging utils """
import logging


def return_logger(name='django'):
    """ Logger fetch from Django settings conf """
    return logging.getLogger(name)
