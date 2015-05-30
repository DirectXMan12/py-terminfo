import struct
from collections import namedtuple
import logging

# the man page uses octal...?
MAGIC_NUMBER = 0o432
# NEGATIVE_INT is actually 0xffff -- seriously, who specifies *that* in octal?
NEGATIVE_INT = 0o377*256 + 0o377


TermInfo = namedtuple('TermInfo', ['names', 'flags', 'numbers', 'strings',
                                   'extended_flags', 'extended_numbers',
                                   'extended_strings'])


def calc_caps_size(bools, numbers, strs, str_table_size, start_offset_is_even):
    res = bools + numbers * 2 + strs * 2 + str_table_size
    if start_offset_is_even and bools % 2 != 0:
        res += 1

    return res


def read_caps(contents, num_bools, num_numbers, num_strs, str_table_size,
              start_offset_is_even, num_act_strs=None):
    ind = 0
    logging.debug('Read %s booleans @ %s' % (num_bools, ind))
    flags = [b == '\x01' for b in contents[ind:(ind + num_bools)]]

    # the numbers section always begins on an even byte because PDP-11
    ind += num_bools
    if ind % 2 != 0 and start_offset_is_even:
        ind += 1

    # a list of unsigned shorts, with NEGATIVE_INT representing -1,
    # which means missing
    logging.debug('Read %s numbers @ %s' % (num_numbers, ind))
    numbers_raw = struct.unpack('<%sH' % num_numbers,
                                contents[ind:(ind + (num_numbers * 2))])
    numbers = [num if num != NEGATIVE_INT else None for num in numbers_raw]

    # a list of offsets in the string table, with NEGATIVE_INT representing -1,
    # which means missing
    ind += num_numbers * 2

    logging.debug('Reading %s offsets @ %s' % (num_strs, ind))
    offsets_raw = struct.unpack('<%sH' % num_strs,
                                contents[ind:(ind + (num_strs * 2))])

    offsets = [offset if offset != NEGATIVE_INT else None
               for offset in offsets_raw]

    # for the extended info
    if num_act_strs is not None:
        names_offsets = offsets[num_act_strs:]
        offsets = offsets[:num_act_strs]

    # a "table" of null-terminated strings referenced by the offsets above
    ind += num_strs * 2
    logging.debug('Reading %s bytes of strings @ %s' % (str_table_size, ind))
    raw_table = contents[ind:(ind + str_table_size)]

    strings = []
    end_ind = 0
    for offset in offsets:
        if offset is None:
            strings.append(None)
        else:
            end_ind = raw_table.index('\0', offset)
            strings.append(raw_table[offset:end_ind])

    # read the names section
    if num_act_strs is not None:
        names_start = end_ind + 1
        logging.debug('Reading %s names starting @ %s in the string table'
                      % (len(names_offsets), names_start))
        for offset in names_offsets:
            end_ind = raw_table.index('\0', names_start + offset)
            strings.append(raw_table[names_start + offset:end_ind])

    return (flags, numbers, strings)


def parse_terminfo(contents):
    # terminfo uses little endian unsigned shorts for many things
    magic_number = struct.unpack('<H', contents[0:2])[0]
    if magic_number != MAGIC_NUMBER:
        raise Exception("Expected magic number %s for a terminfo file, "
                        "got %s instead" % (MAGIC_NUMBER, magic_number))

    (names_size, num_bools, num_numbers,
        num_strs, str_table_size) = struct.unpack('<5H', contents[2:12])

    logging.debug('Main Terminfo Block: name_size=%s, bools=%s, nums=%s, '
                  'strs=%s(%s)' % (names_size, num_bools, num_numbers,
                                   num_strs, str_table_size))

    # null terminated string of names separated by '|'
    ind = 12
    names = contents[ind:(ind + names_size - 1)].split('|')

    # a list of boolean bytes as either 0 or 1
    ind += names_size

    caps_size = calc_caps_size(num_bools, num_numbers, num_strs,
                               str_table_size, ind % 2 == 0)
    flags, numbers, strings = read_caps(contents[ind:(ind + caps_size)],
                                        num_bools, num_numbers, num_strs,
                                        str_table_size, ind % 2 == 0)

    res = {'names': names, 'flags': flags, 'numbers': numbers,
           'strings': strings, 'extended_flags': None,
           'extended_numbers': None, 'extended_strings': None}

    ind += caps_size
    if ind < len(contents):
        logging.debug('Extended Header @ %s' % ind)
        # we have an extended terminfo

        # NB(directxman12): the term(5) manpage doesn't describe this
        # properly -- what is calls "the size of the string table" is actually
        # the number of strings in the table (including names), and what it
        # calls the "last offset in the string table" is actually the size in
        # bytes of the string table
        (num_ext_bools, num_ext_numbers, num_ext_strs,
            num_strs_in_ext_table, ext_str_table_size) = struct.unpack(
                '<5H', contents[ind:(ind + 10)])

        logging.debug('Extended Terminfo Block: bools=%s, nums=%s, '
                      'strs=%s(%s:%s)' % (num_ext_bools, num_ext_numbers,
                                          num_ext_strs, num_strs_in_ext_table,
                                          ext_str_table_size))

        ind += 10
        ext_caps_size = calc_caps_size(num_ext_bools, num_ext_numbers,
                                       num_strs_in_ext_table,
                                       ext_str_table_size, ind % 2 == 0)

        ext_flags, ext_numbers, all_ext_strings = read_caps(
            contents[ind:(ind + ext_caps_size)], num_ext_bools,
            num_ext_numbers, num_strs_in_ext_table,
            ext_str_table_size, ind % 2 == 0, num_ext_strs)

        ext_strings = all_ext_strings[:num_ext_strs]
        ext_names = all_ext_strings[num_ext_strs:]

        res['extended_flags'] = {}
        names_ind = 0
        for ind, flag in enumerate(ext_flags):
            res['extended_flags'][ext_names[names_ind + ind]] = flag

        names_ind += len(ext_flags)
        res['extended_numbers'] = {}
        for ind, num in enumerate(ext_numbers):
            res['extended_numbers'][ext_names[names_ind + ind]] = num

        names_ind += len(ext_numbers)
        res['extended_strings'] = {}
        for ind, string in enumerate(ext_strings):
            res['extended_strings'][ext_names[names_ind + ind]] = string

        ind += ext_caps_size

    return TermInfo(names, res['flags'], res['numbers'], res['strings'],
                    res['extended_flags'], res['extended_numbers'],
                    res['extended_strings'])
