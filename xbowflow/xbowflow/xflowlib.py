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
import uuid
from path import Path
from .filehandling import SharedFileHandle, CompressedFileHandle, TempFileHandle

filehandler = None
filehandler_type = None
session_dir = str(uuid.uuid4())

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

def purge():
    '''
    Remove all temporary files for the current session.
    '''
    if filehandler_type == 'tmp':
        tmpdir = os.path.join(os.path.dirname(tempfile.mkdtemp()), session_dir)
    elif filehandler_type == 'shared':
        tmpdir = os.path.join(os.getenv('SHARED'), session_dir)
    else:
        tmpdir = None
    if tmpdir is not None:
        try:
            shutil.rmtree(tmpdir)
        except:
            pass

def load(filename):
    '''
    Returns a FileHandle for a path
    '''
    if filehandler is None:
        set_filehandler('memory')
    return filehandler(filename, session_dir=session_dir)

class Filepack(object):
    """
    A collection of files
    """
    def __init__(self, filelist):
        self.filepack = {}
        for filename in filelist:
            self.filepack[filename] = filehandler(filename, session_dir=session_dir)

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
        self.template = template
        self.inputs = []
        self.outputs = []
        self.constants = []
        self.STDOUT = None
        if filehandler is None:
            set_filehandler('memory')
        self.filehandler = filehandler
        if session_dir is None:
            raise SystemError('Error - session_dir is not set')
        self.session_dir = session_dir

        self.variables = []
        for key in re.findall(r'\{.*?\}', self.template):
            self.variables.append(key[1:-1])

    def set_inputs(self, inputs):
        """
        Set the inputs the kernel requires
        """
        if not isinstance(inputs, list):
            raise TypeError('Error - inputs must be of type list,'
                    ' not of type {}'.format(type(inputs)))
        self.inputs = inputs

    def set_outputs(self, outputs):
        """
        Set the outputs the kernel produces
        """
        if not isinstance(outputs, list):
            raise TypeError('Error - outputs must be of type list,'
                    ' not of type {}'.format(type(outputs)))
        self.outputs = outputs

    def set_constant(self, key, value):
        """
        Set a constant for the kernel
        If it was previously defined as an input variable, remove it from
        that list.
        """
        d = {}
        d['name'] = key
        if isinstance(value, str):
            if os.path.exists(value):
                d['value'] = self.filehandler(value, session_dir=self.session_dir)
            else:
                d['value'] = value
        else:
            d['value'] = value
        self.constants.append(d)

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
        td = tempfile.mkdtemp()
        with Path(td) as tmpdir:
            var_dict = {}
            for i in range(len(args)):
                if self.inputs[i] in self.variables:
                    var_dict[self.inputs[i]] = args[i]
                else:
                    try:
                        args[i].save(self.inputs[i])
                    except AttributeError:
                        raise TypeError('Error with variable {} {}'.format(i, args[i]))
            for d in self.constants:
                try:
                    d['value'].save(d['name'])
                except AttributeError:
                    var_dict[d['name']] = d['value']
            try:
                cmd = self.template.format(**var_dict)
                result = subprocess.check_output(cmd, shell=True,
                                                 stderr=subprocess.STDOUT)
                self.STDOUT = result.decode()
            except subprocess.CalledProcessError as e:
                print(e.output.decode())
                raise 
            for outfile in self.outputs:
                if os.path.exists(outfile):
                    outputs.append(self.filehandler(outfile, session_dir=self.session_dir))
                else:
                    if outfile == 'STDOUT':
                        outputs.append(self.STDOUT)
                    else:
                        outputs.append(None)
        try:
            shutil.rmtree(td)
        except:
            pass
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
        if filehandler is None:
            set_filehandler('memory')
        self.filehandler = filehandler
        self.session_dir = session_dir

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
                self.constants[key] = self.filehandler(value, session_dir=self.session_dir)

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
        #td = tempfile.TemporaryDirectory(dir=self.tmpdir)
        #with Path(td.name) as tmpdir:
        td = tempfile.mkdtemp(dir=self.tmpdir)
        with Path(td) as tmpdir:
            indict = {}
            for i, v in enumerate(args):
                if isinstance(v, dict):
                    for k in v:
                        if k in self.inputs:
                            try:
                                indict[k] = v[k].save(os.path.basename(v[k].path))
                            except AttributeError:
                                indict[k] = v[k]
                else:
                    try:
                        indict[self.inputs[i]] = v.save(os.path.basename(v.path))
                    except AttributeError:
                        indict[self.inputs[i]] = v
            for k in self.constants:
                try:
                    indict[k] = self.constants[k].save(os.path.basename(self.constants[k].path))
                except AttributeError:
                    indict[k] = self.constants[k]
            result = self.func(**indict)
            if not isinstance(result, list):
                result = [result]
            outputs = []
            for i, v in enumerate(result):
                if isinstance(v, str):
                    if os.path.exists(v):
                        outputs.append(self.filehandler(v, session_dir=self.session_dir))
                    else:
                        outputs.append(v)
                else:
                    outputs.append(v)
        try:
            shutil.rmtree(td)
        except:
            pass
        if len(outputs) == 1:
            outputs = outputs[0]
        else:
            outputs = tuple(outputs)
        return outputs

