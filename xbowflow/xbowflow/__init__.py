from __future__ import print_function
from dask.distributed import Client
import socket

ip = socket.gethostbyname(socket.gethostname())
dask_scheduler = '{}:8786'.format(ip)
try:
    client = Client(dask_scheduler, timeout=2)
except IOError:
    print('Warning: using local dask client')
    client = Client()
