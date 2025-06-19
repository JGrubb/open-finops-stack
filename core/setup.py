"""Setup configuration for open-finops-core package."""

from setuptools import setup, find_packages

setup(
    name="open-finops-core",
    version="0.3.0",
    description="Core framework for Open FinOps Stack",
    long_description="Core framework providing configuration, state tracking, and CLI infrastructure for the Open FinOps Stack.",
    author="Open FinOps Community",
    packages=find_packages(),
    install_requires=[
        "dlt>=0.4.0",
        "duckdb>=0.9.0", 
        "toml>=0.10.0",
        "boto3>=1.26.0",
    ],
    entry_points={
        'console_scripts': [
            'finops=core.cli.main:main',
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)