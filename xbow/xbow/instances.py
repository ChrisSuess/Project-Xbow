import boto3
import paramiko
import time
import uuid
import datetime
import os
import xbow

class ConnectedInstance(object):
    """ An Instance you can talk to"""
    def __init__(self, instance,  username=None, key_filename=None):
        """
        Create a ConnectedInstance.

        Args:
            instance (boto3 Instance): A boto3 Instance
            username (str, optional): The username required to connect to the instance
            key_filename (str, optional): Name of the .pem file

        Attributes:
            status (str): Information about whether the instance can. or is,
                doing anything. Can take values "unknown", "ready", "busy", and
                "unavailable".
            state (str): Information about the general health of the instance.
                Can take standard EC2 values ("running", "terminated", etc.) but
                also "usable" when the instance is running and has also passed
                accessibility checks.
            output (str): The output received from the instance so far, since
                the last command was sent to it.
            exit_status (str): The exit status of the last command sent to the
                instance.

        """
        self.instance = instance
        region = instance.placement['AvailabilityZone'][:-1]
        self.resource = boto3.resource('ec2', region_name=region)
        self.sshclient = paramiko.SSHClient()
        self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.wait_until_usable()
        
        if username is None:
            if self.instance.tags is not None:
                tagdict = {}
                for tag in self.instance.tags:
                    tagdict[tag['Key']] = tag['Value']
                if 'username' in tagdict:
                    username = tagdict['username']
                else:
                    raise ValueError('Error - no username was supplied and the instance is not tagged.')
        
        if key_filename is None:
            key_filename = os.path.join(xbow.XBOW_CONFIGDIR, self.instance.key_name) + '.pem'
        if not os.path.exists(key_filename):
            raise RuntimeError('Error - cannot find the key file {}'.format(key_filename))
                
        self.sshclient.connect(instance.public_ip_address, username=username,
                               key_filename=key_filename, timeout=10)
        self.transport = self.sshclient.get_transport()
        if not self.transport.is_active():
            raise RuntimeError('Error - problem with connection to instance')
        
        self.status = 'unknown'
        self.state = 'unknown'
        self.output = None
        self.exit_status = None
        self.channel = None
        self.get_state()
        self.get_status()

    def get_state(self):
        """
        Update the state info for the instance.
        
        This is like the standard paramiko instance.state, but with the extra
        category of *usable* with means *running* and system/instance statuses ok.
        """
        self.instance.reload()
        self.state = self.instance.state['Name']
        if self.state == 'running':
            dis = self.resource.meta.client.describe_instance_status
            status = dis(InstanceIds=[self.instance.id])['InstanceStatuses'][0]
            system_status = status['SystemStatus']['Status']
            instance_status = status['InstanceStatus']['Status']
            if system_status == 'ok' and instance_status == 'ok':
                self.state = 'usable'

    def wait_until_usable(self):
        """
        Wait until the instance reaches the *usable* state.
        """
        self.get_state()
        if self.state in ['shutting-down', 'terminated', 'stopping', 'stopped']:
            raise RuntimeError('Error - this instance is stopped or terminated.')
        while self.state != 'usable':
            time.sleep(5)
            self.get_state()
            
    def get_status(self):
        """
        Update status info.

        Updates the *state*, *status*, *output* and *exit_status* attributes
        of the ConnectedInstance.
        """
        self.get_state()
        if self.state != 'usable':
            self.status = 'unavailable'
        else:
            if self.channel is None:
                self.status = 'ready'
            else:
                self.status = 'busy'
            
        if self.status == 'busy':
            while self.channel.recv_ready():
                self.output += self.channel.recv(1024).decode('utf-8')
            if self.channel.exit_status_ready():
                self.exit_status = self.channel.recv_exit_status()
                self.channel.close()
                self.get_state()
                if self.state == 'usable':
                    self.status = 'ready'
                else:
                    self.status = 'unavailable'

    def wait(self, timeout=None):
        """
        Wait until not busy.

        Args:
            timeout (float, optional): The maximum time to wait, in seconds. If
                not supplied, wait will wait as long as required.
        """
        start_time = time.time()
        max_wait_exceeded = False
        time.sleep(1)
        self.get_status()
        while self.status == 'busy' and not max_wait_exceeded:
            self.get_status()
            if timeout is not None:
                max_wait_exceeded = (time.time() - start_time).seconds > timeout
            if not max_wait_exceeded:
                time.sleep(5)

    def exec_command(self, script, block=True):
        """
        Send a command to the instance.

        Args:
            script (str): The unix command to execute on the instance.
            block (bool, optional): Whether to wait for the command to complete
                or return immediately.
        """

        self.get_status()
        if self.status != 'ready':
            raise RuntimeError('Error - this instance is {}'.format(self.status))

        self.channel = self.transport.open_session()
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
        """
        Upload a file to the instance.
        
        Args:
            localfile (str): name of the file on the local filesystem.
            remotefile (str): name of the file on the instance's filesystem.
                Relative paths are interpreted relative to the $HOME directory
                of the instances *username*.

        """
        sftp = paramiko.SFTPClient.from_transport(self.transport)
        sftp.put(localfile, remotefile)
        sftp.close()

    def download(self, remotefile, localfile):
        """
        Download a file from the instance.
        
        Args:
            remotefile (str): name of the file on the instance's filesystem.
                Relative paths are interpreted relative to the $HOME directory
                of the instances "username*.
            localfile (str): name of the file on the local filesystem.
        """
        sftp = paramiko.SFTPClient.from_transport(self.transport)
        sftp.get(remotefile, localfile)
        sftp.close()
        
    def terminate(self):
        self.instance.terminate()
        
