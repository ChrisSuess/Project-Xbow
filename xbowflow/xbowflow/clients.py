'''
Clients.py: thin wrapper over dask client
'''
from __future__ import print_function
import socket
from dask.distributed import Client, LocalCluster

def dask_client(local=False, port=8786):
    """
    returns an instance of a dask.distributed client
    """
    if local:
        cluster = LocalCluster()
        client = Client(cluster)
    else:
        ip_address = socket.gethostbyname(socket.gethostname())
        dask_scheduler = '{}:{}'.format(ip_address, port)
        try:
            client = Client(dask_scheduler, timeout=5)
        except IOError:
            print('Warning: using local dask client')
            cluster = LocalCluster()
            client = Client(cluster)
    return client
