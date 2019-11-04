'''
utilities.py: basic functions to launch, connect to, and delete an instance.
'''
import boto3
import uuid
import datetime
import os
import sys

def valid_selection(region, instance_type):
    '''
    Returns a unique ID for the new instance to be launched.

    Checks that the chosen region and instance type are legal.
    '''
    client = boto3.client('ec2')
    session = boto3.Session()
    regions = session.get_available_regions('ec2')
    instance_types = client._service_model.shape_for('InstanceType').enum

    if not instance_type in instance_types:
        raise ValueError('Error: the chosen instance type ({}) is not available'.format(instance_type))
    if not region in regions:
        raise ValueError('Error: no such region as {}'.format(region))
    return    

def create_key_pair(region, uid):
    '''
    Create a key pair for the given uid.
    '''
    if get_key_pair(region, uid) is not None:
        delete_key_pair(region, uid)
    client = boto3.client('ec2', region_name=region)
    response = client.create_key_pair(KeyName=uid)
    return response.get('KeyMaterial')

def create_pem_file(dirname, uid, key_material):
    pem_file_name = os.path.join(dirname, '{}.pem'.format(uid))
    with open(pem_file_name, 'w') as f:
        f.write(key_material)
    os.chmod(pem_file_name, 0o600)
    #print('Key pair created.')
    return pem_file_name

def delete_key_pair(region, uid):
    '''
    Delete a key pair.
    '''
    resource = boto3.resource('ec2', region_name=region)
    if get_key_pair(region, uid) is not None:
        key_pair = resource.KeyPair(uid)
        key_pair.delete()

def delete_pem_file(dirname, uid):
    pem_file_name = os.path.join(dirname, '{}.pem'.format(uid))
    if os.path.exists(pem_file_name):
        os.remove(pem_file_name)

def create_security_group(region, uid):
    '''
    Create a unique security group for this uid.
    '''
    sgid = get_security_group_id(region, uid)
    if sgid is not None:
        return sgid
    client = boto3.client('ec2', region_name=region)
    response = client.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    response = client.create_security_group(GroupName=uid,
                                     Description='Security group for instance {}'.format(uid),
                                     VpcId=vpc_id)
    security_group_id = response['GroupId']
    #print('Security Group Created {} in vpc {}.'.format(security_group_id, vpc_id))
    
    data = client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 2049,
             'ToPort': 2049,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])
    #print('Ingress Successfully Set.')
    return security_group_id

def delete_security_group(region, uid):
    '''
    Delete a security group
    '''
    sgid = get_security_group_id(region, uid)
    if sgid is None:
        return
    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)
    response = client.describe_security_groups(GroupNames=[uid])
    security_group_id = response.get('SecurityGroups', [{}])[0].get('GroupId', '')
    security_group = resource.SecurityGroup(security_group_id)
    security_group.delete()
    

def ami_from_source(region, source):
    '''
    Select a suitable ami based on the source (manifest-location) string.
    '''
    client = boto3.client('ec2', region_name=region)
    filters=[{'Name': 'manifest-location', 
              'Values': [source]}]
    result = client.describe_images(ExecutableUsers=['all'], Filters=filters)

    amis = [i['ImageId'] for i in result['Images']]
    if len(amis) == 0:
        raise ValueError('Error: cannot find a suitable image')
    image_id = amis[0]
    #print('Using image {}'.format(image_id))
    return image_id

