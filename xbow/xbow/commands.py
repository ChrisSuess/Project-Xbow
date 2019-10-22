from __future__ import print_function

import os
import sys
import yaml
import xbow
import subprocess
import uuid
import glob
import argparse
import boto3

from xbow.configuration import XBOW_DIR, config
from xbow import instances
from xbow import filesystems
from xbow.instances import get_by_name
from xbow.instances import ConnectedInstance
from xbow import pools
from xbow.metering import SpotMeter

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

def xbow_login_lab():
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

def create_experiment(region=None, instance_type=None, tag=None):
    '''
    Create and launch an instance
    '''
    if region is None:
        region = config['region']
    if instance_type is None:
        instance_type = config['instance_type']

    try:
        utilities.valid_selection(region, instance_type)
    except ValueError as e:
        print(e)
        exit(1)
    if tag is not None:
        if tag in database.ids():
            print('Error: name {} is already in use'.format(tag))
            exit(1)
        uid = tag
    else:
        uid = str(uuid.uuid4())[:8]
    database.add_entry(uid)
    data = {}
    data['uid'] = uid
    data['region'] = region
    data['instance_type'] = instance_type
    data['pem_file'] = None
    data['security_group_id'] = None
    data['image_id'] = None
    data['security_group_id'] = None
    data['instance_id'] = None
    database.update(uid, data)
    print('creating a {instance_type} instance in region {region} with ID {uid}'.format(**data))

    key_material = utilities.create_key_pair(region, uid)
    pem_file = utilities.create_pem_file(XBOW_DIR, uid, key_material)
    data['pem_file'] = pem_file
    database.update(uid, data)
    print('key pair created')

    security_group_id = utilities.create_security_group(region, uid)
    data['security_group_id'] = security_group_id
    database.update(uid, data)
    print('security group created')

    image_id = utilities.ami_from_source(region, config['source'])
    data['image_id'] = image_id
    database.update(uid, data)
    print('required ami identified')

    print('launching instance')
    try:
        instance_id = utilities.launch(XBOW_DIR, region, uid, image_id, instance_type)
        data['instance_id'] = instance_id
        database.update(uid, data)
        print('instance {instance_id} launched'.format(**data))
    except ClientError as e:
        print(e)
        terminate_instance(uid)

