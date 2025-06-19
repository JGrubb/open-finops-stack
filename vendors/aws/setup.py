"""Setup configuration for open-finops-aws package."""

from setuptools import setup, find_packages

setup(
    name="open-finops-aws",
    version="0.3.0", 
    description="AWS vendor plugin for Open FinOps Stack",
    long_description="AWS Cost and Usage Report (CUR) integration for the Open FinOps Stack, supporting both CUR v1 and v2 formats with state tracking and multi-export capabilities.",
    author="Open FinOps Community",
    packages=find_packages(),
    install_requires=[
        "open-finops-core>=0.3.0",
        "boto3>=1.26.0",
        "botocore>=1.29.0",
    ],
    entry_points={
        'open_finops.vendors': [
            'aws = vendors.aws.cli:AWSCommands',
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