from __future__ import print_function
from dask.distributed import Client
import socket

def dask_client(local=False, port=8786):
    """
    returns an instance of a dask.distributed client
    """
    if local:
        return Client()
    ip = socket.gethostbyname(socket.gethostname())
    dask_scheduler = '{}:{}'.format(ip, port)
    try:
        client = Client(dask_scheduler, timeout=5)
    except IOError:
        print('Warning: using local dask client')
        client = Client()
    return client
