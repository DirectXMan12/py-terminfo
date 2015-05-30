Py-Terminfo
===========

Py-Terminfo is a pure-python parser for compiled terminfo files.  Unlike other
libraries, it has no binary dependecies on ncurses.  However, it has a one-time
dependency on an ncurses capabilities table, such as those found in the ncurses
source.

Requirements
------------

* Python 2.7 or Python 3.3+
* Access to a capabilities table or a py-terminfo cache file (see below)

Capabilities Table
------------------

Due to the nature of the compiled terminfo format (see the `term(5)` manpage),
py-terminfo needs access to an ordered list of capability names to associate
with raw capability values.  A utility is included
(`py-terminfo-create-cache.py`)  that reads the capabilities file an creates
a cached form suitable for use by py-terminfo (instead of keeping the capabilities
file around)

Usage
-----

First, you'll have to load capabilities information.  This information is used
by py-terminfo to associate capabilities data with the corresponding capability
name.

```python
>>> from terminfo import TermInfo, load_cap_info
>>> cap_info = load_cap_info(cache_file='./.caps-cache')
>>> cap_info
<Capabilites Table: flags#44, numbers#39, strings#414, aliases#49>
>>>
```

You can also use the returned object to get information about different terminal
capabilities:

```python
>>> cap_info.flags
<Capabilities Sub-Table(flags): 44 entries>
>>> cap_info.find('ccc')
Capability(number=27, name='ccc', variable_name='can_change', type='flags', old_cap_name='cc', key_name=None, key_value=None, versions='-----', description='terminal can re-define existing colors')
>>> cap_info.numbers[0]
Capability(number=0, name='cols', variable_name='columns', type='numbers', old_cap_name='co', key_name=None, key_value=None, versions='YBCGE', description='number of columns in a line')
>>> cap_info.strings.by_variable_name('initialize_color')
Capability(number=299, name='initc', variable_name='initialize_color', type='strings', old_cap_name='Ic', key_name=None, key_value=None, versions='-----', description='initialize color #1 to (#2,#3,#4)')
>>>
```

After you've loaded the capabilities information, you can load a terminfo file and inspect
it for capabilities:

```python
>>> with open('/usr/share/terminfo/x/xterm', 'rb') as f:
...     info = TermInfo(f.read(), cap_info)
...
>>> info
<TermInfo(xterm): flags#10, numbers#5, strings#221, ext=True>
>>> info.names
[u'xterm', u'xterm terminal emulator (X Window System)']
>>>
```

You can access the different capabilities:

```python
>>> info.flags
<Capabilites(flags) [am, xenl, km, mir, msgr, mc5i, npc, bce, OTbs]>
>>> info.numbers
<Capabilites(numbers) {cols: 80, it: 8, lines: 24, colors: 8, pairs: 64}>
>>> info.strings['bel']
'\x07'
>>> info.numbers['columns']
80
>>> 'ccc' in info.flags
False
>>>
```

You can also access the data from the ncurses extended terminfo:

```python
>>> info.has_extended_capabilities
True
>>> info.extended_flags
<Extended Capabilites(flags) [AX]>
>>>
```

If you don't want py-terminfo to try and parse extended capabilities,
pass `parse_extended=False` to the `TermInfo` constructor.


Examples
--------

The `print-terminfo.py` utility functions similarly to the the `infocmp` utility
included with ncurses.  It demonstrates how to load capabilities information and
parse terminfo files, extracting capabilities.
