from __future__ import print_function

from xbow import instances
from xbow import filesystems
from xbow import utilities
from xbow.instances import get_by_name

import xbow
import yaml
import os
import argparse
import subprocess

def create_lab():
    """
    Create a 'lab' - head node in the cloud
    """
    
    if not os.path.exists(os.path.expanduser('~/.xbow')):
        utilities.create_settings()

    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")

    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    schedulers = instances.get_by_name(cfg['scheduler_name'])
    if len(schedulers) > 1:
        print('Your Lab is already running.')
        exit(1)

    fs_id = filesystems.fs_id_from_name(cfg['shared_file_system'], 
                                        region=cfg['region'], 
                                        ) 
    
    if fs_id is None:
        print('A shared cloud filesystem does not exist')
        print('Creating a filesystem, this may take a moment...')
        fs_id = filesystems.create_fs(cfg['shared_file_system'],
                                     region=cfg['region'], 
                                     efs_security_groups=cfg['efs_security_groups']
                                    )

    cfg['fs_id'] = fs_id

    if len(schedulers) == 1:
        inst = schedulers[0]
        print('Scheduler already running')
    else:
        print("Starting the scheduler node - this may take some time...")

        user_data = '''Content-Type: multipart/mixed; boundary="//"
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

#!/bin/bash
pip install dask distributed && sudo -u ubuntu dask-scheduler > /home/ubuntu/scheduler.log 2>&1 &
mkdir -p {mount_point}
mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 {fs_id}.efs.{region}.amazonaws.com:/ {mount_point}
chmod go+rw {mount_point}
echo 'SHARED={mount_point} >> /etc/environment
'''.format(**cfg)
    
        final_data = '''
--//'''
    
        #extra_data = ''
        #if args.script:
        #    with open(args.script, 'r') as f:
        #        for line in f:
        #            if len(line) > 0 and line[0] != '#':
        #                extra_data += line

        #user_data = user_data + extra_data + final_data

        user_data = user_data + final_data 

        inst = instances.create_lab(
                                    cfg['scheduler_name'],
                                    image_id=cfg['image_id'],
                                    instance_type=cfg['scheduler_instance_type'],
                                    ec2_security_groups = cfg['ec2_security_groups'],
                                    user_data=user_data
                                   )
    
        ci = instances.ConnectedInstance(inst)
        print("All ready for use")

def xbow_login():
    """
    Login in to your head node
    """

    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")

    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    name = cfg['scheduler_name']

    if name is None:
        raise ValueError('Error - No lab has been provided')
        
    instances = get_by_name(name)
    
    if len(instances) == 0:
        raise ValueError('Error - Lab is not running')
    elif len(instances) > 1:
        raise ValueError('Error - more than one instance has that name')
    
    instance = instances[0]
    pem_file = '{}/{}.pem'.format(xbow.XBOW_CONFIGDIR, name)

    if instance.tags is not None:
        for tag in instance.tags:
            if tag['Key'] == 'username':
                username = tag['Value']
                
    if username is None:
        print('Warning: cannot determine username, assuming it is ubuntu')
        username = 'ubuntu'
        
    launch_command = "ssh -i {} {}@{} -oStrictHostKeyChecking=no".format(pem_file, username, instance.public_dns_name)
    #print(launch_command)
    subprocess.call(launch_command, shell=True)
