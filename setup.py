"""SSH Connector package setup."""

from setuptools import setup, find_packages

setup(
    name="ssh-connector",
    version="0.1.0",
    description="Cross-platform reverse SSH client with GUI",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "paramiko>=3.4.0",
        "PyQt6>=6.6.0",
        "keyring>=24.0.0",
    ],
    extras_require={
        "dev": [
            "pyinstaller>=6.0.0",
            "pytest>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ssh-connector=main:main",
        ],
        "gui_scripts": [
            "ssh-connector-gui=main:main",
        ],
    },
)
