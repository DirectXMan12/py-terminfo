#!/usr/bin/env python
from setuptools import setup

setup(
    name='terminfo',
    version='0.1.0',
    author='Solly Ross',
    author_email='directxman12+gh@gmail.com',
    packages=['terminfo'],
    description='A pure-Python compiled terminfo file parser',
    long_description=open('README.md').read(),
    LICENSE='LICENSE.txt',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    keywords=['ncurses', 'terminfo', 'termcap'],
    scripts=['py-terminfo-create-cache.py'],
)
