from distutils.core import setup
setup(
  name = 'xbow',
  packages = ['xbow'], # this must be the same as the name above
  version = '0.1',
  description = 'A simple way to launch a virtual machine in the cloud with AWS and run simulations',
  author = 'Christian Suess',
  author_email = 'christian.suess1@nottingham.ac.uk',
  url = 'https://github.com/ChrisSuess/Project-Xbow', # use the URL to the github repo
  download_url = 'https://github.com/ChrisSuess/Project-Xbow/archive/0.1.tar.gz', # I'll explain this in a second
  keywords = ['cloud', 'aws', 'simulations', 'spot'], # arbitrary keywords
  classifiers = [],
)
