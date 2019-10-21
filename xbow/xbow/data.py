'''
data.py: data and databases
'''
import yaml
import os
from ecpc.configuration import ECPC_DIR
import boto3

default_data = {}
databasefile = os.path.join(ECPC_DIR, 'database.yml')
if not os.path.exists(databasefile):
    with open(databasefile, 'w') as f:
        yaml.dump(default_data, f, default_flow_style=False)

class Database(object):
    '''
    A simple database
    '''
    def __init__(self, databasefile):
        self.databasefile = databasefile
        with open(databasefile, 'r') as f:
            self.data = yaml.load(f, Loader=yaml.BaseLoader)

    def sync(self):
        with open(self.databasefile, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False)

    def add_entry(self, uid):
        self.data[uid] = {'uid': uid}
        self.sync()

    def remove_entry(self, uid):
        if not uid in self.data:
            raise IndexError('Error - entry {} does not exist.'.format(uid))
        result = self.data.pop(uid)
        self.sync()

    def update(self, uid, data):
        if not uid in self.data:
            raise IndexError('Error - entry {} does not exist.'.format(uid))
        for key in data:
            self.data[uid][key] = data[key]
        self.sync()

    def ids(self):
        return list(self.data.keys())
        
    def get(self, uid):
        if not uid in self.data:
            raise IndexError('Error - entry {} does not exist.'.format(uid))
        return self.data[uid]

database = Database(databasefile)
