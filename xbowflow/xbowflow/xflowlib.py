'''
Xflowlib: the Xflow library to build workflows on an Xbow cluster
'''
import re
import subprocess
import os
import tempfile
from shutil import copyfile
import copy
import hashlib
import glob
from path import Path
from .clients import dask_client
from .filehandling import TempFileHandle

def load(filename, filetype=TempFileHandle):
    '''
    Returns a FileHandle for a path
    '''
    return filetype(filename)

class Filepack(object):
    """
    A collection of files
    """
    def __init__(self, filelist, filetype=TempFileHandle):
        self.filepack = {}
        for filename in filelist:
            self.filepack[filename] = filetype(filename)

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
    def __init__(self, template, filetype=TempFileHandle):
        """
        Arguments:
            template (str): a template for the command to be executed
            filetype (FileHandle): the class used for file-type data
        """
        self.inputs = []
        self.outputs = []
        self.constants = {}
        self.filetype = filetype
        self.tmpdir = None
        self.STDOUT = None

        self.var_dict = {}
        for key in re.findall('\{.*?\}', template):
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
            raise TypeError('Error - inputs must be of type list, not of type {}'.format(type(inputs)))
        self.inputs = []
        for i in inputs:
            i2 = i.replace('.', '_')
            if not i2 in self.var_dict:
                raise ValueError('Error - no input parameter "{}" in the command template'.format(i))
            self.inputs.append(i)

    def set_outputs(self, outputs):
        """
        Set the outputs the kernel produces
        """
        if not isinstance(outputs, list):
            raise TypeError('Error - outputs must be of type list, not of type {}'.format(type(outputs)))
        self.outputs = []
        for i in outputs:
            i2 = i.replace('.', '_')
            if not i2 in self.var_dict:
                raise ValueError('Error - no output parameter "{}" in the command template'.format(i))
            self.outputs.append(i)

    def set_constant(self, key, value):
        """
        Set a constant for the kernel
        If it was previously defined as an input variable, remove it from
        that list.
        """
        k = key.replace('.', '_')
        if not k in self.var_dict:
            raise ValueError('Error - no constant "{}" in the command template'.format(key))
        self.constants[k] = value
        if isinstance(value, str):
            if os.path.exists(value):
                self.constants[k] = self.filetype(value)
        if key in self.inputs:
            self.inputs.remove(key)

    def copy(self):
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
        td = tempfile.TemporaryDirectory(dir=self.tmpdir)
        with Path(td.name) as tmpdir:
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
                    outputs.append(self.filetype(outfile))
                else:
                    outputs.append(None)
        if len(outputs) == 1:
            outputs = outputs[0]
        else:
            outputs = tuple(outputs)
        return outputs
            
class FunctionKernel(object):
    def __init__(self, func, filetype=TempFileHandle):
        """
        Arguments:
            func: the Python function to wrap
            filetype (FileHandle): the file-type handler
        """
        self.func = func
        self.inputs = []
        self.outputs = []
        self.constants = {}
        self.filetype = filetype
        self.tmpdir=None

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
                self.constants[key] = self.filetype(value)

    def copy(self):
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
                        outputs.append(self.filetype(v))
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

    def upload(self, f):
        c = f
        if isinstance(f, str):
            if os.path.exists(f):
                c = SharedFile(f)
        return self.client.scatter(c, broadcast=True)

    def unpack(self, f, t):
        if len(f.outputs) == 1:
            return t
        outputs = []
        for i in range(len(f.outputs)):
            outputs.append(self.client.submit(lambda tup, j: tup[j], t, i))
        return tuple(outputs)

    def submit(self, func, *args):
        if isinstance(func, SubprocessKernel):
            func.tmpdir = self.tmpdir
            t = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, t)
        elif isinstance(func, FunctionKernel):
            func.tmpdir = self.tmpdir
            t = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, t)
        else:
            return self.client.submit(func, *args)

    def _lt2tl(self, l):
        '''converts a list of tuples to a tuple of lists'''
        result = []
        for i in range(len(l[0])):
            result.append([t[i] for t in l])
        return tuple(result)

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
            func.tmpdir = self.tmpdir
            l = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, t) for t in l]
        elif isinstance(func, FunctionKernel):
            func.tmpdir = self.tmpdir
            l = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, t) for t in l]
        else:
            result =  self.client.map(func, *its, pure=False)
        if isinstance(result[0], tuple):
            result = self._lt2tl(result)
        return result

def md5checksum(filename):
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
