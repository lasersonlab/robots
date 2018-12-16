from setuptools import setup

def readme():
    with open("README.md", "r") as ip:
        return ip.read()

setup(
    name="hardy",
    version="0.0.0",
    description="hardy opentrons OT-2 protocols",
    long_description=readme(),
    url="https://github.com/lasersonlab/robots/hardy",
    author="Laserson Lab",
    classifiers=["Programming Language :: Python :: 3"],
    py_modules=["hardy"],
    install_requires=["click", "pandas", "plotly", "pyyaml", "sample_sheet"],
    entry_points={"console_scripts": ["hardy = hardy:cli"]},
)
