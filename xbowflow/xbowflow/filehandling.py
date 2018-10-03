'''
filehanding.py: this module provides classes for passing files between
processes on distributed computing platforms that may not share a common
file system.
'''
from __future__ import print_function

import os
import tempfile
import zlib
from shutil import copyfile

'''
This module defines classes to handle files in distributed environments
where filesyatems may not be shared.

Objects of each class are instantiated with the path of an existing file on
an existing file syatem:

    fh = FileHandle('/path/to/file')

and have a save() method that creates a local copy of that file:

    filename_here = fh.save(filename_here)

'''
class FileHandle(object):
    '''
    Base class for file handlers
    '''
    def __init__(self, path):
        self.path = os.path.abspath(path)
   
    def __str__(self):
        return self.path

    def save(self, path):
        """
        Save the file

        args:
            path (str): file path

        returns:
            str: the path
        """
        abspath = os.path.abspath(path)
        if abspath != self.path:
            copyfile(self.path, path)
        return path

    def as_file(self):
        """
        Returns a path which points at the file
        """
        return self.path

class TempFileHandle(FileHandle):
    '''
    File handler that used $TMPDIR as shared space
    '''
    def __init__(self, path):
        super(TempFileHandle, self).__init__(path)
        ext = os.path.splitext(path)[1]
        self.tmp_path = tempfile.NamedTemporaryFile(suffix=ext, delete=False).name
        copyfile(self.path, self.tmp_path)
        
    def __del__(self):
        try:
            os.remove(self.tmp_path)
        except:
            pass

    def save(self, path):
        """
        Save a copy of the file.

        args:
            path (str): the path to use

        returns:
            str: the path used
        """
        copyfile(self.tmp_path, path)
        return path

    def as_file(self):
        """
        returns a path that points at the file
        """
        return self.tmp_path

class SharedFileHandle(FileHandle):
    '''
    File handler that stores data in some shared - e.g. NFS - space.
    Methods allow for $SHARED to point at different places on different nodes
    '''
    def __init__(self, path):
        super(SharedFileHandle, self).__init__(path)
        shared_dir = os.getenv('SHARED')
        if shared_dir is None:
            raise IOError('Error - environment variable $SHARED is not set')
        ext = os.path.splitext(path)[1]
        self.shared_path = tempfile.NamedTemporaryFile(suffix=ext,
                                                       dir=shared_dir,
                                                       delete=False).name
        copyfile(self.path, self.shared_path)

    def __del__(self):
        shared_dir = os.getenv('SHARED')
        if shared_dir is not None:
            shared_path = os.path.join(shared_dir, os.path.basename(self.shared_path))
            try:
                os.remove(shared_path)
            except:
                pass

    def save(self, path):
        """
        Save a copy of the file

        args:
            path (str): path for the saved file

        returns:
            str: path of the saved file
        """
        shared_dir = os.getenv('SHARED')
        if shared_dir is None:
            raise IOError('Error - environment variable $SHARED is not set')
        shared_path = self.as_file()
        copyfile(shared_path, path)
        return path

    def as_file(self):
        """
        Returns a path that points at the file
        """
        shared_dir = os.getenv('SHARED')
        if shared_dir is None:
            raise IOError('Error - environment variable $SHARED is not set')
        shared_path = os.path.join(shared_dir, os.path.basename(self.shared_path))
        return shared_path

class CompressedFileHandle(FileHandle):
    '''
    File handler that stores data in memory
    '''
    def __init__(self, path):
        super(CompressedFileHandle, self).__init__(path)
        with open(self.path, 'rb') as f:
            self.compressed_data = zlib.compress(f.read())

    def save(self, path):
        """
        Save a copy of the file

        args:
            path (str): path for the saved file

        returns:
            str: path of the saved file
        """
        with open(path, 'wb') as f:
            f.write(zlib.decompress(self.compressed_data))
        return path

    def as_file(self):
        """
        Returns a path that points at the file
        """
        ext = os.path.splitext(self.path)[1]
        tmp_path = tempfile.NamedTemporaryFile(suffix=ext, delete=False).name
        return self.save(tmp_path)
