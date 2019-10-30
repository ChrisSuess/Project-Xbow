'''
configuration.py: configuration and defaults
'''
import yaml
import os
import boto3

XBOW_DIR = os.path.join(os.getenv('HOME'), '.xbow-test')

session = boto3.session.Session()
default_data = {}
default_config = {'instance_type': 't2.small'}
default_config['worker_type'] = None
default_config['region'] = session.region_name
default_config['source'] = '099720109477/ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-20180912'
default_config['image_name'] = 'image_name: "*xbow-packer-*"'

if not os.path.exists(XBOW_DIR):
    os.mkdir(XBOW_DIR)

configfile = os.path.join(XBOW_DIR, 'config.yml')
if not os.path.exists(configfile):
    with open(configfile, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    config = default_config
else:
    with open(configfile, 'r') as f:
        config = yaml.load(f, Loader=yaml.BaseLoader)