def launch(dirname, region, uid, image_id, instance_type, worker_type, schd_data, worker_data):
    '''
    Launch the instance.
    '''
    instance_id = get_instance_id(region, uid)
    if instance_id is not None:
        return instance_id

    key_name = get_key_pair(region, uid)
    if key_name is None:
        key_material = create_key_pair(region, uid)
        key_name = uid
        pem_file = create_pem_file(dirname, uid, key_material)

    security_group_id = get_security_group_id(region, uid)
    if security_group_id is None:
        security_group_id = create_security_group(region, uid)

    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)
    instances = resource.create_instances(ImageId=image_id, 
                                         InstanceType=instance_type, 
                                         MaxCount=1, 
                                         MinCount=1, 
                                         KeyName=uid, 
                                         UserData=schd_data,
                                         SecurityGroupIds=[security_group_id], 
                                         ClientToken=str(uuid.uuid4()),
                                         InstanceMarketOptions={'MarketType': 'spot'},
                                         TagSpecifications=[
                                                {
                                                    'ResourceType' : 'instance',
                                                    'Tags' : [
                                                        {
                                                             'Key': 'Name', 'Value': uid + 'scd',
                                                             'Key': 'name', 'Value': uid + 'scd'
                                                        },
                                                     ]
                                                },
                                            ],
                                        )
    instance = instances[0]
    if worker_type is not None:
        workers = resource.create_instances(ImageId=image_id,
                                            InstanceType=worker_type,
                                            MaxCount=4,
                                            MinCount=4,
                                            KeyName=uid,
                                            UserData=worker_data,
                                            SecurityGroupIds=[security_group_id],
                                            ClientToken=str(uuid.uuid4()),
                                            InstanceMarketOptions={'MarketType': 'spot'},
                                            TagSpecifications=[
                                                {
                                                    'ResourceType' : 'instance',
                                                    'Tags' : [
                                                        {
                                                             'Key': 'Name', 'Value': uid,
                                                             'Key': 'name', 'Value': uid
                                                        },
                                                     ]
                                                },
                                            ],
                                           )

    #waiter = client.get_waiter('instance_status_ok')
    #waiter.wait(InstanceIds=[instance.instance_id])
    #instance.reload()
    return instance.instance_id

def launch_schd(dirname, region, uid, image_id, instance_type, schd_data):
    '''
    Launch the schd.
    '''
    instance_id = get_instance_id(region, uid)
    if instance_id is not None:
        return instance_id

    key_name = get_key_pair(region, uid)
    if key_name is None:
        key_material = create_key_pair(region, uid)
        key_name = uid
        pem_file = create_pem_file(dirname, uid, key_material)

    security_group_id = get_security_group_id(region, uid)
    if security_group_id is None:
        security_group_id = create_security_group(region, uid)

    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)
    instances = resource.create_instances(ImageId=image_id, 
                                         InstanceType=instance_type, 
                                         MaxCount=1, 
                                         MinCount=1, 
                                         KeyName=uid, 
                                         UserData=schd_data,
                                         SecurityGroupIds=[security_group_id], 
                                         ClientToken=str(uuid.uuid4()),
                                         InstanceMarketOptions={'MarketType': 'spot'},
                                         TagSpecifications=[
                                                {
                                                    'ResourceType' : 'instance',
                                                    'Tags' : [
                                                        {
                                                             'Key': 'Name', 'Value': uid + 'scd',
                                                             'Key': 'name', 'Value': uid + 'scd'
                                                        },
                                                     ]
                                                },
                                            ],
                                        )
    instance = instances[0]
    #return instance.instance_id
    return instance

def launch_work(dirname, region, uid, image_id, worker_type, worker_data):
    '''
    Launch the workers. Viva La Resistance
    '''
    instance_id = get_instance_id(region, uid)
    if instance_id is not None:
        return instance_id

    key_name = get_key_pair(region, uid)
    if key_name is None:
        key_material = create_key_pair(region, uid)
        key_name = uid
        pem_file = create_pem_file(dirname, uid, key_material)

    security_group_id = get_security_group_id(region, uid)
    if security_group_id is None:
        security_group_id = create_security_group(region, uid)

    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)
    if worker_type is None:
       print('no worker has been specified')
       sys.exit()

    print('arming the workers')
    workers = resource.create_instances(ImageId=image_id,
                                        InstanceType=worker_type,
                                        MaxCount=4,
                                        MinCount=4,
                                        KeyName=uid,
                                        UserData=worker_data,
                                        SecurityGroupIds=[security_group_id],
                                        ClientToken=str(uuid.uuid4()),
                                        InstanceMarketOptions={'MarketType': 'spot'},
                                        TagSpecifications=[
                                                 {
                                                    'ResourceType' : 'instance',
                                                    'Tags' : [
                                                        {
                                                             'Key': 'Name', 'Value': uid,
                                                             'Key': 'name', 'Value': uid
                                                        },
                                                     ]
                                                },
                                            ],
                                        )

    #return workers.instance_id
    return workers


def get_instance_cost(region, uid):
    '''
    Returns the APPROXIMATE cost so far for the instance
    '''
    instance = get_instance(region, uid)
    if instance is None:
        return None
    client = boto3.client('ec2', region_name=region)
    launch_time = instance.launch_time
    tz = launch_time.tzinfo
    dph = client.describe_spot_price_history
    data = dph(InstanceTypes=[instance.instance_type],
               EndTime=datetime.datetime.now(tz),
               StartTime=instance.launch_time,
               Filters=[{'Name': 'product-description',
                         'Values': ['Linux/UNIX']},
                        {'Name': 'availability-zone',
                         'Values': [instance.placement['AvailabilityZone']]}
                       ]
               )
    costsum = 0
    then = datetime.datetime.now(tz)
    for d in data['SpotPriceHistory']:
        now = then
        then = d['Timestamp']
        if then < launch_time:
            then = launch_time
        period = (now - then).seconds / 3600.0
        costsum += period * float(d['SpotPrice'])

    return costsum

