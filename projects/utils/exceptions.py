import json


class AudioRecordsDoNotExist(Exception):
    """ Custom exception for Loadout classes """


class TTSBackendIsUnavailable(Exception):
    """ Checking if response code is 200 """


class YandexCloudAPIError(object):

    def __init__(self, error_text):
        """ Wrapper class above YSK error messages

        Args:
            error_text: Text content of the HTTP response (requests lib)

        Notes:
            error_text must be in JSON format

        """
        js_er = json.loads(error_text)
        self.status = js_er['error_status']
        self.error = js_er['error_message']


class ChosenSpeedIsUnavailable(Exception):
    """ Checking that speed is between 3 and 0.1 """


class DuplicatingAudioRecord(Exception):
    """ Thrown in case of creating AudioRecord with the same name """


class FileUploadParseError(Exception):
    """ Thrown in case of file uploading and TTS backend unavailability """


class ReadUserDataFileError(Exception):
    """ Thrown in case of file corruption or etc (when tried to be parsed) """
