from typing import Optional, Any


__all__ = (
    'OptionalValue',
    'OptionalValueInteger',
)


class OptionalValue:

    regex = '.*'

    def to_python(self, value: str) -> Optional[str]:
        """ Convert any string url matched to string value """
        return value if value else None

    def to_url(self, value: Any):
        """ Convert given data to a url string """
        return str(value) if value is not None else ''


class OptionalValueInteger:

    regex = '.*'

    def to_python(self, value: str) -> Optional[int]:
        """ Convert any string url matched to string value """
        return int(value) if value else None

    def to_url(self, value: Any):
        """ Convert given data to a url string """
        return str(value) if value is not None else ''
