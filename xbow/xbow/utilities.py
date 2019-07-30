'''
utilities.py: basic functions to launch, connect to, and delete an instance.
'''
import boto3
import uuid
import datetime
import os

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

def launch(dirname, region, uid, image_id, instance_type):
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
                                         SecurityGroupIds=[security_group_id], 
                                         ClientToken=str(uuid.uuid4()),
                                         InstanceMarketOptions={'MarketType': 'spot'}
                                        )
    instance = instances[0]
    #waiter = client.get_waiter('instance_status_ok')
    #waiter.wait(InstanceIds=[instance.instance_id])
    #instance.reload()
    return instance.instance_id

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
