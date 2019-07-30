from __future__ import print_function

from xbow import instances
from xbow import filesystems

import xbow
import yaml
import os
import argparse

def create_lab():
    """
    Create a 'lab' - head node in the cloud
    """

    cfg_file = os.path.join(xbow.XBOW_CONFIGDIR, "settings.yml")

    with open(cfg_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    schedulers = instances.get_by_name(cfg['scheduler_name'])
    if len(schedulers) > 1:
        print('Error - there is more than one scheduler already running with this name.')
        exit(1)

    fs_id = filesystems.fs_id_from_name(cfg['shared_file_system'], 
                                        region=cfg['region'], 
                                        ) 
    if fs_id is None:
        fs_id = filesystem.create_fs(cfg['shared_file_system'],
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
