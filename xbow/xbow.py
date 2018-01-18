import boto3
import base64
import paramiko
import time
import uuid
import datetime
import tempfile
class SpotMeter(object):
    """APPROXIMATE cost meter for a spot instance"""
    def __init__(self, instance_type, availability_zone, count = 1):
        """initialise the meter"""
        self.instance_type = instance_type
        self.availability_zone = availability_zone
        self.count = count
        self.ec2_resource = boto3.resource('ec2')
        dph = self.ec2_resource.meta.client.describe_spot_price_history
        data = dph(InstanceTypes=[instance_type], 
                   StartTime=datetime.datetime.now(), 
                   Filters=[{'Name': 'product-description', 
                             'Values':['Linux/UNIX']}, 
                            {'Name': 'availability-zone', 
                             'Values': [availability_zone]}
                           ]
                  )

        self.tz = data['SpotPriceHistory'][0]['Timestamp'].tzinfo
        self.start_time = datetime.datetime.now(self.tz)
        
    def current_price(self):
        """get the current spot price"""
        dph = self.ec2_resource.meta.client.describe_spot_price_history
        data = dph(InstanceTypes=[instance_type], 
                   StartTime=datetime.datetime.now(), 
                   Filters=[{'Name': 'product-description', 
                             'Values':['Linux/UNIX']}, 
                            {'Name': 'availability-zone', 
                             'Values': [self.availability_zone]}
                           ]
                  )

        spot_price = float(data['SpotPriceHistory'][0]['SpotPrice'])
        return spot_price * self.count
    
    def total_cost(self):
        """total cost since the meter was started"""
        dph = self.ec2_resource.meta.client.describe_spot_price_history
        data = dph(InstanceTypes=[instance_type], 
                   EndTime=datetime.datetime.now(self.tz),
                   StartTime=self.start_time, 
                   Filters=[{'Name': 'product-description', 
                             'Values':['Linux/UNIX']}, 
                            {'Name': 'availability-zone', 
                             'Values': [self.availability_zone]}
                           ]
                  )
        costsum = 0
        then = datetime.datetime.now(self.tz)
        for d in data['SpotPriceHistory']:
            now = then
            then = d['Timestamp']
            if then < self.start_time:
                then = self.start_time
            period = (now - then).seconds / 3600.0
            costsum += period * float(d['SpotPrice'])
            
        return costsum * self.count
    
    def total_time(self):
        """Total time (in hours) the meter has been running"""
        period = datetime.datetime.now(self.tz) - self.start_time
        return period.seconds / 3600.0
 
class ConnectedInstance(object):
    """ An Instance you can talk to"""
    def __init__(self, instance,  username, key_filename):
        self.instance = instance
        region = instance.placement['AvailabilityZone'][:-1]
        self.resource = boto3.resource('ec2', region_name=region)
        self.status = 'unknown'
        self.state = 'unknown'
        self.output = None
        self.exit_status = None
        self.update()
        if self.state != 'usable':
            return
        
        self.sshclient = paramiko.SSHClient()
        self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.sshclient.connect(instance.public_ip_address, username=username, 
                               key_filename=key_filename, timeout=10)
        self.status = 'ready'
        self.output = None
        
        
    
    def update(self):
        """Update status info"""
        
        self.instance.reload()
        self.state = self.instance.state['Name']
        if self.state == 'running':
            dis = self.resource.meta.client.describe_instance_status
            status = dis(InstanceIds=[self.instance.id])['InstanceStatuses'][0]
            system_status = status['SystemStatus']['Status']
            instance_status = status['InstanceStatus']['Status']
            if system_status == 'ok' and instance_status == 'ok':
                self.state = 'usable'
        
        if self.status == 'busy':
            while self.channel.recv_ready():
                self.output += self.channel.recv(1024)
            if self.channel.exit_status_ready():
                self.exit_status = self.channel.recv_exit_status()
                if self.state == 'usable':
                    self.status = 'ready'
                else:
                    self.status = 'unavailable'
                
    def wait(self, timeout=None):
        """wait until not busy"""
        start_time = time.time()
        max_wait_exceeded = False
        time.sleep(1)
        self.update()
        while self.status == 'busy' and not max_wait_exceeded:
            self.update()
            if timeout is not None:
                max_wait_exceeded = (time.time() - start_time).seconds > timeout
            if not max_wait_exceeded:
                time.sleep(5)
    
    def exec_command(self, script, block=True):
        """send a command to the instance"""
        
        self.update()
        if self.status == 'unavailable':
            self.output = 'Error - this instance is unavailable'
            self.exit_status = -1
            return
        
        if self.status != 'ready':
            self.output = 'Error - this instance is not ready'
            self.exit_status = -1
            return
        
        transport = self.sshclient.get_transport()
        self.channel = transport.open_session()
        self.channel.set_combine_stderr(True)
        self.channel.exec_command(script)
        self.status='busy'
        self.exit_status=None
        self.output = ''
        if block:
            self.wait()
        else:
            return
    
    def upload(self, localfile, remotefile):
        """upload a file"""
        transport = self.sshclient.get_transport()
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(localfile, remotefile)
        sftp.close()
        
    def download(self, remotefile, localfile):
        """download a file"""
        transport = self.sshclient.get_transport()
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.gett(remotefile, localfile)
        sftp.close()