def get_by_name(name, region=None):
    """
    Return a list of instances with this name. The list may be empty..
    """
    if region is None:
        region = boto3.session.Session().region_name
    if region is None:
        raise ValueError('Error - no region identified')
    ec2_resource = boto3.resource('ec2', region_name=region)
    instances = list(ec2_resource.instances.filter(Filters=[{'Name': 'key-name', 'Values': [name]}, {'Name': 'instance-state-name', 'Values': ['running']}]))
    return instances 

def create(name, image_id, instance_type, region=None, 
           user_data=None, ec2_security_groups=None, username=None):
    """
    Creates a single instance - not in the spot pool
    """
    sshclient = paramiko.SSHClient()
    sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if region is None:
        region = boto3.session.Session().region_name
    if region is None:
        raise ValueError('Error - no region identified')
    ec2_resource = boto3.resource('ec2', region_name=region)
    key_name = name
    pem_file = os.path.join(xbow.XBOW_CONFIGDIR, key_name) + '.pem'
    if not os.path.exists(pem_file):
        raise RuntimeError('Error - cannot find {}'.format(pem_file))

    instances = get_by_name(key_name)
    if len(instances) > 0:
        raise ValueError('Error - an instance with this name already exists')
        
    image = ec2_resource.Image(image_id)

    instance = ec2_resource.create_instances(ImageId=image_id, 
                                             InstanceType=instance_type, 
                                             KeyName=key_name,
                                             UserData=user_data, 
                                             SecurityGroups=ec2_security_groups,
                                             ClientToken=str(uuid.uuid4()), 
                                             MaxCount=1, MinCount=1
                                            )[0]
    instance.wait_until_running()
    instance.reload()

    if username is None:
        for test_username in ['ubuntu', 'ec2_user']:
            try:
                sshclient.connect(instance.public_ip_address, 
                                  username=test_username,
                                  key_filename=pem_file
                                 )
                username = test_username
                sshclient.close()
                break
            except:
                pass

    if username is None:
        username = 'ubuntu'
    image.create_tags(Tags=[{'Key': 'username', 'Value': username}])
    instance.create_tags(Tags=[{'Key': 'username', 'Value': username}, 
                               {'Key': 'name', 'Value': name}
                              ]
                        )
    return instance

def terminate_cluster(name, region=None):
    """
    Terminates the cluster given by the name specified in settings.yml
    """
    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)

    dsir = client.describe_spot_instance_requests
    response = dsir(Filters=[{'Name': 'launch-group', 'Values': [name]}])
    spot_instance_request_ids = [s['SpotInstanceRequestId'] 
                                 for s in response['SpotInstanceRequests']
                                ]

    if len(spot_instance_request_ids) > 1:
        print('cancelling all spot requests')
        csir =  client.cancel_spot_instance_requests
        csir(SpotInstanceRequestIds=spot_instance_request_ids, DryRun=False)

    filters = [{'Name': 'key-name', 'Values': [name]}, 
               {'Name': 'instance-state-name', 'Values': ['running']}
              ]
    instances = list(resource.instances.filter(Filters=filters))

    if len(instances) == 0:
        raise ValueError('Error - no such cluster')
    else:
        print('Terminating instances')
        for instance in instances:
            instance.terminate(DryRun=False)
