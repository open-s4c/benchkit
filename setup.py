#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name="benchkit",
      packages=find_packages(
            include = ["benchkit*", "plotbench*"]
      ),
)
