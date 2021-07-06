#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import sys

from setuptools import find_packages, setup

author = "Dave Vandenbout"
email = "info@xess.com"
version = "0.0.10"

if "sdist" in sys.argv[1:]:
    with open("myhdlpeek/pckg_info.py", "w") as f:
        for name in ["version", "author", "email"]:
            f.write("{} = '{}'\n".format(name, locals()[name]))

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read().replace(".. :changelog:", "")

requirements = [
    # Put package requirements here
    "future >= 0.15.0",
    "myhdl",
    "nmigen",
    "tabulate",
    "pandas",
    "nbwavedrom",
]

test_requirements = [
    # Put package test requirements here
    "pytest",
]

setup(
    name="myhdlpeek",
    version=version,
    description="Peek at signals in a MyHDL or nMigen digital system simulation.",
    long_description=readme + "\n\n" + history,
    author=author,
    author_email=email,
    url="https://github.com/devbisme/myhdlpeek",
    #    packages=['myhdlpeek',],
    packages=find_packages(exclude=["tests"]),
    entry_points={"console_scripts": ["myhdlpeek = myhdlpeek.__main__:main"]},
    package_dir={"myhdlpeek": "myhdlpeek"},
    include_package_data=True,
    package_data={"myhdlpeek": ["*.gif", "*.png"]},
    scripts=[],
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords="myhdlpeek",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
    ],
    test_suite="tests",
    tests_require=test_requirements,
)
