#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='bcf',
    packages=["bcf", "bcf.flasher", "bcf.flasher.serialport", "bcf.log", "bcf.repos", "bcf.firmware"],
    version='@@VERSION@@',
    description='BigClown Firmware Tool.',
    author='HARDWARIO s.r.o.',
    author_email='karel.blavka@bigclown.com',
    url='https://github.com/bigclownlabs/bch-firmware-tool',
    include_package_data=True,
    install_requires=[
        'appdirs>=1.4', 
        'pyserial>=3.0', 
        'colorama>=0.3', 
        'PyYAML>=3.11', 
        'schema>=0.6.7', 
        'requests>=2.18', 
        'Click>=6.0', 
        'intelhex>=2.2.1'
    ],
    license='MIT',
    zip_safe=False,
    keywords=['BigClown', 'bcf', 'firmware', 'flasher'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'Environment :: Console'
    ],
    entry_points='''
        [console_scripts]
        bcf=bcf.cli:main
    ''',
    long_description='''
BigClown Firmware Tool.
'''
)