def get_instance_id(region, uid):
    '''
    Returns the Instance ID for the given uid.
    '''
    client = boto3.client('ec2', region_name=region)
    response = client.describe_instances(Filters=[{'Name': 'key-name', 'Values': [uid]}])
    rs = response.get('Reservations', [{}])
    if len(rs) == 0:
        return None
    instance_id = response.get('Reservations', [{}])[0].get('Instances', [{}])[0].get('InstanceId')
    return instance_id

def get_instance(region, uid):
    '''
    Returns an Instance object for the given uid
    '''
    instance_id = get_instance_id(region, uid)
    if instance_id is None:
        return None
    resource = boto3.resource('ec2', region_name=region)
    return resource.Instance(instance_id)

def get_instance_state(region, uid):
    '''
    Get the state of an instance - enhanced version of the usual boto3 version
    that distinguishes between 'running' and 'ready'.
    '''
    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)
    instance_id = get_instance_id(region, uid)
    if instance_id is None:
        return None
    instance = resource.Instance(instance_id)
    state = instance.state['Name']
    if state == 'running':
        status = client.describe_instance_status(InstanceIds=[instance_id])['InstanceStatuses'][0]
        system_status = status['SystemStatus']['Status']
        instance_status = status['InstanceStatus']['Status']
        if system_status == 'ok' and instance_status == 'ok':
            state = 'ready'
        else:
            state = 'booting-up'
    return state
    
def get_security_group_id(region, uid):
    '''
    Returns the security group for the given uid
    '''
    client = boto3.client('ec2', region_name=region)
    try:
        response = client.describe_security_groups(GroupNames=[uid])
    except:
        return None
    sgs = response.get('SecurityGroups', [{}])
    if len(sgs) == 0:
        return None
    security_group_id = response.get('SecurityGroups', [{}])[0].get('GroupId')
    return security_group_id

def get_key_pair(region, uid):
    '''
    Returns the key pair for the given uid
    '''
    client = boto3.client('ec2', region_name=region)
    try:
        response = client.describe_key_pairs(KeyNames=[uid])
    except:
        return None
    kps = response.get('KeyPairs', [{}])
    if len(kps) == 0:
        return None
    key_name = response.get('KeyPairs', [{}])[0].get('KeyName')
    return key_name
    
def get_pem_file(dirname, uid):
    '''
    Returns the .pem file for a given uid.
    '''
    pem_file_name = os.path.join(dirname, '{}.pem'.format(uid))
    if not os.path.exists(pem_file_name):
        pem_file_name = None
    return pem_file_name
        
def terminate(region, uid):
    '''
    Terminate the given instance.
    '''
    instance_id = get_instance_id(region, uid)
    if instance_id is None:
        return
    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)
    instance = resource.Instance(instance_id)
    response = instance.terminate()
    waiter = client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=[instance_id])
    #print('Instance terminated.')

def get_login_string(dirname, region, uid):
    '''
    Returns the command required to log in to the instance.
    '''
    pem_file_name = get_pem_file(dirname, uid)
    if pem_file_name is None:
        return None
    resource = boto3.resource('ec2', region_name=region)
    instance_id = get_instance_id(region, uid)
    instance = resource.Instance(get_instance_id(region, uid))
    command = 'ssh -i {} ubuntu@{} -oStrictHostKeyChecking=no'.format(pem_file_name, instance.public_ip_address)
    return command

