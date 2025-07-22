from setuptools import find_packages, setup

setup(
    name="kgents-shared",
    version="0.1.0",
    description="Shared models, schemas, and utilities for the Kgents platform",
    author="Kgents Team",
    author_email="team@kgents.com",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.5.0,<3.0.0",
        "sqlalchemy>=2.0.31,<3.0.0",
    ],
)
