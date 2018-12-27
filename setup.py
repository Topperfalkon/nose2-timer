#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

with open('nose2_timer/__init__.py') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)

setup(
    name='nose2-timer',
    version=version,
    description='A timer plugin for nose2',
    long_description=long_description,
    author=', '.join([
        'Alister Cordiner',
        'Andres Riancho',
        'Anton Egorov',
        'Arthur Kulik',
        'Corey Goldberg',
        'Dmitry Sandalov',
        'Harald Nordgren',
        'Ivan Kolodyazhny',
        'Juan Pedro Fisanotti',
        'Kevin Burke',
        'Mahmoud Abdelkader',
        'Raoul Snyman',
        'Stanislav Kudriashev',
    ]),
    url='https://github.com/Topperfalkon/nose2-timer',
    packages=['nose2_timer', ],
    install_requires=[
        'nose2',
    ],
    license='MIT',
    entry_points={
        'nose.plugins.0.10': [
            'nose2_timer = nose2_timer.plugin:TimerPlugin',
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
        'Environment :: Console',
    ],
)
