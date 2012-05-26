# setuptools import
from setuptools import setup, find_packages

import sys, os

def read(*names):
    values = dict()
    for name in names:
        filename = name+'.txt'
        if os.path.isfile(filename):
            value = open(name+'.txt').read()
        else:
            value = ''
        values[name] = value
    return values

long_description="""
%(README.md)s

See http://packages.python.org/eventsource/ for the full documentation

News
====

%(CHANGES)s

""" % read('README.md', 'CHANGES')

setup(name="eventsource",
      version="1.0",
      description="Event Source Library",
      long_description=long_description,
      author="Bernard Pratz",
      author_email="guyzmo@hackable-devices.org",
      install_requires = [
          'tornado'
      ],
      packages = find_packages(exclude=['examples', 'tests']),
      url='http://packages.python.org/eventsource/',
      include_package_data=True,
      zip_safe=False,
      license="GPLv3",
      classifiers = ["Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                     "Intended Audience :: Developers",
                     "License :: OSI Approved :: ",
                     "Operating System :: OS Independent",
                     "Programming Language :: Python",
                     "Topic :: Utilities"],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      eventsource-server = eventsource.listener:start
      eventsource-client = eventsource.client:start
      eventsource-request = eventsource.request:start
      """,
      )
