from setuptools import setup, find_packages

setup(
    name="open-finops",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["boto3", "clickhouse-connect", "platformshconfig", "dateparser"],
)
