#! /usr/bin/env python3
#
# When files are synced between different unix/Mac computers by
# OneDrive, sometimes it seems to randomly alter permissions, e.g
# add or delete execute permissions. This script uses 'git diff'
# to check for, and if neccessary correct, this.
#
import subprocess
from collections import deque
import os

def get_fname(string):
    '''
    Extract the filename from a string produced by 'git diff'
    '''
    f_parts = []
    append = False
    for w in string.split():
        if 'a/' in w[:2]:
            append = True
            f_parts.append(w[2:])
        elif 'b/' in w[:2]:
            append = False
        else:
            if append:
                f_parts.append(w)
    return ' '.join(f_parts)

def get_mode(string):
    '''
    Extract the file mode from a string produced by 'git diff'm
    '''
    return int(string.split()[2], 8)

git_diff = subprocess.run('git diff', shell=True, 
                          stdout=subprocess.PIPE, universal_newlines=True)

lines = git_diff.stdout.split('\n')
lbuffer = deque(lines[:2], maxlen=3)
for line in lines[2:]:
    lbuffer.append(line)
    if lbuffer[0][:4] == 'diff':
        if lbuffer[1][:3] == 'old' and lbuffer[2][:3] == 'new':
            fname = get_fname(lbuffer[0])
            oldmode = get_mode(lbuffer[1])
            newmode = get_mode(lbuffer[2])
            os.chmod(fname, oldmode)

