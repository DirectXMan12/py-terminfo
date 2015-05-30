#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import argparse

from terminfo import cap_info

arg_parser = argparse.ArgumentParser(
    description="Create a capabilities cache file for use with py-terminfo",
    epilog='Capabilities table files are included with the ncurses source'
           'code.  The default one is /path/to/ncurses-source/include/Caps, '
           'but ncurses includes ones for several alternate implementations '
           'as well.'
)

arg_parser.add_argument('caps_file', metavar='CAPS_FILE',
                        help='The file containing the capabilities table.')
arg_parser.add_argument('--cache-file', metavar='CACHE_FILE',
                        default=os.path.expanduser('~/.py-terminfo-caps-file'),
                        help='The cache file to use to store the capability '
                             'names and helps (defaults to '
                             '~/.py-terminfo-caps-file)')
args = arg_parser.parse_args()

cap_info = cap_info.load_cap_info(args.caps_file, args.cache_file)

print('Successfully generated a capabilities cache at %s.' % args.cache_file)
