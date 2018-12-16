'''
Clients.py: thin wrapper over dask client
'''
from __future__ import print_function
import socket
import hashlib
import subprocess
import glob
import os
from dask.distributed import Client, LocalCluster
from .xflowlib import FunctionKernel, SubprocessKernel

def dask_client(scheduler_file=None, local=False, port=8786):
    """
    returns an instance of a dask.distributed client
    """
    if local:
        cluster = LocalCluster()
        client = Client(cluster)
    elif scheduler_file:
        client = Client(scheduler_file=scheduler_file)
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

class XflowClient(object):
    '''Thin wrapper around Dask client so functions that return multiple
       values (tuples) generate tuples of futures rather than single futures.
    '''
    def __init__(self, **kwargs):
        self.tmpdir = kwargs.pop('tmpdir', None)
        self.client = dask_client(**kwargs)

    def cluster(self):
        """
        Basic info about the cluster
        """
        return self.client.cluster

    def close(self):
        """
        The close() method of the underlying dask client
        """
        return self.client.close

    def upload(self, some_object):
        """
        Upload some data/object to the Xbow cluster.

        args:
            fsome_object (any type): what to upload

        returns:
            dask.Future
        """
        return self.client.scatter(some_object, broadcast=True)

    def unpack(self, kernel, future):
        """
        Unpacks the single future returned by kernel when run through
        a dask submit() or map() method, returning a tuple of futures.

        The outputs attribute of kernel lists how many values kernel
        should properly return.

        args:
            kernel (Kernel): the kernel that generated the future
            future (Future): the future returned by kernel

        returns:
            future or tuple of futures.
        """
        if len(kernel.outputs) == 1:
            return future
        outputs = []
        for i in range(len(kernel.outputs)):
            outputs.append(self.client.submit(lambda tup, j: tup[j], future, i))
        return tuple(outputs)

    def submit(self, func, *args):
        """
        Wrapper round the dask submit() method, so that a tuple of
        futures, rather than just one future, is returned.

        args:
            func (function/kernel): the function to be run
            args (list): the function arguments
        returns:
            future or tuple of futures
        """
        if isinstance(func, SubprocessKernel):
            func.tmpdir = self.tmpdir
            future = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, future)
        if isinstance(func, FunctionKernel):
            func.tmpdir = self.tmpdir
            future = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, future)
        else:
            return self.client.submit(func, *args)

    def _lt2tl(self, l):
        '''converts a list of tuples to a tuple of lists'''
        result = []
        for i in range(len(l[0])):
            result.append([t[i] for t in l])
        return tuple(result)

    def map(self, func, *iterables):
        """
        Wrapper arounf the dask map() method so it returns lists of
        tuples of futures, rather than lists of futures.

        args:
            func (function): the function to be mapped
            iterables (iterables): the function arguments

        returns:
            list or tuple of lists: futures returned by the mapped function
        """
        its = []
        maxlen = 0
        for iterable in iterables:
            if isinstance(iterable, list):
                l = len(iterable)
                if l > maxlen:
                    maxlen = l
        for iterable in iterables:
            if isinstance(iterable, list):
                l = len(iterable)
                if l != maxlen:
                    raise ValueError('Error: not all iterables are same length')
                its.append(iterable)
            else:
                its.append([iterable] * maxlen)
        if isinstance(func, SubprocessKernel):
            func.tmpdir = self.tmpdir
            futures = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, future) for future in futures]
        elif isinstance(func, FunctionKernel):
            func.tmpdir = self.tmpdir
            futures = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, future) for future in futures]
        else:
            result =  self.client.map(func, *its, pure=False)
        if isinstance(result[0], tuple):
            result = self._lt2tl(result)
        return result

    def execall(self, cmd):
        '''
        Run a command on all workers in a cluster.
        '''
        full_cmd = 'cd {}; {}'.format(os.getcwd(), cmd)
        def myfunc(cmd):
            try:
                r = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
                returncode = 0
            except subprocess.CalledProcessError as e:
                r = e.output
                returncode = e.returncode
            return {'returncode': returncode, 'output': r}
        result = self.client.run(myfunc, full_cmd)
        return result

    def install(self, package, sudo=False):
        '''
        Install a package on all workers in a cluster.
        '''
        if sudo:
            cmd = 'sudo pip install {}'.format(package)
        else:
            cmd = 'pip install {}'.format(package)

        result = self.execall(cmd)
        errors = False
        errortext = ''
        for key in result.keys():
            if result[key]['returncode'] != 0:
                errortext += 'Warning: install failed for worker {}\n'.format(key)
                errortext += result[key]['output'].decode('utf-8')
                errors = True
        if errors:
            raise RuntimeError(errortext)

def md5checksum(filename):
    """
    Returns the md5 checksum of a file
    """
    return hashlib.md5(open(filename, 'rb').read()).hexdigest()

def unpack_run_and_pack(cmd, filepack, tmpdir=None):
    '''
    Unpack some data files, run a command, return the results.
    '''
    with tempfile.TemporaryDirectory(dir=tmpdir) as tmpd:
        os.chdir(tmpd)
        filepack.unpack()
        m5s = {}
        for filename in filepack.filepack:
            m5s[filename] = md5checksum(filename)

        try:
            result = subprocess.check_output(cmd, shell=True,
                                             stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            result = e.output
        with open('STDOUT', 'wb') as f:
            f.write(result)
        filelist = glob.glob('*')
        outfiles = []
        for filename in filelist:
            if not filename in filepack.filepack:
                outfiles.append(filename)
            elif md5checksum(filename) != m5s[filename]:
                outfiles.append(filename)
        outfilepack = Filepack(outfiles)
    return outfilepack

def remote_run(client, cmd, tmpdir=None):
    '''
    Run a command on a client, including file staging
    '''
    files = [f for f in glob.glob('*') if os.path.isfile(f)]
    filepack = client.scatter(Filepack(files))
    result = client.submit(unpack_run_and_pack, cmd, filepack, tmpdir)
    result.result().unpack()
