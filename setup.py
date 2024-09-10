from setuptools import setup, find_packages

setup(
    name="benchkit",
    description="A push-button end-to-end performance evaluation pipeline for automatically exploring the parameter space",
    version="1.0.0",
    url="https://github.com/open-s4c/benchkit",
    author="Antonio Paolillo",
    packages=find_packages(include=["benchkit", "benchkit.*"]),
)