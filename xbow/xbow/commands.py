from __future__ import print_function

import os
import re
import sys
import yaml
import xbow
import subprocess
import uuid
import glob
import argparse
import boto3
import pytz
from botocore.exceptions import ClientError

from datetime import datetime

from xbow.data import database
from xbow import utilities
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

    cfg['image_id'] = utilities.get_image_id(cfg)
    image_id = cfg['image_id']

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
mkdir -p /run/metadata/xbow
touch /run/metadata/xbow/is_scheduler
echo 'XBOW_SHARED_FILESYSTEM={fs_id}.efs.{region}.amazonaws.com:/' > /run/metadata/xbow/shared_file_system
echo 'FS_ID={shared_file_system}' >> /run/metadata/xbow/shared_file_system
echo 'SHARED=/home/ubuntu/shared' >> /etc/environment
'''.format(**cfg)

        final_data = '''
--//'''

        user_data = user_data + final_data 

        inst = instances.create_lab(
                                    cfg['scheduler_name'],
                                    image_id=image_id,
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

def create_experiment(job_schd, region=None, instance_type=None, tag=None, worker_type=None, image_id=None):
    '''
    Create and launch an instance
    '''

    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")

    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    with open(job_schd, 'r') as tag1:
        for line in tag1:
            if re.search('#XBOW-CLUS cluster_name', line):
                 newline = line.replace('#XBOW-CLUS cluster_name: ', "")
                 tag = newline[:-1]
    
    with open(job_schd, 'r') as region1:
        for line in region1:
            if re.search('#XBOW-CLUS region', line):
                 newline = line.replace('#XBOW-CLUS region: ', "")
                 region = newline[:-1]
    if region is None:
        region = config['region']

    with open(cfg_file, 'r') as ymlfile:
        #print(ymlfile.read()),
        for line in ymlfile:
            if re.search('#XBOW-CLUS image_name', line):
                newline = line.replace('#XBOW-CLUS image_name: ', "")
                newline = newline.replace('"', "")
                newline = newline[:-1]
                image = {}
                image['image_name'] = newline
                image['region'] = region
    #image['image_name'] = utilities.get_image_id(image)
    #image_id = image['image_name']
    if image_id is None:
        config['image_id'] = utilities.get_image_id(config)
        image_id = config['image_id']

    with open(job_schd, 'r') as itype:
        for line in itype:
            if re.search('#XBOW-CLUS scheduler_instance_type:', line):
                 newline = line.replace('#XBOW-CLUS scheduler_instance_type: ', "")
                 instance_type = newline[:-1]
    if instance_type is None:
        instance_type = config['instance_type']

    with open(job_schd, 'r') as wtype:
        for line in wtype:
            if re.search('#XBOW-CLUS worker_instance_type:', line):
                 newline = line.replace('#XBOW-CLUS worker_instance_type: ', "")
                 worker_type = newline[:-1]
    if worker_type is None:
        worker_type = config['worker_type']
    
    with open(job_schd, 'r') as psize:
        for line in psize:
            if re.search('#XBOW-CLUS pool_size:', line):
                 newline = line.replace('#XBOW-CLUS pool_size: ', "")
                 pool_size = newline[:-1]
                 pool_size = int(pool_size)
    if pool_size is None:
        print('no workers specified')
        
    #if image_id is None:
    #    image_id = config['image_id']

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
    data['image_id'] = cfg['image_id']
    data['security_group_id'] = None
    data['instance_id'] = None
    data['fs_id'] = None
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

    image_id = cfg['image_id']
    if image_id is None: 
        image_id = utilities.ami_from_source(region, config['source'])
    database.update(uid, data)
    print('required ami identified')
    
    fs_path = os.path.abspath('/run/metadata/xbow/shared_file_system')
    with open(fs_path, 'r') as fs_path1:
        for line in fs_path1:
            if re.search('FS_ID=', line):
                FS_ID = line.replace('FS_ID=', "")
                FS_ID = FS_ID.replace('"', "")
                FS_ID = FS_ID[:-1]

    fs_id = filesystems.fs_id_from_name(FS_ID, 
                                       region=data['region'] 
                                       )
    if fs_id is None:
        print('creating a new filesystem')
        fs_id = filesystems.create_fs(cfg['shared_file_system'],
                                      region=cfg['region'], 
                                      efs_security_groups=cfg['efs_security_groups']
                                     )
    data['fs_id'] = fs_id
    database.update(uid, data)
    print('required filesystem attached')
    
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
echo 'SHARED=/home/ubuntu/shared' >> /etc/environment
'''.format(**data)

    scheduler_extra_data = ''
    worker_extra_data = ''

    final_data = '''

--//'''
    
    schd_data = preamble_data + scheduler_user_data + scheduler_extra_data + final_data
    

    print('launching scheduler')
    try:
        instance_id = utilities.launch_schd(XBOW_DIR, region, uid, image_id, instance_type, schd_data)
        data['instance_id'] = instance_id.id
        database.update(uid, data)
        print('instance {instance_id} launched'.format(**data))
    except ClientError as e:
        print(e)
        terminate_instance(uid)

    data['scheduler_ip_address'] = instance_id.private_ip_address
    if not 'worker_nprocs' in cfg:
        data['worker_nprocs'] = 1
    database.update(uid, data)

    worker_user_data = '''
#!/bin/bash
mkdir -p /run/metadata/xbow
echo 'XBOW_SCHEDULER_IP_ADDRESS={scheduler_ip_address}' > /run/metadata/xbow/scheduler_ip_address
echo 'XBOW_WORKER_NPROCS={worker_nprocs}' >> /run/metadata/xbow/scheduler_ip_address
echo 'XBOW_SHARED_FILESYSTEM={fs_id}.efs.{region}.amazonaws.com:/' > /run/metadata/xbow/shared_file_system
echo 'SHARED=/home/ubuntu/shared' >> /etc/environment
'''.format(**data)

    work_data = preamble_data + worker_user_data + worker_extra_data + final_data

    try:
        workers = utilities.launch_work(XBOW_DIR, region, uid, image_id, worker_type, work_data, pool_size)
        for i in range(len(workers)):
            worker = workers[i]
            data['worker{}'.format(i)] = worker.id
        #data['workers_id'] = workers
        database.update(uid, data)
        print('workers launched')
        #print('instance {instance_id} launched'.format(**data))
    except ClientError as e:
        print(e)
        terminate_instance(uid)

def list_instances():
    '''
    List running instances.
    '''
    ids = database.ids()
    rows = []
    row = ['ID', 'region', 'type', 'up_time', 'state', 'cost($)']
    rows.append(row)
    for uid in ids:
        data = database.get(uid)
        region = data['region']
        instance = utilities.get_instance(region, uid)
        if instance is None:
            data['up_time'] = '********'
            data['state'] = 'FAILED'
            data['cost'] = 0.0
        else: 
            state = utilities.get_instance_state(region, uid)
            data['instance_type'] = instance.instance_type
            utc = pytz.UTC
            up = datetime.now(utc) - instance.launch_time
            hours, remainder = divmod(int(up.total_seconds()), 3600)
            minutes, remainder = divmod(remainder, 60)
            seconds, remainder = divmod(remainder, 60)
            data['up_time'] = '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
            data['state'] = state
            data['cost'] = utilities.get_instance_cost(region, uid)
        row = '{uid} {region} {instance_type} {up_time} {state} {cost:3.2f}'.format(**data).split()
        rows.append(row)
    widths = [max(map(len, col)) for col in zip(*rows)]
    if len(rows) == 1:
        return
    for row in rows:
        print("  ".join((val.ljust(width) for val, width in zip(row, widths))))

def terminate_instance(uid):
    entry = database.get(uid)
    region = entry['region']
    utilities.terminate_cluster(region, uid)
    print('instance terminated')
    utilities.delete_security_group(region, uid)
    print('security group deleted')
    utilities.delete_key_pair(region, uid)
    print('key pair deleted')
    utilities.delete_pem_file(XBOW_DIR, uid)
    print('.pem file deleted')
    database.remove_entry(uid)

def transfer(source, target):
    uid = utilities.get_transfer_uid(XBOW_DIR, source, target)
    try:
        entry = database.get(uid)
    except IndexError as e:
        print(e)
        exit(1)
    command = utilities.get_transfer_string(XBOW_DIR, entry['region'], uid, source, target)
    state = utilities.get_instance_state(entry['region'], uid)
    if state is not 'ready':
        print('Instance is not ready, in state {}'.format(state))
    else:
        exit(subprocess.call(command, shell=True))
