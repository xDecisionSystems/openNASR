import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "openNASR",
    version = "0.0.1",
    author = "Adan E Vela",
    author_email = "adan.vela@ucf.edu",
    description = ("Library to access FAA NASR data"),
    license = "GNU GENERAL PUBLIC LICENSE Version 3",
    keywords = "FAA NASR",
    url = "https://github.com/ADCLab/openNASR",
    packages=['openNASR'],
    install_requires=['matplotlib','shapely','numpy','pandas'], #external packages as dependencies
    dependency_links=['https://pypi.adc-ucf.com/simple/'], # Added just in case.  Probably should be removed
    long_description=read('README.md'),
)