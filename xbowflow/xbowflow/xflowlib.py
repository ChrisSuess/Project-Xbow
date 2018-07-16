import zlib
import subprocess
import os
import tempfile
import copy
from .clients import dask_client

class CompressedFileContents(object):
    '''contains the contents of a file in compressed form'''
    def __init__(self, filename):
        self.name = os.path.basename(filename)
        self.data = zlib.compress(open(filename, 'rb').read())
    
    def write(self, filename=None, suffix=None):
        if suffix is not None:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(zlib.decompress(self.data))
            return f.name
        else:
            if filename is None:
                filename = self.name
            with open(filename, 'wb') as f:
                f.write(zlib.decompress(self.data))
            return filename

class SubprocessKernel(object):
    def __init__(self, cmd):
        """
        Arguments:
            cmd (str): the command to be executed
        """
        self.cmd = cmd
        self.inputs = []
        self.outputs = []
        self.constants = {}

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
                self.constants[key] = CompressedFileContents(value)

    def copy(self):
        return copy.copy(self)

    def run(self, *args, **kwargs):
        """
        Run the kernel with the given inputs.
        Args:
            args: positional arguments whose order should match self.inputs
            kwargs: keyword arguments 

        Returns:
            dict : the output dictionary, with at least
                two keys:
                    'STDOUT' : the standard output and error from the command
                    'returncode' : the exit code for the command
                 in addition there will be one value for each of the keys
                 in self.outputs
        """
        outputs = {}
        outputs['returncode'] = 0
        tmpdir = tempfile.mkdtemp()
        os.chdir(tmpdir)
        indict = {}
        for i in range(len(args)):
            if isinstance(args[i], dict):
                for key in args[i]:
                    indict[key] = args[i][key]
            else:
                indict[self.inputs[i]] = args[i]
        for key in kwargs:
            indict[key] = kwargs[key]
        for key in self.inputs:
            if not key in indict:
                raise KeyError('Error - missing argument {}'.format(key))
            else:
                if indict[key] is None:
                    print('Error: indict key {} is None'.format(key))
                indict[key].write(key)
        for key in self.constants:
            self.constants[key].write(key)
        try:
            result = subprocess.check_output(self.cmd, shell=True,
                                             stderr=subprocess.STDOUT)
            outputs['STDOUT'] = result
            for key in self.outputs:
                if os.path.exists(key):
                    outputs[key] = CompressedFileContents(key)
                else:
                    outputs[key] = None
        except subprocess.CalledProcessError as e:
            outputs['returncode'] = e.returncode
            outputs['STDOUT'] = e.output
            for key in self.outputs:
                outputs[key] = None
        for key in indict:
            outputs[key] = indict[key]
        return outputs
            
class FunctionKernel(object):
    def __init__(self, func):
        """
        Arguments:
            func: the Python function to wrap
        """
        self.func = func
        self.inputs = []
        self.outputs = []
        self.constants = {}

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
                self.constants[key] = CompressedFileContents(value)

    def copy(self):
        return copy.copy(self)

    def run(self, *args):
        """
        Run the kernel/function with the given arguments.

        Returns:
            a dictionary with one key for each of the items in outputs,
            plus keys 'returncode', and 'STDOUT' (for compatability with
            SubprocessKernel)
        """
        outputs = {}
        outputs['returncode'] = 0
        tmpdir = tempfile.mkdtemp()
        os.chdir(tmpdir)
        indict = {}
        for i, v in enumerate(args):
            if isinstance(v, CompressedFileContents):
                indict[self.inputs[i]] = v.write()
            else:
                indict[self.inputs[i]] = v
        for k in self.constants:
            if isinstance(self.constants[k], CompressedFileContents):
                indict[k] = self.constants[k].write()
            else:
                indict[k] = self.constants[k]
        result = self.func(**indict)
        if not isinstance(result, list):
            result = [result]
        for i, v in enumerate(result):
            outputs[self.outputs[i]] = v
            if isinstance(v, str):
                if os.path.exists(v):
                    outputs[self.outputs[i]] = CompressedFileContents(v)
        return outputs

class XflowClient(object):
    '''Thin wrapper around Dask client so functions return dictionaries
       of futures rather than single futures.
    '''
    def __init__(self):
        self.client = dask_client()

    def upload(self, f):
        c = f
        if isinstance(f, str):
            if os.path.exists(f):
                c = CompressedFileContents(f)
        return self.client.scatter(c, broadcast=True)

    def unpack(self, f, d):
        outdict = {}
        for key in ['returncode', 'STDOUT']:
            outdict[key] = self.client.submit(lambda d, key: d[key], d, key)
        for key in f.outputs:
            outdict[key] = self.client.submit(lambda d, key: d[key], d, key)
        return outdict

    def submit(self, func, *args):
        if isinstance(func, SubprocessKernel):
            d = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, d)
        elif isinstance(func, FunctionKernel):
            d = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, d)
        else:
            return self.client.submit(func, *args)

    def _ld2dl(self, l):
        '''converts a list of dicts to a dict of lists'''
        result = {}
        for k in l[0]:
            result[k] = [d[k] for d in l]
        return result

    def map(self, func, *iterables):
        its = []
        maxlen = 0
        for it in iterables:
            if isinstance(it, list):
                l = len(it)
                if l > maxlen:
                    maxlen = l
        for it in iterables:
            if isinstance(it, list):
                l = len(it)
                if l != maxlen:
                    raise ValueError('Error: not all iterables are same length')
                its.append(it)
            else:
                its.append([it] * maxlen)
        if isinstance(func, SubprocessKernel):
            l = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, d) for d in l]
        elif isinstance(func, FunctionKernel):
            l = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, d) for d in l]
        else:
            result =  self.client.map(func, *its, pure=False)
        if isinstance(result[0], dict):
            result = self._ld2dl(result)
        return result
