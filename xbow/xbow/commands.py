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
import sys
import uuid
import glob

from xbow.metering import SpotMeter
from xbow.instances import get_by_name, ConnectedInstance
from xbow.filesystems import fs_id_from_name
from xbow import pools

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

def create_project(project=None, files=None):
    """
    create a project directory
    """
    
    if project is None:
        get_input = input
        if sys.version_info[:2] <= (2, 7):
            get_input = raw_input
        project = get_input("Please give your project a name:")
    
    #mount_point = cfg['mount_point']
    mount_point = '/home/ubuntu/shared'
    fullpath = mount_point + '/' + project
    
    try:
        os.mkdir(fullpath)
    except OSError:
        print ("Creation of the project '%s' failed, does it already exist?" % project)
    else:
        print ("Successfully created the project '%s' " % project)

def xflow(command, workers):
    """
    Copy files and run
    """
    
    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")
    
    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    
    command = ' '.join(sys.argv[1:])
    pack_n_run(command)
    boot_workers(workers)

def pack_n_run(command):
    """
    Stage the contents of the current directory to the xbow cluster, then
    run the given command, creating the neccessary worker instance.
    """

    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")
    
    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    
    instances = get_by_name(cfg['scheduler_name'])
    if len(instances) == 0:
        raise ValueError('Error - no such instance')
    elif len(instances) > 1:
        raise ValueError('Error - more than one instance has that name')
    instance = instances[0]
    ci = ConnectedInstance(instance)
    az = instance.placement['AvailabilityZone']
    meter = SpotMeter(cfg['worker_instance_type'], az, count = cfg['pool_size'])
    jobid = uuid.uuid4()
    mount_point=cfg['mount_point']

    ci.exec_command('sudo apt update && sudo apt install -y task-spooler && tsp -S 80')
    print('remote directory will be {}/{}'.format(mount_point, jobid))
    ci.exec_command('mkdir {}/{}'.format(mount_point, jobid))
    infiles = glob.glob('*')
    print('uploading files:')
    for filename in infiles:
        if os.path.isfile(filename):
            print('    {}'.format(filename))
            ci.upload(filename, '{}/{}/{}'.format(mount_point, jobid, filename))
    ci.exec_command("cd {}/{} && tsp xflow-exec '{}'".format(mount_point, jobid, command)) 
    tsp_id = ci.output[:-1]
    print('tsp job {} submitted.'.format(tsp_id))

    HOSTFILE = open(os.path.expanduser('.xbow_ids.yml'), 'w+')
    HOSTFILE.write('jobid: {}\n'.format(jobid))
    HOSTFILE.write('tsp_id: {}\n'.format(tsp_id))
    HOSTFILE.close()

def boot_workers(workers):
    
    #parser = argparse.ArgumentParser()
    #parser.add_argument('-s', '--script', help='name of provisioning script')
    #parser.add_argument('-n', '--n_workers', help='number of workers to launch')

    #args = parser.parse_args()

    
    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")
    
    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    
    fs_id = filesystems.fs_id_from_name(cfg['shared_file_system'],
                                   region=cfg['region']
                                  )

    cfg['fs_id'] = fs_id
    #print(fs_id)
    #print(cfg['fs_id'])
    print("Job has been submitted, now starting a workers. This may take some time...")
    
    instances = get_by_name(cfg['scheduler_name'])
    inst = instances[0]
    #print(inst.private_ip_address)

    cfg['scheduler_ip_address'] = inst.private_ip_address
    #print(cfg['scheduler_ip_address'])
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
pip install dask distributed && sudo -u ubuntu dask-worker --local-directory /tmp/dask --nthreads 1 --nprocs 1 --worker-port 45792 {scheduler_ip_address}:8786 &
mkdir -p {mount_point}
mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 {fs_id}.efs.{region}.amazonaws.com:/ {mount_point}
chmod go+rw {mount_point}
echo 'SHARED={mount_point}' >> /etc/environment

'''.format(**cfg)

    final_data = '''

--//'''

    user_data = user_data + final_data
    #print(user_data)

    n_workers = workers

    sip = pools.create_spot_pool(cfg['worker_pool_name'],
                            count=n_workers,
                            price=cfg['price'],
                            image_id=cfg['image_id'],
                            instance_type=cfg['worker_instance_type'],
                            ec2_security_groups=cfg['ec2_security_groups'],
                            user_data=user_data
                          )  
    print("Worker now ready. Please use `xbow-check` to monitor your job...")
