import sys
import boto3
import os
import uuid
import base64
import time
import xbow

from .metering import SpotMeter
from .instances import ConnectedInstance

def create_spot_pool(name, count=1, price=1.0, image_id=None, region=None,
                     instance_type=None, user_data=None,
                     ec2_security_groups=None, username=None,
                     append=False, wait=True):
    """
    Creates an instance of a SpotInstancePool.

    Args:
        name (str): The name to give the SpotInstancePool. If append=False,
            it must not match any known pool in the same region.
        count (int, optional): Number of ConnectedInstances in the pool.
        price (float, optional): The target spot price, in dollars.
        image_id (str): The AMI to use.
        region (str, optional): The EC2 region to create instances in. If not
            specified the value in tbe boto3 configuration file is used.
        security_groups (list): List of security groups for the instance.
        username (str, optional): The username to connect to the instance. If
            not supplied, an attempt will be name to find it from the tags
            associated with the AMI.
        user_data (str, optional): Commands to be executed at start-up.
        append (bool, default False): Append these instances to an existing
            spot pool, if there is one.
        wait (bool, default True): Block until the pool is up and ready.

    Returns:
        SpotInstancePool

    """
    if region is None:
        region = boto3.session.Session().region_name
    if region is None:
        raise ValueError('Error - no region identified')
    ec2_resource = boto3.resource('ec2', region_name=region)
    ec2_client = boto3.client('ec2')
    dsir = ec2_client.describe_spot_instance_requests
    filters = [{'Name': 'launch-group', 'Values':[name]},
               {'Name': 'state', 'Values': ['open', 'active']}
              ]
    response = dsir(Filters=filters)
    spot_instance_request_ids = [s['SpotInstanceRequestId'] 
                                 for s in response['SpotInstanceRequests']
                                ]
    if len(spot_instance_request_ids) > 0:
        if not append:
            raise ValueError('Error - spot pool {} already exists'.format(name))
    launch_group = name
    key_name = launch_group
    pem_file = os.path.join(xbow.XBOW_CONFIGDIR, launch_group) + '.pem'
    if not os.path.exists(pem_file):
        raise RuntimeError('Error - cannot find key file {}'.format(pem_file))

    if username is None:
        image = ec2_resource.Image(image_id)
        tagdict = {}
        for tag in image.tags:
            tagdict[tag['Key']] = tag['Value']
        username = tagdict.get('username')

    rsi = ec2_client.request_spot_instances

    if sys.version_info > (3, 0):
        use_the_data = base64.b64encode(bytes(user_data, 'utf-8')).decode()
    elif sys.version_info[:2] <= (2, 7):
        use_the_data = base64.b64encode(user_data)

    response = rsi(ClientToken=str(uuid.uuid4()),
                   InstanceCount=count,
                   SpotPrice=price,
                   Type='persistent',
                   LaunchGroup=launch_group,
                   LaunchSpecification={
                                        'SecurityGroups': ec2_security_groups,
                                        'ImageId': image_id,
                                        'InstanceType': instance_type,
                                        'KeyName': key_name,
                                        'UserData': use_the_data
                                       })
        
    if wait:
        waiter = ec2_client.get_waiter('spot_instance_request_fulfilled')
        waiter.wait(Filters=filters)
    else:
        time.sleep(35)
    response = dsir(Filters=filters)
    spot_instance_ids = [s['InstanceId'] for s in response['SpotInstanceRequests']]
    taglist = [{'Key': 'username', 'Value': username}, 
               {'Key': 'name', 'Value': name}
              ]
    for spot_instance_id in spot_instance_ids:
        ec2_client.create_tags(Resources=[spot_instance_id],Tags=taglist)
    sip = SpotInstancePool(launch_group, region)
    return sip

