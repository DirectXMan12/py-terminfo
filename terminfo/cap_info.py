import os
import pickle
import logging
from collections import namedtuple, Sequence


__all__ = ['CapInfo', 'load_cap_info']


class CapTypeInfo(Sequence):
    def __init__(self, type, info_list, aliases):
        self._type = type
        self._info = info_list
        self._aliases = aliases
        self._by_var_name = {}
        self._by_cap_name = {}
        for info in self._info:
            self._by_var_name[info.variable_name] = info
            self._by_cap_name[info.name] = info

    def by_variable_name(self, name, default=None):
        return self._by_var_name.get(name, default)

    def by_cap_name(self, name, default=None):
        if name in self._aliases:
            name = self._aliases[name].actual_name

        return self._by_cap_name.get(name, default)

    def __getitem__(self, ind):
        return self._info[ind]

    def __len__(self):
        return len(self._info)

    def __iter__(self):
        for info in self._info:
            yield info

    def __repr__(self):
        return ('<Capabilities Sub-Table(%s): '
                '%s entries>') % (self._type, len(self._info))


_CAP_TYPES = {'bool': 'flags', 'num': 'numbers', 'str': 'strings'}
Capability = namedtuple('Capability', ['number', 'name', 'variable_name',
                                       'type', 'old_cap_name', 'key_name',
                                       'key_value', 'versions', 'description'])

_ALIAS_TYPES = {'capalias': 'termcap', 'infoalias': 'terminfo'}
Alias = namedtuple('Alias', ['type', 'alias', 'actual_name', 'extension',
                             'description'])


class CapInfo(object):
    def __init__(self, flags=None, numbers=None, strings=None, aliases=None):
        self._flags = flags or []
        self._numbers = numbers or []
        self._strings = strings or []

        self.aliases = aliases or {'termcap': {}, 'terminfo': {}}

        self.strings = CapTypeInfo('strings', strings, aliases['terminfo'])
        self.numbers = CapTypeInfo('numbers', numbers, aliases['terminfo'])
        self.flags = CapTypeInfo('flags', flags, aliases['terminfo'])

    def __reduce__(self):
        return (type(self),
                (self._flags, self._numbers, self._strings, self.aliases))

    def __repr__(self):
        aliases_count = (len(self.aliases['termcap']) +
                         len(self.aliases['terminfo']))
        return ('<Capabilites Table: flags#%s, numbers#%s, strings#%s, '
                'aliases#%s>') % (len(self._flags), len(self._numbers),
                                  len(self._strings), aliases_count)

    def __len__(self):
        return (len(self._flags) + len(self._numbers) + len(self._strings) +
                len(self.aliases['termcap']) + len(self.aliases['terminfo']))

    def find(self, cap_name=None, variable_name=None):
        if variable_name is not None:
            return (self.flags.by_variable_name(variable_name) or
                    self.numbers.by_variable_name(variable_name) or
                    self.strings.by_variable_name(variable_name))
        elif cap_name is not None:
            return (self.flags.by_cap_name(cap_name) or
                    self.numbers.by_cap_name(cap_name) or
                    self.strings.by_cap_name(cap_name))
        else:
            raise KeyError(None)

    @classmethod
    def loads(cls, content):
        return cls._load(content.splitlines())

    @classmethod
    def load(cls, content):
        counts = {'flags': 0, 'numbers': 0, 'strings': 0}
        aliases = {'termcap': {}, 'terminfo': {}}
        infos = {'flags': [], 'numbers': [], 'strings': []}
        for line in content:
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

                (alias_type, alias, actual_name, extension, desc) = parts

                if actual_name == 'IGNORE':
                    actual_name = None

                type_name = _ALIAS_TYPES[alias_type]
                aliases[type_name][alias] = Alias(
                    type_name, alias, actual_name, extension, desc.rstrip())
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

                type_name = _CAP_TYPES[cap_type]

                info = Capability(counts[type_name], cap_name, var_name,
                                  type_name, tcap_cap_name, key_name,
                                  key_value, versions, cap_desc.rstrip())

                infos[type_name].append(info)
                counts[type_name] += 1

        return cls(infos['flags'], infos['numbers'], infos['strings'], aliases)


def load_cap_info(caps_file=None, cache_file=None):
    if cache_file is not None:
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

    if caps_file is None:
        if cache_file is None:
            raise Exception('No capabilities table file was specified, and '
                            'no cache file was specified.')
        else:
            raise Exception('No capabilities table file was specified, and '
                            'cache file "%s" does not exist.' % cache_file)

    with open(caps_file, 'r') as f:
        res = CapInfo.load(f)

    if cache_file is not None:
        with open(cache_file, 'wb') as f:
            pickle.dump(res, f)

    return res
