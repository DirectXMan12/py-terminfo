import struct
import collections
import logging

__all__ = ['TermInfo']

# the man page uses octal...?
_MAGIC_NUMBER = 0o432
# _NEGATIVE_INT is actually 0xffff -- seriously, who specifies *that* in octal?
_NEGATIVE_INT = 0o377*256 + 0o377


class ExtFlagsInfoProxy(collections.Set):
    def __init__(self, caps):
        self._caps = caps

    def __contains__(self, flag):
        return self._caps.get(flag, False)

    def __iter__(self):
        for cap, val in self._caps.items():
            if not val:
                continue
            else:
                yield cap

    def __len__(self):
        return sum(val for val in self._caps.values())

    def __repr__(self):
        return '<Extended Capabilites(flags) [%s]>' % (', '.join(self))


class FlagsCapInfoProxy(collections.Set):
    def __init__(self, info, caps):
        self._info = info
        self._caps = caps

    def __contains__(self, flag):
        return self._caps.get(flag, False)

    def __iter__(self):
        for ind, cap in enumerate(self._caps):
            if not cap:
                continue
            else:
                yield self._info[ind].name

    def __len__(self):
        return sum(cap for cap in self._caps)

    def __repr__(self):
        return '<Capabilites(flags) [%s]>' % (', '.join(self))


class CapInfoProxy(collections.Mapping):
    def __init__(self, type, info, caps):
        self._info = info
        self._caps = caps
        self._type = type

    def __getitem__(self, key):
        info = self._info.by_variable_name(key, None)

        if info is None:
            info = self._info.by_cap_name(key, None)

        if info is None:
            raise KeyError(key)

        res = self._caps[info.number]
        if res is None:
            raise KeyError(key)
        else:
            return res

    def __iter__(self):
        for ind, cap in enumerate(self._caps):
            # zero or '' are ok
            if cap is None:
                continue
            else:
                yield self._info[ind].name

    def __len__(self):
        return sum(cap is not None for cap in self._caps)

    def __repr__(self):
        return '<Capabilites(%s) {%s}>' % (
            self._type, ', '.join('%s: %s' % (k, repr(v))
                                  for k, v in self.items()))


class ExtInfoProxy(collections.Mapping):
    def __init__(self, type, caps):
        self._caps = caps
        self._type = type

    def __getitem__(self, key):
        return self._caps[key]

    def __iter__(self):
        for cap, val in self._caps.items():
            # zero or '' are ok
            if val is None:
                continue
            else:
                yield cap

    def __len__(self):
        return sum(val is not None for val in self._caps.values())

    def __repr__(self):
        return '<Capabilites(%s) {%s}>' % (
            self._type, ', '.join('%s: %s' % (k, repr(v))
                                  for k, v in self.items()))


