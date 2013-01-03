# setuptools import
from setuptools import setup, find_packages

import os

def read(*names):
    values = dict()
    for name in names:
        for ext in ['.txt','.md','.rst','']:
            filename = name+ext
            if os.path.isfile(filename):
                value = open(filename).read()
                break
        else:
            value = ''
        values[name] = value
    return values

long_description="""
%(README)s

See http://packages.python.org/eventsource/ for the full documentation
See https://github.com/guyzmo/event-source-library for latest sources and for patches

News
====

%(CHANGES)s

""" % read('README', 'CHANGES')

setup(name="eventsource",
      version="1.0.5",
      description="Event Source Library",
      long_description=long_description,
      author="Bernard Pratz",
      author_email="guyzmo@hackable-devices.org",
      install_requires = [
          'tornado',
          'pycurl'
      ],
      packages = find_packages(exclude=['examples', 'tests']),
      url='http://packages.python.org/eventsource/',
      include_package_data=True,
      zip_safe=False,
      license="GPLv3",
      classifiers = ["Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                     "Intended Audience :: Developers",
                     "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
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
