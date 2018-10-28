'''
Xflowlib: the Xflow library to build workflows on an Xbow cluster
'''
import re
import subprocess
import os
import tempfile
import shutil
import copy
import hashlib
import glob
from path import Path
from .clients import dask_client
from .filehandling import SharedFileHandle, CompressedFileHandle, TempFileHandle

filehandler = SharedFileHandle
filehandler_type = 'shared'

def set_filehandler(fh_type):
    """
    Set the type of file handler that will be used to pass file data between
    kernels.

    Currently three options are available. 

    The most basic ('tmp') uses the
    temporary file system on the host for sharing files. Obviously this only
    works if all workers reside on the same host.

    The second option is 'shared' which uses some shared (e.g. NFS) file
    system to pass files between worker nodes. This requires each node to
    have an environment variable SHARED which points to the mount point of
    the shared file system on that node.

    The third option is 'memory' which doesn't use a file system at all, 
    file data is stored in memory and passed to workers the same way as 
    all other data objects.

    args:
        fh_type (str): one of 'tmp', 'shared', or 'memory'
    """
    global filehandler_type
    global filehandler
    fh_types = ['tmp', 'shared', 'memory']
    fh_list = [TempFileHandle, SharedFileHandle, CompressedFileHandle]
    if not fh_type in fh_types:
        raise ValueError('Error - argument must be one of "tmp", "shared". '
                         'or "memory"')
    filehandler_type = fh_type
    filehandler = fh_list[fh_types.index(fh_type)]

def load(filename):
    '''
    Returns a FileHandle for a path
    '''
    return filehandler(filename)

class Filepack(object):
    """
    A collection of files
    """
    def __init__(self, filelist):
        self.filepack = {}
        for filename in filelist:
            self.filepack[filename] = filehandler(filename)

    def unpack(self, outputdir='.'):
        '''
        Unpack the files in the Filepack into the given directory.
        '''
        for filename in self.filepack:
            outname = os.path.join(outputdir, filename)
            self.filepack[filename].save(outname)

class SubprocessKernel(object):
    '''
    A kernel that runs a command-line executable
    '''
    def __init__(self, template):
        """
        Arguments:
            template (str): a template for the command to be executed
        """
        self.inputs = []
        self.outputs = []
        self.constants = {}
        self.tmpdir = None
        self.STDOUT = None

        self.var_dict = {}
        for key in re.findall(r'\{.*?\}', template):
            k = key[1:-1].replace('.', '_')
            self.var_dict[k] = key[1:-1]

        templist = []
        for i in template.split('{'):
            if '}' in i:
                templist.append(i.replace('.', '_'))
            else:
                templist.append(i)
        self.template = '{'.join(templist)

    def set_inputs(self, inputs):
        """
        Set the inputs the kernel requires
        """
        if not isinstance(inputs, list):
            raise TypeError('Error - inputs must be of type list,'
                    ' not of type {}'.format(type(inputs)))
        self.inputs = []
        for i in inputs:
            i2 = i.replace('.', '_')
            if not i2 in self.var_dict:
                 self.var_dict[i2] = i
            #    raise ValueError('Error - no input parameter "{}" in'
            #            ' the command template'.format(i))
            self.inputs.append(i)

    def set_outputs(self, outputs):
        """
        Set the outputs the kernel produces
        """
        if not isinstance(outputs, list):
            raise TypeError('Error - outputs must be of type list,'
                    ' not of type {}'.format(type(outputs)))
        self.outputs = []
        for i in outputs:
            i2 = i.replace('.', '_')
            if not i2 in self.var_dict:
                raise ValueError('Error - no output parameter "{}" in'
                        ' the command template'.format(i))
            self.outputs.append(i)

    def set_constant(self, key, value):
        """
        Set a constant for the kernel
        If it was previously defined as an input variable, remove it from
        that list.
        """
        k = key.replace('.', '_')
        if not k in self.var_dict:
             self.var_dict[k] = key
        #    raise ValueError('Error - no constant "{}" in the command'
        #            ' template'.format(key))
        self.constants[k] = value
        if isinstance(value, str):
            if os.path.exists(value):
                self.constants[k] = filehandler(value)
        if key in self.inputs:
            self.inputs.remove(key)

    def copy(self):
        '''
        Return a copy of the kernel
        '''
        return copy.deepcopy(self)

    def run(self, *args):
        """
        Run the kernel with the given inputs.
        Args:
            args: positional arguments whose order should match self.inputs

        Returns:
            tuple : outputs in the order they appear in
                self.outputs
        """
        outputs = []
        #td = tempfile.TemporaryDirectory(dir=self.tmpdir)
        #with Path(td.name) as tmpdir:
        td = tempfile.mkdtemp(dir=self.tmpdir)
        with Path(td) as tmpdir:
            var_dict = self.var_dict
            for i in range(len(args)):
                try:
                    args[i].save(self.inputs[i])
                except AttributeError:
                    var_dict[self.inputs[i]] = args[i]
            for key in self.constants:
                try:
                    self.constants[key].save(self.var_dict[key])
                except AttributeError:
                    var_dict[key] = self.constants[key]
            try:
                cmd = self.template.format(**var_dict)
                result = subprocess.check_output(cmd, shell=True,
                                                 stderr=subprocess.STDOUT)
                self.STDOUT = result.decode()
            except subprocess.CalledProcessError as e:
                print(e.output)
                raise
            for outfile in self.outputs:
                if os.path.exists(outfile):
                    outputs.append(filehandler(outfile))
                else:
                    outputs.append(None)
        shutil.rmtree(td)
        if len(outputs) == 1:
            outputs = outputs[0]
        else:
            outputs = tuple(outputs)
        return outputs
     