'''
def create_elastic_spot_pool(name, count=1, price=1.0, image_id=None, region=None,
                     instance_type=None, user_data=None,
                     efs_security_groups=None, ec2_security_groups=None, username=None,
                     shared_file_system=None, mount_point=None):
    """
    Creates an instance of a SpotInstancePool.

    Args:
        name (str): The name to give the SpotInstancePool. It must not match 
            any known pool in the same region.
        count (int, optional): Number of ConnectedInstances in the pool.
        price (float, optional): The target spot price, in dollars.
        image_id (str): The AMI to use.
        region (str, optional): The EC2 region to create instances in. If not
            specified the value in tbe boto3 configuration file is used.
        security_groups (list): List of security groups for the instance.
        username (str, optional): The username to connect to the instance. If
            not supplied, an attempt will be name to find it from the tags
            associated with the AMI.
        user_data (str, optional): Commands to be executed at start-up.
        shared_file_system (str, optional): Name of an efs file system to
            attach to each instance.
        mount_point (str, optional): Mount directory for the shared file system.

    Returns:
        SpotInstancePool

    """
    if region is None:
        region = boto3.session.Session().region_name
    if region is None:
        raise ValueError('Error - no region identified')
    ec2_resource = boto3.resource('ec2', region_name=region)
    ec2_client = boto3.client('ec2')
    response = ec2_resource.meta.client.describe_spot_instance_requests(Filters=[{'Name': 'launch-group', 'Values':[name]},
      {'Name': 'state', 'Values': ['open', 'active']}])
    spot_instance_request_ids = [s['SpotInstanceRequestId'] for s in response['SpotInstanceRequests']]
    launch_group = name
    key_name = launch_group
    pem_file = os.path.join(xbow.XBOW_CONFIGDIR, launch_group) + '.pem'
    if not os.path.exists(pem_file):
        raise RuntimeError('Error - cannot find key file {}'.format(pem_file))

    if username is None:
        image = ec2_resource.Image(image_id)
        tagdict = {}
        for tag in image.tags:
            tagdict[tag['Key']] = tag['Value']
        username = tagdict.get('username')

    efs_client = boto3.client('efs', region_name=region)
    if shared_file_system is not None:
        dfs = efs_client.describe_file_systems
        response = dfs(CreationToken=shared_file_system)['FileSystems']
        if len(response) > 0:
            FileSystemId = response[0]['FileSystemId']
        else:
            cfs = efs_client.create_file_system
            response = cfs(CreationToken=shared_file_system)
            FileSystemId = response['FileSystemId']

        subnets = ec2_resource.subnets.all()
        sgf = ec2_resource.security_groups.filter
        security_groups = sgf(GroupNames=efs_security_groups)
        efs_security_groupid = [security_group.group_id
                                    for security_group in security_groups]
        response = efs_client.describe_mount_targets(FileSystemId = FileSystemId)
        mounttargets = response["MountTargets"]
        if len(mounttargets) == 0:
            for subnet in subnets:
                cmt = efs_client.create_mount_target
                cmt(FileSystemId=FileSystemId,
                    SubnetId=subnet.id,
                    SecurityGroups=efs_security_groupid
                   )

        mount_command = '#!/bin/bash\n mkdir -p {}\n'.format(mount_point)
        dnsname = '{}.efs.{}.amazonaws.com'.format(FileSystemId, region)
        mount_command += 'mount -t nfs -o nfsvers=4.1,rsize=1048576,'
        mount_command += 'wsize=1048576,hard,timeo=600,retrans=2 '
        mount_command += '{}:/ {}\n'.format(dnsname, mount_point)
        mount_command += ' chmod go+rw {}\n'.format(mount_point)
        mount_command += "echo 'SHARED={}' >> /etc/environment \n".format(mount_point)
        mount_command += "echo 'XFLOWBUCKETNAME={}' >> /etc/environment \n".format(shared_file_system)
    else:
        mount_command = None
    if user_data is None:
        user_data = mount_command
    else:
        user_data = mount_command + user_data

    rsi = ec2_resource.meta.client.request_spot_instances

    if sys.version_info > (3, 0):
        use_the_data = base64.b64encode(bytes(user_data, 'utf-8')).decode()

    if sys.version_info[:2] <= (2, 7):
        use_the_data = base64.b64encode(user_data)

    response = rsi(ClientToken=str(uuid.uuid4()),
                   InstanceCount=count,
                   SpotPrice=price,
                   Type='persistent',
                   LaunchGroup=launch_group,
                   LaunchSpecification={
                                        'SecurityGroups': ec2_security_groups,
                                        'ImageId': image_id,
                                        'InstanceType': instance_type,
                                        'KeyName': key_name,
                                        'UserData': use_the_data
                                       })
    """    
    n_up = 0
    while n_up == 0:
        time.sleep(5)
        response = ec2_resource.meta.client.describe_spot_instance_requests(Filters=[{'Name': 'launch-group', 'Values':[launch_group]},
              {'Name': 'state', 'Values': ['open', 'active']}])
        spot_instance_request_ids = [s['SpotInstanceRequestId'] for s in response['SpotInstanceRequests']]
        spot_instance_ids = [s['InstanceId'] for s in response['SpotInstanceRequests']]
        #print(spot_instance_ids)
        #for spot_instance_id in spot_instance_ids:
        #    print(spot_instance_id)
        n_up = len(spot_instance_request_ids)
    """
    time.sleep(35)
    response = ec2_resource.meta.client.describe_spot_instance_requests(Filters=[{'Name': 'launch-group', 'Values':[launch_group]},
          {'Name': 'state', 'Values': ['open', 'active']}])
    spot_instance_request_ids = [s['SpotInstanceRequestId'] for s in response['SpotInstanceRequests']]
    spot_instance_ids = [s['InstanceId'] for s in response['SpotInstanceRequests']]
    for spot_instance_id in spot_instance_ids:
        ec2_client.create_tags(Resources=[spot_instance_id],Tags=[{'Key': 'username', 'Value': username}, {'Key': 'name', 'Value': name}])
    #sip = SpotInstancePool(launch_group, region)
    #return sip

'''
class SpotInstancePool(object):
    """A pool of persistent connected spot instances"""

    def __init__(self, name, region=None):
        """
        Load an instance of a SpotInstancePool.

        Args:
            name (str): name of the SpotInstancePool, as given when it was
                created.
            region (str, optional): Name of the EC2 region. If not supplied,
                the default value from the boto3 configuration file is used.

        Attributes:
            name (str): Name of the pool.
            status (str): Status of the pool. Takes the value of the most
                significant ststus of any instance in the pool, in the order:
                "busy" > "unavailable" > "ready" > "unknown".
            meter (InstanceMeter): an InstanceMeter for the pool, initialised
                at the time of loading (not of pool creation!).
            outputs (list): Outputs from the last command run on each instance
                in the pool.
            exit_statuses (list): Exit status of the last command run on each
                instance in the pool.
        """

        if region is None:
            region = boto3.session.Session().region_name
        if region is None:
            raise ValueError('Error - no region identified')
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.name = name
        response = self.ec2_resource.meta.client.describe_spot_instance_requests(Filters=[{'Name': 'launch-group', 'Values':[name]},
          {'Name': 'state', 'Values': ['open', 'active']}])
        self.spot_instance_request_ids = [s['SpotInstanceRequestId'] for s in response['SpotInstanceRequests']]
        if len(self.spot_instance_request_ids) == 0:
            raise ValueError('Error - spot pool {} does not exist'.format(name))
        else:
            self.instance_count = len(self.spot_instance_request_ids)

        az = response['SpotInstanceRequests'][0]['LaunchSpecification']['Placement']['AvailabilityZone']
        instance_type = response['SpotInstanceRequests'][0]['LaunchSpecification']['InstanceType']
        self.meter = SpotMeter(instance_type, az, count=self.instance_count)
        self.launch_group = name
        self.key_name = name
        self.kp = self.ec2_resource.KeyPair(self.key_name)
        self.pem_file = os.path.join(xbow.XBOW_CONFIGDIR, self.key_name) + '.pem'

        image_id = response['SpotInstanceRequests'][0]['LaunchSpecification']['ImageId']
        image = self.ec2_resource.Image(image_id)
        tagdict = {}
        if image.tags is None:
            raise ValueError('Error - the chosen image does not define the username')
        for tag in image.tags:
            tagdict[tag['Key']] = tag['Value']
        self.username = tagdict.get('username')

        if self.username is None:
            raise ValueError('Error - the chosen image does not define the username')

        self.outputs = None
        self.exit_statuses = None
        self.status = None
        self.instances = None
        self.connected_instances = None
        self.refresh()

    def get_status(self):
        """
        Update the status of the pool
        Updates all pool attributes.
        """
        for ci in self.connected_instances:
            ci.get_status()
        self.outputs = [ci.output for ci in self.connected_instances]
        self.exit_statuses = [ci.exit_status for ci in self.connected_instances]
        statuses = [ci.status for ci in self.connected_instances]
        if 'busy' in statuses:
            self.status = 'busy'
        else:
            if 'unavailable' in statuses:
                self.status = 'unavailable'
            else:
                self.status = 'ready'

    def wait(self):
        """Wait until the pool is not busy"""
        for ci in self.connected_instances:
            ci.wait()
        self.outputs = [ci.output for ci in self.connected_instances]
        self.exit_statuses = [ci.exit_status for ci in self.connected_instances]
        statuses = [ci.status for ci in self.connected_instances]
        if 'unavailable' in statuses:
            self.status = 'unavailable'
        else:
            self.status = 'ready'

    def refresh(self):
        """Update the list of running instances.

        Checks the status of each instance in the pool, and if they appear
        to have died, waits for them to be replaced by the EC2 persistent
        spot instance process.
        """
        if self.connected_instances is not None:
            if self.status == 'busy':
                raise RuntimeError("Error - cannot refresh while the pool is busy")

        if self.instances is None:
            n_up = 0
        else:
            for i in self.instances:
                i.reload()
            n_up = [i.state for i in self.instances].count('running')

        while n_up < self.instance_count:
            self.instances = self.ec2_resource.instances.filter(Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'spot-instance-request-id', 'Values': self.spot_instance_request_ids}
            ])
            self.instance_ids = [i.id for i in self.instances]
            n_up = len(self.instance_ids)
            if n_up < self.instance_count:
                time.sleep(15)

        my_waiter = self.ec2_resource.meta.client.get_waiter('instance_status_ok')
        my_waiter.wait(InstanceIds=self.instance_ids)
        self.connected_instances = [ConnectedInstance(i,
                                                      self.username,
                                                      self.pem_file)
                                    for i in self.instances]
        self.get_status()

    def terminate(self):
        """Terminate the pool of instances"""
        csr = self.ec2_resource.meta.client.cancel_spot_instance_requests
        response = csr(SpotInstanceRequestIds=self.spot_instance_request_ids)
        for i in self.instances:
            i.terminate()
        self.kp.delete()

    def exec_command(self, command, block=True):
        """
        Run a command on all instances in the pool.

        Args:
             command (str): The script to execute.
             block (bool, optional): Whether or not to wait until the command
                 completes before returning.
        """
        self.get_status()
        if self.status == 'unavailable':
            self.refresh()
        for ci in self.connected_instances:
            ci.output = None
            ci.exec_command(command, block=False)
        if block:
            self.wait()

    def exec_commands(self, commandlist, block=True):
        """
        Run each command in commandlist on a different instance.

        Args:
            commandlist (list): List of commands (str) to run. The list length
                must be less than or equal to the pool size.
            block (bool, optional): Whether or not to wait until the commands
                complete before returning.
        """

        self.get_status()
        if self.status == 'unavailable':
            self.refresh()
        if len(commandlist) > self.instance_count:
            raise ValueError('Error - more commands than available instances')
        for ci in self.connected_instances:
            ci.output = None
        for i in range(len(commandlist)):
            self.connected_instances[i].exec_command(commandlist[i], block=False)
        if block:
            self.wait()

    def upload(self, localfiles, remotefiles):
        """
        Upload files to the pool.

        Each local file in the list localfiles is uploaded to a different
        instance, with the remote name taken from the same element in
        remotefiles. If either of localfiles or remotefiles is a string, it
        is expanded to [filename] * *pool_size*. The two lists must be equal
        in length and less than or equal to *pool_size*. If the list lengths
        are less than *pool_size*, later instances get no files.
        """
        self.get_status()
        if self.status == 'unavailable':
            self.refresh()
        if isinstance(localfiles, list):
            if len(localfiles) > self.instance_count:
                raise ValueError('Error - more elements in localfiles list than instances in the pool')
        if isinstance(remotefiles, list):
            if len(remotefiles) > self.instance_count:
                raise ValueError('Error - more elements in remotefiles list than instances in the pool')
        if isinstance(localfiles, list) and not isinstance(remotefiles, list):
            remotefiles = [remotefiles] * len(localfiles)
        if isinstance(remotefiles, list) and not isinstance(localfiles, list):
            localfiles = [localfiles] * len(remotefiles)
        if not (isinstance(localfiles, list) and isinstance(remotefiles, list)):
            localfiles = [localfiles] * self.instance_count
            remotefiles = [remotefiles] * self.instance_count
        if len(localfiles) != len(remotefiles):
                raise ValueError('Error - filelists must be the same length')
        zlist = zip(localfiles, remotefiles)
        for i in range(len(zlist)):
            self.connected_instances[i].upload(zlist[i][0], zlist[i][1])

    def download(self, localfiles, remotefiles):
        """
        Download files from the pool.

        localfiles must be a list of length <= *pool_size*; remotefiles
        can be the same, or a single string in which case it is expanded
        to [remotefiles] * len(localfiles).
        """
        self.get_status()
        if self.status == 'unavailable':
            self.refresh()
        if not isinstance(localfiles, list):
            raise ValueError('Error - localfiles must be a list')
        else:
            if len(localfiles) > self.instance_count:
                raise ValueError('Error - more elements in localfiles list than instances in the pool')
        if isinstance(remotefiles, list):
            if len(remotefiles) > self.instance_count:
                raise ValueError('Error - more elements in remotefiles list than instances in the pool')
        if not isinstance(remotefiles, list):
            remotefiles = [remotefiles] * len(localfiles)
        if len(localfiles) != len(remotefiles):
                raise ValueError('Error - filelists must be the same length')
        zlist = zip(localfiles, remotefiles)
        for i in range(len(zlist)):
            self.connected_instances[i].download(zlist[i][0], zlist[i][1])

