#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', 'r') as f:
    requirements = f.read()

setup(
    name='bcf',
    packages=find_packages(),
    version='@@VERSION@@',
    description='BigClown Firmware Tool.',
    author='HARDWARIO s.r.o.',
    author_email='karel.blavka@bigclown.com',
    url='https://github.com/bigclownlabs/bch-firmware-tool',
    include_package_data=True,
    install_requires=requirements,
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
    long_description=long_description,
    long_description_content_type='text/markdown'
)
