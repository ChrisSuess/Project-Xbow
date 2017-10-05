#!/usr/bin/python2.7 

import os, errno, subprocess

cwd = os.getcwd()
file_path = cwd + "/mount"
base = os.path.basename(cwd)

print base
print file_path

try:
    os.mkdir(file_path)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

subprocess.call('rsync -avz --exclude mount ' + cwd + '/* ' + file_path + '/' + base, shell=True)