class FunctionKernel(object):
    def __init__(self, func):
        """
        Arguments:
            func: the Python function to wrap
            filetype (FileHandle): the file-type handler
        """
        self.func = func
        self.inputs = []
        self.outputs = []
        self.constants = {}
        self.tmpdir = None

    def set_inputs(self, inputs):
        """
        Set the inputs the kernel requires
        """
        self.inputs = inputs

    def set_outputs(self, outputs):
        """
        Set the outputs the kernel produces
        """
        self.outputs = outputs

    def set_constant(self, key, value):
        """
        Set a parameters for the kernel
        """
        self.constants[key] = value
        if isinstance(value, str):
            if os.path.exists(value):
                self.constants[key] = filehandler(value)

    def copy(self):
        """
        Return a copy of the kernel
        """
        return copy.copy(self)

    def run(self, *args):
        """
        Run the kernel/function with the given arguments.

        Returns:
            Whatever the function returns, with output files converted
                to FileHandle objects
        """
        td = tempfile.TemporaryDirectory(dir=self.tmpdir)
        with Path(td.name) as tmpdir:
            indict = {}
            for i, v in enumerate(args):
                if isinstance(v, FileHandle):
                    indict[self.inputs[i]] = v.save(os.path.basename(v.path))
                elif isinstance(v, dict):
                    for k in v:
                        if k in self.inputs:
                            if isinstance(v[k], FileHandle):
                                indict[k] = v[k].save(os.path.basename(v[k].path))
                            else:
                                indict[k] = v[k]
                else:
                    indict[self.inputs[i]] = v
            for k in self.constants:
                if isinstance(self.constants[k], FileHandle):
                    indict[k] = self.constants[k].save(os.path.basename(self.constants[k].path))
                else:
                    indict[k] = self.constants[k]
            result = self.func(**indict)
            if not isinstance(result, list):
                result = [result]
            outputs = []
            for i, v in enumerate(result):
                if isinstance(v, str):
                    if os.path.exists(v):
                        outputs.append(filehandler(v))
                    else:
                        outputs.append(v)
                else:
                    outputs.append(v)
        if len(outputs) == 1:
            outputs = outputs[0]
        else:
            outputs = tuple(outputs)
        return outputs

class XflowClient(object):
    '''Thin wrapper around Dask client so functions that return multiple
       values (tuples) generate tuples of futures rather than single futures.
    '''
    def __init__(self, **kwargs):
        self.tmpdir = kwargs.pop('tmpdir', None)
        self.client = dask_client(**kwargs)

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
