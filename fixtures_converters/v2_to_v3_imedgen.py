""" Convert old v2 imedgen project models to a v3 ones (via fixtures) """
import argparse
import json
import os
import pathlib
import sys
import uuid

from typing import List, Dict, Any, Mapping, Optional

CUR_PATH = pathlib.Path(os.path.dirname(__file__))

OLD_TO_NEW_VOICES = {
    1: 'alyss',
    2: 'jane',
    3: 'oksana',
    4: 'omazh',
    5: 'zahar',
    6: 'ermil',
    7: 'Vladimir8000',
    8: 'Julia8000',
    9: 'Anna8000',
    10: 'Viktoriya8000',
    11: 'Alexander8000',
    12: 'Maria8000',
    13: 'Lydia8000',
    14: 'Carol8000',
    15: 'Asel8000',
}


def get_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """ Fetch args for current script """
    parser.add_argument('path', help='Path to an old fixture file')
    parser.add_argument('--export_to', help='Path for a new fixture')
    return parser.parse_args()


def _read_json(path: pathlib.Path) -> List[Dict[str, Any]]:
    """ Extract json body from fixture """
    with open(str(path), 'r') as reader:
        content = reader.read()
    return json.loads(content)


def _write_json(path: pathlib.Path, content: List[Dict[str, Any]]) -> None:
    """ Write JSON result to a new file """
    with open(str(path), 'w') as writer:
        writer.write(json.dumps(content, indent=4))
    return None


def _migrate_audio_records(content: Dict[str, Any]) -> Mapping[str, Any]:
    """ Make actual changes to audio records fields content """
    new_content = content.copy()
    del new_content['slug']
    new_content['voice'] = OLD_TO_NEW_VOICES[content['voice']]
    emote = content['emote']
    new_content['emote'] = emote if emote else 'Not specified'
    tts = new_content.pop('tts_backend')
    new_content['source'] = 1 if tts == 2 else 2
    return new_content


def _migrate_projects(content: Dict[str, Any]) -> Mapping[str, Any]:
    """ Make actual changes to integration projects fields content """
    new_content = content.copy()
    new_content['last_updated'] = new_content.pop('created_at')
    return new_content


def rebuild(from_p: pathlib.Path, to_p: pathlib.Path) -> None:
    """ Convert v2 format to v3 without pain """
    data = _read_json(from_p)
    version_idx: Optional[int] = None
    for index, entry in enumerate(data):
        model: str = entry['model']
        content: Dict[str, Any] = entry['fields']
        if model == 'projects.audiorecord':
            new_content = _migrate_audio_records(content)
        elif model == 'projects.integrationproject':
            new_content = _migrate_projects(content)
        elif model == 'projects.projectversion':
            version_idx = index
            continue
        else:
            continue

        entry['fields'] = new_content

    if version_idx:
        data.pop(version_idx)

    _write_json(to_p, data)
    return None


def main(namespace: argparse.Namespace) -> None:
    """ Parse args and execute migration scenario """
    old_fixture = namespace.path
    if not pathlib.Path(old_fixture).exists():
        raise ValueError(f'This path does not exists - {old_fixture}')

    if namespace.export_to:
        new_fixture = pathlib.Path(namespace.export_to).name
    else:
        new_fixture = CUR_PATH / f'newFixture_{uuid.uuid4().hex}'

    rebuild(old_fixture, new_fixture)
    return None


if __name__ == '__main__':
    parser_ = argparse.ArgumentParser()
    namespace_ = get_args(parser_)
    main(namespace_)
    sys.exit(0)
