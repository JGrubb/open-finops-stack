"""Setup configuration for open-finops-docker package."""

from setuptools import setup, find_packages

setup(
    name="open-finops-docker",
    version="0.3.0",
    description="Docker configurations for Open FinOps Stack", 
    long_description="Docker and container configurations for deploying the Open FinOps Stack, including Metabase integration and DuckDB support.",
    author="Open FinOps Community",
    packages=find_packages(),
    install_requires=[
        "open-finops-core>=0.3.0",
    ],
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