class TermInfo(object):
    def __init__(self, contents, cap_info, parse_extended=True):
        self._parse_extended = parse_extended
        self.has_extended_capabilities = False

        self.names = None

        self._flags = None
        self._numbers = None
        self._strings = None

        self._ext_flags = None
        self._ext_numbers = None
        self._ext_strings = None

        self._flags_proxy = None
        self._numbers_proxy = None
        self._strings_proxy = None

        self._ext_flags_proxy = None
        self._ext_numbers_proxy = None
        self._ext_strings_proxy = None

        self._cap_info = cap_info

        self._parse(contents)

    @classmethod
    def _calc_caps_block_size(cls, num_bools, num_numbers, num_strs,
                              str_table_size, start_offset_is_even):
        res = num_bools + (num_numbers + num_strs) * 2 + str_table_size
        if start_offset_is_even and num_bools % 2 == 1:
            res += 1

        return res

    @property
    def flags(self):
        if self._flags is None:
            return None

        if self._flags_proxy is None:
            self._flags_proxy = FlagsCapInfoProxy(self._cap_info.flags,
                                                  self._flags)

        return self._flags_proxy

    @property
    def numbers(self):
        if self._numbers is None:
            return None

        if self._numbers_proxy is None:
            self._numbers_proxy = CapInfoProxy('numbers',
                                               self._cap_info.numbers,
                                               self._numbers)

        return self._numbers_proxy

    @property
    def strings(self):
        if self._strings is None:
            return None

        if self._strings_proxy is None:
            self._strings_proxy = CapInfoProxy('strings',
                                               self._cap_info.strings,
                                               self._strings)

        return self._strings_proxy

    @property
    def extended_flags(self):
        if self._ext_flags is None:
            return None

        if self._ext_flags_proxy is None:
            self._ext_flags_proxy = ExtFlagsInfoProxy(self._ext_flags)

        return self._ext_flags_proxy

    @property
    def extended_numbers(self):
        if self._ext_numbers is None:
            return None

        if self._ext_numbers_proxy is None:
            self._ext_numbers_proxy = ExtInfoProxy('numbers',
                                                   self._ext_numbers)

        return self._ext_numbers_proxy

    @property
    def extended_strings(self):
        if self._ext_strings is None:
            return None

        if self._ext_strings_proxy is None:
            self._ext_strings_proxy = ExtInfoProxy('strings',
                                                   self._ext_strings)

        return self._ext_strings_proxy

    def __repr__(self):
        return '<TermInfo(%s): flags#%s, numbers#%s, strings#%s, ext=%s>' % (
            self.names[0], len(self.flags) + len(self.extended_flags or []),
            len(self.numbers) + len(self.extended_numbers or []),
            len(self.strings) + len(self.extended_strings or []),
            self.has_extended_capabilities)

    @classmethod
    def _read_caps_block(cls, block, num_bools, num_numbers, num_offsets,
                         str_table_size, start_offset_is_even, num_strs=None):
        ind = 0
        logging.debug('Read %s booleans @ %s' % (num_bools, ind))
        flags = [b == '\x01' for b in block[ind:(ind + num_bools)]]

        # the numbers section always begins on an even byte because PDP-11
        ind += num_bools
        if ind % 2 != 0 and start_offset_is_even:
            ind += 1

        # a list of unsigned shorts, with _NEGATIVE_INT representing -1,
        # which means missing
        logging.debug('Read %s numbers @ %s' % (num_numbers, ind))
        numbers_raw = struct.unpack('<%sH' % num_numbers,
                                    block[ind:(ind + (num_numbers * 2))])
        numbers = [num if num != _NEGATIVE_INT else None
                   for num in numbers_raw]

        # a list of offsets in the string table, with _NEGATIVE_INT
        # representing -1, # which means missing
        ind += num_numbers * 2

        logging.debug('Reading %s offsets @ %s' % (num_offsets, ind))
        offsets_raw = struct.unpack('<%sH' % num_offsets,
                                    block[ind:(ind + (num_offsets * 2))])

        offsets = [offset if offset != _NEGATIVE_INT else None
                   for offset in offsets_raw]

        # for the extended info
        if num_strs is not None:
            names_offsets = offsets[num_strs:]
            offsets = offsets[:num_strs]

        # a "table" of null-terminated strings referenced by the offsets above
        ind += num_offsets * 2
        logging.debug('Reading %s bytes of strings @ %s' % (str_table_size,
                                                            ind))
        raw_table = block[ind:(ind + str_table_size)]

        strings = []
        end_ind = 0
        for offset in offsets:
            if offset is None:
                strings.append(None)
            else:
                end_ind = raw_table.index(b'\0', offset)
                strings.append(raw_table[offset:end_ind])

        # read the names section
        if num_strs is not None:
            names_start = end_ind + 1
            logging.debug('Reading %s names starting @ %s in the string table'
                          % (len(names_offsets), names_start))
            for offset in names_offsets:
                end_ind = raw_table.index(b'\0', names_start + offset)
                # we can safely decode these because they're human-readable names
                strings.append(raw_table[names_start + offset:end_ind].decode())

        return (flags, numbers, strings)

    def _parse(self, block):
        # terminfo uses little endian unsigned shorts for lengths and offsets
        magic_number = struct.unpack('<H', block[0:2])[0]
        if magic_number != _MAGIC_NUMBER:
            raise Exception("Expected magic number %s for a terminfo file, "
                            "got %s instead" % (_MAGIC_NUMBER, magic_number))

        (names_size, num_bools, num_numbers,
            num_strs, str_table_size) = struct.unpack('<5H', block[2:12])

        logging.debug('Main Terminfo Block: name_size=%s, bools=%s, nums=%s, '
                      'strs=%s(%s)' % (names_size, num_bools, num_numbers,
                                       num_strs, str_table_size))

        # null terminated string of names separated by '|'
        ind = 12
        self.names = [name.decode() for name
                      in block[ind:(ind + names_size - 1)].split(b'|')]

        # a list of boolean bytes as either 0 or 1
        ind += names_size

        caps_size = self._calc_caps_block_size(
            num_bools, num_numbers, num_strs, str_table_size, ind % 2 == 0)
        self._flags, self._numbers, self._strings = self._read_caps_block(
            block[ind:(ind + caps_size)], num_bools, num_numbers, num_strs,
            str_table_size, ind % 2 == 0)

        if not self._parse_extended:
            return

        ind += caps_size
        if ind < len(block):
            self.has_extended_capabilities = True
            logging.debug('Extended Header @ %s' % ind)
            # we have an extended terminfo

            # NB(directxman12): the term(5) manpage doesn't describe this
            # properly -- what is calls "the size of the string table" is
            # actually the number of strings in the table (including names),
            # and what it calls the "last offset in the string table" is
            # actually the size in bytes of the string table
            (num_ext_bools, num_ext_numbers, num_ext_strs,
                num_strs_in_ext_table, ext_str_table_size) = struct.unpack(
                    '<5H', block[ind:(ind + 10)])

            logging.debug('Extended Terminfo Block: bools=%s, nums=%s, '
                          'strs=%s(%s:%s)' % (num_ext_bools, num_ext_numbers,
                                              num_ext_strs,
                                              num_strs_in_ext_table,
                                              ext_str_table_size))

            ind += 10
            ext_caps_size = self._calc_caps_block_size(
                num_ext_bools, num_ext_numbers, num_strs_in_ext_table,
                ext_str_table_size, ind % 2 == 0)

            ext_flags, ext_numbers, all_ext_strings = self._read_caps_block(
                block[ind:(ind + ext_caps_size)], num_ext_bools,
                num_ext_numbers, num_strs_in_ext_table,
                ext_str_table_size, ind % 2 == 0, num_ext_strs)

            ext_strings = all_ext_strings[:num_ext_strs]
            ext_names = all_ext_strings[num_ext_strs:]

            self._ext_flags = {}
            names_ind = 0
            for ind, flag in enumerate(ext_flags):
                self._ext_flags[ext_names[names_ind + ind]] = flag

            names_ind += len(ext_flags)
            self._ext_numbers = {}
            for ind, num in enumerate(ext_numbers):
                self._ext_numbers[ext_names[names_ind + ind]] = num

            names_ind += len(ext_numbers)
            self._ext_strings = {}
            for ind, string in enumerate(ext_strings):
                self._ext_strings[ext_names[names_ind + ind]] = string

            ind += ext_caps_size