class SpotInstancesPool(object):
    """A pool of persistent connected spot instances"""
    
    def __init__(self, count=1, price=1.0, image_id=None, region=None,
                 instance_type=None, 
                 launch_group=None,
                 security_groups=None, username=None, 
                 shared_file_system=None, mount_point=None):
    

        self.ec2_resource = boto3.resource('ec2', region_name=region)
        if launch_group is not None:
            response = self.ec2_resource.meta.client.describe_spot_instance_requests(Filters=[{'Name': 'launch-group', 'Values':[launch_group]},
              {'Name': 'state', 'Values': ['open', 'active']}])
            spot_instance_request_ids = [s['SpotInstanceRequestId'] for s in response['SpotInstanceRequests']]
            if len(spot_instance_request_ids) > 0:
               pool_exists = True
               self.instance_count = len(spot_instance_request_ids)
               image_id = response['SpotInstanceRequests'][0]['LaunchSpecification']['ImageId']
               self.spot_instance_request_ids = spot_instance_request_ids
               instance_type = response['SpotInstanceRequests'][0]['LaunchSpecification']['InstanceType']
            else:
               pool_exists = False
 
        if launch_group is None:
            self.key_name = str(uuid.uuid4())[:8]
            launch_group = self.key_name
        else:
            self.key_name = launch_group
        self.pem_file = '/Users/pazcal/.xbow/{}.pem'.format(launch_group)
        self.kp = self.ec2_resource.KeyPair(self.key_name)

        if not pool_exists:
            result = self.ec2_resource.meta.client.create_key_pair(KeyName=self.key_name)
            with open(self.pem_file, 'w') as f:
                f.write(result['KeyMaterial'])
        
        if username is None:
            image = self.ec2_resource.Image(image_id)
            tagdict = {}
            for tag in image.tags:
                tagdict[tag['Key']] = tag['Value']
            username = tagdict.get('username')

        efs_client = boto3.client('efs', region_name=region)
        if not pool_exists:
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
                    for subnet in subnets:
                        cmt = efs_client.create_mount_target
                        cmt(FileSystemId=FileSystemId, 
                            SubnetId=subnet.id, 
                            SecurityGroups=efs_security_groupid
                           )
                user_data = '#!/bin/bash\n mkdir {}\n'.format(mount_point)
                dnsname = '{}.efs.{}.amazonaws.com'.format(FileSystemId, region)
                mount_command = 'mount -t nfs -o nfsvers=4.1,rsize=1048576,'
                mount_command += 'wsize=1048576,hard,timeo=600,retrans=2 '
                mount_command += '{}:/ {}\n'.format(dnsname, mount_point)
                user_data += mount_command
                user_data += ' chmod go+rw {}\n'.format(mount_point)
            else:
                user_data = None
            rsi = self.ec2_resource.meta.client.request_spot_instances
            
            response = rsi(ClientToken=str(uuid.uuid4()),
                           InstanceCount=count,
                           SpotPrice=price,
                           Type='persistent',
                           LaunchGroup=launch_group,
                           LaunchSpecification={
                                                'SecurityGroups': security_groups,
                                                'ImageId': image_id,
                                                'InstanceType': instance_type,
                                                'KeyName': self.key_name,
                                                'UserData': base64.b64encode(user_data)
                                               })
            self.instance_count = count
            self.launch_group = launch_group
            self.spot_instance_request_ids = [sir['SpotInstanceRequestId'] for sir in response['SpotInstanceRequests']]
        if username is None:
            raise ValueError('Error - no username supplied')
        self.username = username
        self.connected_instances = None
        self.outputs = None
        self.exit_statuses = None
        self.status = None
        self.instances = None
        az = response['SpotInstanceRequests'][0]['LaunchSpecification']['Placement']['AvailabilityZone']
        self.meter = SpotMeter(instance_type, az, count=count)
        self.refresh()
        
        
    def update(self):
        """Update the status of the pool"""
        for ci in self.connected_instances:
            ci.update()
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
        """Update the list of running instances"""
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
        self.update()
        
    
    def terminate(self):
        """Terminate the pool of instances"""
        csr = self.ec2_resource.meta.client.cancel_spot_instance_requests
        response = csr(SpotInstanceRequestIds=self.spot_instance_request_ids)
        for i in self.instances:
            i.terminate()
        self.kp.delete()
    
    def exec_command(self, script, block=True):
        """Run a script on all instances in the pool"""
        self.update()
        if self.status == 'unavailable':
            self.refresh()
        for ci in self.connected_instances:
            ci.output = None
            ci.exec_command(script, block=False)
        if block:
            self.wait()
    
    def exec_commands(self, scriptlist, block=True):
        """Run each script in scriptlist on a different instance"""
        self.update()
        if self.status == 'unavailable':
            self.refresh()
        if len(scriptlist) > self.instance_count:
            raise ValueError('Error - more commands than available instances')
        for ci in self.connected_instances:
            ci.output = None
        for i in range(len(scriptlist)):
            self.connected_instances[i].exec_command(scriptlist[i], block=False)
        if block:
            self.wait()
    
    def upload(self, localfiles, remotefiles):
        """upload files to the pool"""
        self.update()
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
        """upload files to the pool"""
        self.update()
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
            self.connected_instances[i].download(zlist[i][0], zlist[i][1])
 
