from distutils.core import setup
from setuptools import setup, Extension, find_packages

setup(
  name = 'xbow',
  packages = find_packages(), # this must be the same as the name above
  version = '0.1',
  description = 'A simple way to launch a virtual machine in the cloud with AWS and run simulations',
  author = 'Christian Suess',
  author_email = 'christian.suess1@nottingham.ac.uk',
  url = 'https://github.com/ChrisSuess/Project-Xbow', # use the URL to the github repo
  download_url = 'https://github.com/ChrisSuess/Project-Xbow/archive/0.1.tar.gz', # I'll explain this in a second
  keywords = ['cloud', 'aws', 'simulations', 'spot'], # arbitrary keywords
  classifiers = ['Environment :: Console',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2.6',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.2',
                 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Topic :: Scientific/Engineering',
                 'Topic :: Scientific/Engineering :: Bio-Informatics',
                 'Topic :: Scientific/Engineering :: Chemistry',
                 'Topic :: System :: Distributed Computing',
                 'Topic :: Utilities',
                 'Topic :: Software Development :: Libraries',
                 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: POSIX :: Linux',
	         'Operating System :: Unix'
		],
  license = 'MIT',
)