class BatchPool(object):
    """
    A simple batch job oriented pool class.
    
    """
    def __init__(self, pool):
        """Create a new BatchPool instance.
        
        Args:
            pool (SpotInstancePool): the pool of instances to run the jobs
            
        Attributes:
            status (list): status of each instance in the BatchPool. Each may be one of
                "running", "finished", or "terminated".
            outputs [list]: outputs (so far) from the last command submitted to each instance.
            exit_statuses [list]: exit status for the last command submitted to each instance, or None if
                it is still running.
        """
        self.pool = pool
        self.status = []
        self.jobids = []
        self.exit_statuses = []
        self.get_exitstatuses()
        self.pool.exec_command("ps -e | grep runme.sh")
        for output in self.pool.outputs:
            if 'runme.sh' in output:
                self.status.append('running')
                self.jobids.append(output.split()[0])
            else:
                self.status.append('idle')
                self.jobids.append(1)
        for i in range(len(self.exit_statuses)):
            if self.exit_statuses[i] != None and self.status == 'idle':
                self.status = 'finished'
        self.outputs = []
        self.wait()
    
    def submit(self, commands):
        """
        Submit commands to the pool.
        
        Args:
            commands (str or list): commands to execute. If a string, the same command
                is executed on each instance. If a list, each element is sent to a different
                instance.
            """
        if "running" is self.status:
            raise RuntimeError('Error - the pool is still busy')
        if not isinstance(commands, list):
            self.commands = [commands] * self.pool.instance_count
        else:
            self.commands = commands
        self.cleanup()
        self.pool.exec_command("echo \#\!/bin/bash > test/runme.sh")
        self.pool.exec_commands(["echo {} >> test/runme.sh".format(cmd) for cmd in self.commands])
        #self.pool.exec_command("echo echo \$? \> _EXITCODE_ >> test/runme.sh")
        self.pool.exec_command("cd test; ~/bin/jobrunner.sh runme.sh > runme.log; ps -e | grep runme.sh")
        self.jobids = [int(output.split()[0]) for output in self.pool.outputs]
        self.status = ['submitted'for i in range(self.pool.instance_count)]
        
    def get_status(self):
        """
        Update the batch pool attributes.
        """
        commands = ['ps -p {} -h'.format(jid) for jid in self.jobids]
        self.pool.exec_commands(commands)
        self.status = []
        for output in self.pool.outputs:
            if 'runme.sh' in output:
                self.status.append('running')
            else:
                self.status.append('finished')
        self.get_output()
        
    def wait(self):
        """
        Wait until all commands have completed.
        """
        self.get_status()
        while 'running' in self.status:
            time.sleep(10)
            self.get_status()
        self.get_exitstatuses()
        self.cleanup()
        
    def cancel(self):
        """
        Cancel all jobs.
        """
        self.pool.exec_command('killall runme.sh')
        cmds = []
        for i in range(len(self.status)):
            if self.status[i] == 'running':
                cmds.append('echo 1 > test/_EXITCODE_')
                self.status[i] = 'terminated'
            else:
                cmds.append('ls')
        self.pool.exec_commands(cmds)
        self.get_output()
        self.get_exitstatuses()
  
    def get_output(self):
        """
        Update the outputs attribute with data from the instances.
        """
        self.pool.exec_command('cat test/runme.log')
        self.outputs = self.pool.outputs

    def get_exitstatuses(self):
        self.pool.exec_command('if [[ -a test/_EXITCODE_ ]]; then cat test/_EXITCODE_; fi')
        self.exit_statuses = []
        for out in self.pool.outputs:
            if out == '':
                self.exit_statuses.append(None)
            else:
                self.exit_statuses.append(int(out))
            
    def cleanup(self):
        self.pool.exec_command('rm test/runme.log test/runme.sh test/_EXITCODE_')
