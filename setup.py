#!/usr/bin/env python

from setuptools import setup, find_packages
import widgets

setup(
    name="widgets",
    version=widgets.__version__,
    author="Steve Pike Kevin Mahoney",
    author_email="git@stevepike.co.uk git@kevinmahoney.co.uk",
    description="A framework for reusable mini-views",
    packages=find_packages(exclude=('test',)),
    include_package_data=True,
    install_requires=[
        "django>=1.2.4",
    ],
#    tests_require=['nose>=1.1.2','coverage>=3.5.1','mock>=0.7.2'],
)
