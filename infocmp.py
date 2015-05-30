from __future__ import print_function

import sys
import os
import argparse

from terminfo import core
from terminfo import cap_info


def escape_str(input_str):
    input_str = input_str.replace('\x1b', r'\E')
    input_str = input_str.replace('\0', r'\0')
    input_str = input_str.replace('\x7f', r'\x7f')

    for i in range(1, 32):
        input_str = input_str.replace(chr(i), '^%s' % chr(i + 64))

    return input_str


def wrap(input_items):
    MAX_LEN = 60
    line = '\t'
    res = []
    for i in input_items:
        if len(line) + len(i) + 2 < MAX_LEN:
            line += i + ', '
        else:
            if not line.isspace():
                res.append(line.rstrip())
            line = '\t' + i + ', '

    res.append(line.rstrip())
    return '\n'.join(res)


arg_parser = argparse.ArgumentParser(
    description="Display binary terminfo files (similarly to infocmp from "
                "ncurses).",
    epilog="In order to generate a cache file, you must specify a source "
           "capabilities file.  These files are found in the ncurses source "
           "under 'include/Caps' and 'include/Caps.*'.  If you specify a "
           "capabilities file without specifiying a terminfo file, a cache "
           "will be generated, and the utility will then exit."
)

arg_parser.add_argument('file', metavar='TERMINFO_FILE', default=None,
                        nargs='?', help='The binary terminfo file from which '
                                        ' to load the information.')
arg_parser.add_argument('-x', dest='show_extended',
                        help='Print extended capabilities, similarly to the '
                             ' -x flag in infocmp from ncurses.')
arg_parser.add_argument('--cache-file', metavar='CACHE_FILE',
                        default=os.path.expanduser('~/.py-terminfo-caps-file'),
                        help='The cache file to use to store the capability '
                             'names and helps (defaults to '
                             '~/.py-terminfo-caps-file)')
arg_parser.add_argument('--caps-file', metavar='CAPS_FILE', default=None,
                        help='A file containing a capabilities table, '
                             '(only needed if no cache file is present')
args = arg_parser.parse_args()

if args.file is None and args.caps_file is None:
    sys.exit("You must at least specify either a capabilities file "
             "or a terminfo file.")

cap_info.load_cap_info(args.caps_file, args.cache_file)

if args.file is None:
    sys.exit()

with open(args.file, 'rb') as f:
    contents = f.read()
    info = core.parse_terminfo(contents)

    named_flags = {}
    for ind, val in enumerate(info.flags):
        named_flags[cap_info.CAP_NAMES['flags'][ind]] = val

    named_flags = sorted(named_flags.items(), key=lambda i: i[0])
    if args.show_extended:
        named_flags.extend(sorted((info.extended_flags or {}).items(),
                           key=lambda i: i[0]))

    named_numbers = {}
    for ind, val in enumerate(info.numbers):
        named_numbers[cap_info.CAP_NAMES['numbers'][ind]] = val

    named_numbers = sorted(named_numbers.items(), key=lambda i: i[0])
    if args.show_extended:
        named_numbers.extend(sorted((info.extended_numbers or {}).items(),
                             key=lambda i: i[0]))

    named_strings = {}
    for ind, val in enumerate(info.strings):
        named_strings[cap_info.CAP_NAMES['strings'][ind]] = val

    named_strings = sorted(named_strings.items(), key=lambda i: i[0])
    if args.show_extended:
        named_strings.extend(sorted((info.extended_strings or {}).items(),
                             key=lambda i: i[0]))

    print('|'.join(info.names).rstrip() + ',')
    print(wrap(name for name, val in named_flags if val))
    print(wrap('%s#%s' % (name, val)
               for name, val in named_numbers if val is not None))
    print(wrap('%s=%s' % (name, escape_str(val))
               for name, val in named_strings if val is not None))
