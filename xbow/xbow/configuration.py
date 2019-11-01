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

preamble_data = '''Content-Type: multipart/mixed; boundary="//"
MIME-Version: 1.0

--//
Content-Type: text/cloud-config; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="cloud-config.txt"

#cloud-config
cloud_final_modules:
- [scripts-user, always]

--//
Content-Type: text/x-shellscript; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="userdata.txt"
'''
scheduler_user_data='''
#!/bin/bash
mkdir -p /run/metadata/xbow
touch /run/metadata/xbow/is_scheduler
echo 'XBOW_SHARED_FILESYSTEM={fs_id}.efs.{region}.amazonaws.com:/' > /run/metadata/xbow/shared_file_system
echo 'SHARED={mount_point}' >> /etc/environment
'''.format(**cfg)

scheduler_extra_data = ''
worker_extra_data = ''

if args.script:
    with open(args.script, 'r') as f:
        for_scheduler = True
        for_worker = True
        for line in f:
            if len(line) == 0:
                pass
            elif line[0] == '#':
                pass
            elif line[0] == '[':
                if '[all]' in line:
                    for_scheduler = True
                    for_worker = True
                elif [scheduler] in line:
                    for_scheduler = True
                    for_worker = False
                elif '[workers]' in line:
                    for_scheduler = False
                    for_worker = True
                else:
                    raise ValueError('Error - unrecognised command in provisioning file')
            else:
                if for_scheduler:
                    scheduler_extra_data += line
                if for_worker:
                    worker_extra_data += line

final_data = '''

--//'''

worker_user_data = '''
#!/bin/bash
mkdir -p /run/metadata/xbow
echo 'XBOW_SCHEDULER_IP_ADDRESS={scheduler_ip_address}' > /run/metadata/xbow/scheduler_ip_address
echo 'XBOW_WORKER_NPROCS={worker_nprocs}' >> /run/metadata/xbow/scheduler_ip_address
echo 'XBOW_SHARED_FILESYSTEM={fs_id}.efs.{region}.amazonaws.com:/' > /run/metadata/xbow/shared_file_system
echo 'SHARED={mount_point}' >> /etc/environment
'''.format(**cfg)