def create_settings():
    """
    Create a settings configuration file for use with xbow
    """
    try:
	
        if not os.path.exists(os.path.expanduser('~/.xbow')):
            os.makedirs(os.path.expanduser('~/.xbow'))

        # Test for the old directory presence (IE updating).
        if os.path.isdir(os.path.expanduser('~/.Xbow')):

            os.rename(os.path.expanduser('~/.Xbow'),
                      os.path.expanduser('~/.xbow'))
        
	# Setting up the .xbow directory.
        if not os.path.isfile(os.path.expanduser('~/.xbow/settings.yml')):
            print('Xbow will create a hidden directory in your $HOME directory \n'
                  'in which it will create the hosts configuration file. You will\n'
                  'need to edit this file with your cloud preferences for the \n'
                  'cloud machines you wish to use. See documentation for more \n'
                  'information on best cloud practices.')
            
            get_input = input
            if sys.version_info[:2] <= (2, 7):
                get_input = raw_input

            user = get_input("Enter a Lab Name: ")
            #compute = get_input("Enter a worker node compute resource: ")
            #price = get_input("Enter the highest price you are willing to pay for a resource: ")

            print("Configuring {}'s Xbow with default settings (Recommended)"
      .format(user))
      
            newfile = open(os.path.expanduser('~/.xbow/settings.yml'), 'w+')

            newfile.write('### USER SPECIFIC SETTINGS ###\n')
            newfile.write('cluster_name: {}\n'.format(user))
            newfile.write('scheduler_name: {}Schd\n'.format(user))
            newfile.write('worker_pool_name: {}Work\n'.format(user))
            newfile.write('shared_file_system: {}FS\n'.format(user))
            newfile.write('creation_token: {}FS\n'.format(user))
            newfile.write('mount_point: /home/ubuntu/shared\n\n')

            newfile.write('### CLUSTER SPECIFIC SETTINGS ###\n')

            newfile.write('region: eu-west-1\n')
            newfile.write("price: '0.15'\n")
            newfile.write('image_id: ami-0e3c951d1401c05fc\n')
            newfile.write('scheduler_instance_type: t2.small\n')
            newfile.write('worker_instance_type: c5.xlarge\n')
            newfile.write('pool_size: 4\n\n')

            newfile.write('### SECURITY SPECIFIC SETTINGS ###\n')
            newfile.write("ec2_security_groups: ['Xbow-SG-ec2c']\n")
            newfile.write("efs_security_groups: ['Xbow-SG-mt']\n")
            newfile.close()

        else:

            print("Settings.yml already exists at '~/.xbow, xbow is skipping "
                  "creating a new one.")

    except IOError:

        print('Xbow failed to create the host configuration file in '
              '"~/.xbow/settings.yml", you will have to do this manually. The '
              'user documentation details the information that should be in this '
              'file.')

def get_image_id(cfg):
    '''
    Find an ami that matches the given data.

    If the cfg dictionary already contains a key 'image_id', then use that,
    otherwise look for the newest ami that matches the 'image_name' filter
    string.
    '''
    if 'image_id' in cfg:
        image_id = cfg['image_id']
    else:
        if not 'image_name' in cfg:
            raise RuntimeError('Error: your .xbow configuration file has neither an image_id or image_name specified')
        client = boto3.client('ec2', region_name=cfg['region'])
        filters=[{'Name': 'manifest-location',
                  'Values': [cfg['image_name']]}]
        result = client.describe_images(Filters=filters)
        images = result['Images']
        if len(images) == 0:
            raise ValueError('Error: cannot find a suitable image matching {}'.format(cfg['image_name']))

        for image in images:
            image['CreationDate'] = datetime.datetime.strptime(image['CreationDate'][:-1], '%Y-%m-%dT%H:%M:%S.%f')
        images_by_age = sorted(images, reverse=True, key=lambda img: img['CreationDate'])
        image_id = images_by_age[0]['ImageId']
    return image_id

def terminate_cluster(region, uid):
    """
    Terminates the cluster given by the name specified in settings.yml
    """
    client = boto3.client('ec2', region_name=region)
    resource = boto3.resource('ec2', region_name=region)

    dsir = client.describe_spot_instance_requests
    response = dsir(Filters=[{'Name': 'launch.key-name', 'Values': [uid]}])
    spot_instance_request_ids = [s['SpotInstanceRequestId']
                                 for s in response['SpotInstanceRequests']
                                ]

    if len(spot_instance_request_ids) > 1:
        print('cancelling all spot requests')
        csir =  client.cancel_spot_instance_requests
        csir(SpotInstanceRequestIds=spot_instance_request_ids, DryRun=False)

    filters = [{'Name': 'key-name', 'Values': [uid]},
               {'Name': 'instance-state-name', 'Values': ['running']}
              ]
    instances = list(resource.instances.filter(Filters=filters))

    if len(instances) == 0:
        raise ValueError('Error - no such cluster')
    else:
        print('Terminating instances')
        for instance in instances:
            instance.terminate(DryRun=False)

        for instance in instances:
            waiter = client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[instance.id])
            
        print('Cluster {} terminated'.format(uid))
