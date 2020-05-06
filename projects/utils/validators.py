from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def validate_name(value):
    """ Validating data. Pattern is ASCII letter, digits and _ symbol

    Raises:
        ValidationError: Would be render if form is invalid!

    """
    for char in value:
        if char not in settings.VALIDATOR_SYMBOLS:
            error_msg = _(
                f'is not valid. {settings.VALIDATOR_SYMBOLS} are allowed'
            )
            raise ValidationError(f'{value} {error_msg}')


def validate_speed_accuracy(value):
    """ Checking if speed is OK with our representation

    Args:
        value: DecimalField value from the django model

    """
    if value > 3 or value < 0.09999:
        raise ValidationError('Speed should be between 0.1 and 3')


def validate_file_extension(value):
    """ Validate file ext in the system

    Args:
        value: File from the File django sys

    Raises:
        ValidationError if file doesn't have .xls, .csv or .xlsx extension

    """
    exts = ('csv', 'xls', 'xlsx', 'imed')
    file_ext = value.name.split('.')[-1]
    if file_ext not in exts:
        raise ValidationError('File is not xls(x)/csv or imed')


def validate_file_not_none(value):
    """ Validate file is not None

    Args:
        value: File from the File django sys

    Raises:
        ValidationError if file doesn't exist

    """
    if bool(value.file) is False:
        raise ValidationError('No file were provided')
