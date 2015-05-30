import os
import pickle
import logging
from collections import namedtuple


__all__ = ['CAP_NAMES', 'INFO_BY_CAP_NAME', 'INFO_BY_VAR_NAME', 'ALIASES',
           'load_cap_info']


CAP_NAMES = {'flags': [], 'numbers': [], 'strings': []}
INFO_BY_CAP_NAME = {}
INFO_BY_VAR_NAME = {}
ALIASES = {'termcap': {}, 'terminfo': {}}

_CAP_TYPES = {'bool': 'flags', 'num': 'numbers', 'str': 'strings'}
Capability = namedtuple('Capability', ['variable_name', 'cap_name', 'type',
                                       'old_cap_name', 'key_name',
                                       'key_value', 'versions',
                                       'description'])
_ALIAS_TYPES = {'capalias': 'termcap', 'infoalias': 'terminfo'}
Alias = namedtuple('Alias', ['type', 'name', 'alias', 'extension',
                             'description'])


def load_cap_info(caps_file=None, cache_file=None):
    global CAP_NAMES, INFO_BY_CAP_NAME, INFO_BY_VAR_NAME, ALIASES

    if cache_file is not None:
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                (CAP_NAMES, INFO_BY_CAP_NAME,
                 INFO_BY_VAR_NAME, ALIASES) = pickle.load(f)

            return

    if caps_file is None:
        if cache_file is None:
            raise Exception('No capabilities table file was specified, and '
                            'no cache file was specified.')
        else:
            raise Exception('No capabilities table file was specified, and '
                            'cache file "%s" does not exist.' % cache_file)

    with open(caps_file, 'r') as f:
        _load_cap_info(f)

    if cache_file is not None:
        with open(cache_file, 'wb') as f:
            pickle.dump(
                (CAP_NAMES, INFO_BY_CAP_NAME, INFO_BY_VAR_NAME, ALIASES), f)


def _load_cap_info(caps_file):
    for line in caps_file:
        if line[0] == '#':
            continue
        elif '# ' in line:
            line = line[:line.index('# ')]

        if not line or line.isspace():
            continue

        if line.startswith('capalias') or line.startswith('infoalias'):
            parts = line.split(None, 4)

            if len(parts) < 5:
                logging.warn('Skipping caps line "%s"' % line)
                continue

            (alias_type, name, alias, extension, desc) = parts
            ALIASES[_ALIAS_TYPES[alias_type]] = Alias(
                _ALIAS_TYPES[alias_type], name, alias, extension, desc)
        else:
            parts = line.split(None, 7)

            if len(parts) < 8:
                logging.warn('Skipping caps line "%s"' % line)
                continue

            (var_name, cap_name, cap_type, tcap_cap_name, key_name,
             key_value, versions, cap_desc) = parts

            if key_name == '-':
                key_name = None

            if key_value == '-':
                key_value = None

            CAP_NAMES[_CAP_TYPES[cap_type]].append(cap_name)
            info = Capability(var_name, cap_name, _CAP_TYPES[cap_type],
                              tcap_cap_name, key_name, key_value, versions,
                              cap_desc)

            INFO_BY_CAP_NAME[cap_name] = info
            INFO_BY_VAR_NAME[var_name] = info
