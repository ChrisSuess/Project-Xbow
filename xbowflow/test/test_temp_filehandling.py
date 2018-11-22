import unittest
import os

from xbowflow import xflowlib, filehandling

class TestTempFilehandlingMethods(unittest.TestCase):

    def test_filehandle_methods_for_temp(self):
        xflowlib.set_filehandler('tmp')
        self.assertEqual(xflowlib.filehandler_type, 'tmp')
        self.assertEqual(xflowlib.filehandler, filehandling.TempFileHandle)
        fh = xflowlib.load('data/test.txt')
        self.assertIsInstance(fh, filehandling.FileHandle)
        fh.save('tempfile.txt')
        self.assertTrue(os.path.exists('tempfile.txt'))
        with open('data/test.txt', 'rb') as f1:
            d1 = f1.read()
        with open('tempfile.txt', 'rb') as f2:
            d2 = f2.read()
        self.assertEqual(d1, d2)
        os.remove('tempfile.txt')
        self.assertFalse(os.path.exists('tempfile.txt'))
        tmpname = fh.as_file()
        self.assertTrue(os.path.exists(tmpname))
        #del(fh)
        #self.assertFalse(os.path.exists(tmpname))

    def test_filehandle_methods_for_shared(self):
        xflowlib.set_filehandler('shared')
        self.assertEqual(xflowlib.filehandler_type, 'shared')
        self.assertEqual(xflowlib.filehandler, filehandling.SharedFileHandle)
        fh = xflowlib.load('data/test.txt')
        self.assertIsInstance(fh, filehandling.FileHandle)
        fh.save('tempfile.txt')
        self.assertTrue(os.path.exists('tempfile.txt'))
        with open('data/test.txt', 'rb') as f1:
            d1 = f1.read()
        with open('tempfile.txt', 'rb') as f2:
            d2 = f2.read()
        self.assertEqual(d1, d2)
        os.remove('tempfile.txt')
        self.assertFalse(os.path.exists('tempfile.txt'))
        tmpname = fh.as_file()
        self.assertTrue(os.path.exists(tmpname))
        #del(fh)
        #self.assertFalse(os.path.exists(tmpname))

    def test_filehandle_methods_for_memory(self):
        xflowlib.set_filehandler('memory')
        self.assertEqual(xflowlib.filehandler_type, 'memory')
        self.assertEqual(xflowlib.filehandler, filehandling.CompressedFileHandle)
        fh = xflowlib.load('data/test.txt')
        self.assertIsInstance(fh, filehandling.FileHandle)
        fh.save('tempfile.txt')
        self.assertTrue(os.path.exists('tempfile.txt'))
        with open('data/test.txt', 'rb') as f1:
            d1 = f1.read()
        with open('tempfile.txt', 'rb') as f2:
            d2 = f2.read()
        self.assertEqual(d1, d2)
        os.remove('tempfile.txt')
        self.assertFalse(os.path.exists('tempfile.txt'))
        tmpname = fh.as_file()
        self.assertTrue(os.path.exists(tmpname))
        del(fh)
        #self.assertFalse(os.path.exists(tmpname))

    def test_filehandle_methods_for_bad_value(self):
        with self.assertRaises(ValueError):
            xflowlib.set_filehandler('should_fail')
