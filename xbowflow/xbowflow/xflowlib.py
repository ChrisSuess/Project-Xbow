'''
Xflowlib: the Xflow library to build workflows on an Xbow cluster
'''
import re
import subprocess
import os
import os.path as op
import tempfile
import shutil
import copy
import hashlib
import glob
import uuid
import numpy as np
from path import Path
from .filehandling import SharedFileHandle, CompressedFileHandle, TempFileHandle, FileHandle

filehandler = None
filehandler_type = None
session_dir = str(uuid.uuid4())
STDOUT = "STDOUT"
DEBUGINFO = "DEBUGINFO"

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

def _gen_filenames(pattern, n_files):
    '''
    Generate a list of filenames consistent with a pattern.
    '''
    if not '?' in pattern and not '*' in pattern:
        raise ValueError('Error - the pattern must contain * or ?')
    l = int(np.log10(n_files)) + 1
    if '*' in pattern:
        w = pattern.split('*')
        template = '{}{{:0{}d}}{}'.format(w[0], l, w[1])
    else:
        w = pattern.split('?')
        if pattern.count('?') < l:
            raise ValueError('Error - too many files for this pattern')
        template = '{}{{:0{}d}}{}'.format(w[0], pattern.count('?'), w[-1])
    filenames = [template.format(i) for i in range(n_files)]
    return filenames
            
class Filepack(object):
    """
    A collection of files
    """
    def __init__(self, filelist):
        self.filepack = []
        for filename in filelist:
            self.filepack.append(load(filename))

    def _gen_filenames(self, pattern):
        '''
        Generate a list of filenames consistent with a pattern.
        '''
        if not '?' in pattern and not '*' in pattern:
            raise ValueError('Error - the pattern must contain * or ?')
        n_files = len(self.filepack)
        l = int(np.log10(n_files)) + 1
        if '*' in pattern:
            w = pattern.split('*')
            template = '{}{{:0{}d}}{}'.format(w[0], l, w[1])
        else:
            w = pattern.split('?')
            if pattern.count('?') < l:
                raise ValueError('Error - too many files for this pattern')
            template = '{}{{:0{}d}}{}'.format(w[0], pattern.count('?'), w[-1])
        filenames = [template.format(i) for i in range(n_files)]
        return filenames
            
    def unpack(self, pattern, outputdir='.'):
        '''
        Unpack the files in the Filepack into the given directory.
        '''
        filenames = self._gen_filenames(pattern)
        for i, f in enumerate(self.filepack):
            outname = os.path.join(outputdir, filenames[i])
            f.save(outname)

    def append(self, other):
        if not isinstance(other, FileHandle):
            raise ValueError('Error - cannot add a {} to a Filepack'.format(type(other)))
        else:
            self.filepack.append(other)

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
                    if isinstance(args[i], list):
                        fnames = _gen_filenames(self.inputs[i], len(args[i]))
                        for j, f in enumerate(args[i]):
                            try:
                                f.symlink(fnames[j])
                            except AttributeError:
                                f.save(fnames[j])
                    else:
                        try:
                            args[i].symlink(self.inputs[i])
                        except AttributeError:
                            try:
                                args[i].save(self.inputs[i])
                            except AttributeError:
                                raise TypeError('Error: cannot process kernel argument {} {}'.format(i, args[i]))
            for d in self.constants:
                try:
                    d['value'].save(d['name'])
                except AttributeError:
                    var_dict[d['name']] = d['value']
            cmd = self.template.format(**var_dict)
            try:
                result = subprocess.run(cmd, shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True,
                                        check=True)
            except subprocess.CalledProcessError as e:
                r2 = subprocess.run(['ls', '-l'], stdout=subprocess.PIPE,
                                    universal_newlines=True)
                result = CalledProcessError(e, extra=r2.stdout)
                if not DEBUGINFO in self.outputs:
                    raise result

            self.STDOUT = result.stdout
            for outfile in self.outputs:
                if '*' in outfile or '?' in outfile:
                    outf = glob.glob(outfile)
                    outf.sort()
                    outputs.append([self.filehandler(f, session_dir=self.session_dir) for f in outf])
                else:
                    if op.exists(outfile):
                        outputs.append(self.filehandler(outfile, session_dir=self.session_dir))
                    elif outfile == STDOUT:
                        outputs.append(self.STDOUT)
                    elif outfile == DEBUGINFO:
                        outputs.append(result)
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
class XflowError(Exception):
    """
    Base class for Xflowlib exceptions.
    """
    pass

class CalledProcessError(XflowError):
    """
    Exception raised if a kernel fails with an error.

    A cosmetic wrapper round subprocess.CalledProcessError
    """

    def __init__(self, e, extra=''):
        self.cmd = e.cmd
        self.returncode = e.returncode
        self.stdout = e.stdout + extra
        self.stderr = e.stderr
        self.output = self.stdout

    def __str__(self):
        return 'Error: command "{}" failed with return code {}; STDOUT="{}"; STDERR="{}"'.format(self.cmd, self.returncode, self.stdout, self.stderr)
