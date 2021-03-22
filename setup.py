import pathlib

from setuptools import find_packages, setup

BASE_DIR = pathlib.Path(__file__).resolve().parent
exec((BASE_DIR / "pysen/_version.py").read_text())


setup(
    name="pysen",
    version=__version__,  # type: ignore[name-defined]  # NOQA: F821
    packages=find_packages(),
    description=(
        "Python linting made easy. "
        "Also a casual yet honorific way to address individuals "
        "who have entered an organization prior to you."
    ),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Yuki Igarashi, Toru Ogawa, Ryo Miyajima",
    author_email="igarashi@preferred.jp, ogawa@preferred.jp, ryo@preferred.jp",
    url="https://github.com/pfnet/pysen",
    license="MIT License",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
    ],
    install_requires=[
        "GitPython>=3.0.0,<4.0.0",
        "colorlog>=4.0.0,<5.0.0",
        "dacite>=1.1.0,<2.0.0",
        "dataclasses>=0.6,<1.0;python_version<'3.7'",
        "tomlkit>=0.5.11,<1.0.0",
        "unidiff>=0.6.0,<1.0.0",
    ],
    extras_require={
        "lint": [
            "black>=19.10b0,<=20.8",
            "flake8-bugbear",  # flake8 doesn't have a dependency for bugbear plugin
            "flake8>=3.7,<4",
            "isort>=4.3,<5.2.0",
            "mypy>=0.770,<0.800",
        ],
    },
    package_data={"pysen": ["py.typed"]},
    entry_points={"console_scripts": ["pysen=pysen.cli:cli"]},
)
