"""Setup configuration for the main open-finops package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="open-finops",
    version="0.3.0",
    description="FOCUS-first open source FinOps platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Open FinOps Community",
    url="https://github.com/JGrubb/open-finops-stack",
    packages=[],  # Meta-package with no code
    install_requires=[
        # Default installation includes everything for best UX
        "open-finops-core>=0.3.0",
        "open-finops-aws>=0.3.0", 
        "open-finops-docker>=0.3.0",
    ],
    extras_require={
        # Specific vendors for specialized use cases
        'aws': ['open-finops-core>=0.3.0', 'open-finops-aws>=0.3.0'],
        'docker': ['open-finops-core>=0.3.0', 'open-finops-docker>=0.3.0'],
        
        # Advanced options
        'core': ['open-finops-core>=0.3.0'],  # Core only for developers
        'all': [                              # Explicit everything (same as default)
            'open-finops-core>=0.3.0',
            'open-finops-aws>=0.3.0',
            'open-finops-docker>=0.3.0',
        ],
    },
    # Entry point provided by open-finops-core package
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: Office/Business :: Financial",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="finops cloud costs aws azure gcp billing focus",
)