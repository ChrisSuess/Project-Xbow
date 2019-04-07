import boto3
import time

def fs_id_from_name(name, region=None):
    """
    Given a file system name, return the file system ID.

    Returns None if there is no such file system in the region
    """

    fs_id = None
    efs_client = boto3.client('efs', region_name=region)

    dfs = efs_client.describe_file_systems
    response = dfs(CreationToken=name)['FileSystems']
    if len(response) > 0:
        fs_id = response[0]['FileSystemId']
    return fs_id

def create_fs(name, region=None, efs_security_groups=None):
    """
    Create a file system with the requested name in the chosen region.

    Returns the file system ID
    """

    fs_id = fs_id_from_name(name)
    if fs_id is not None:
        return fs_id

    efs_client = boto3.client('efs', region_name=region)
    ec2_resource = boto3.resource('ec2', region_name=region)

    cfs = efs_client.create_file_system
    response = cfs(CreationToken=name, Encrypted=True)
    fs_id = response['FileSystemId']

    create_tag = efs_client.create_tags(
            FileSystemId = response['FileSystemId'],
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            )

    time.sleep(5)

    subnets = ec2_resource.subnets.all()
    sgf = ec2_resource.security_groups.filter
    security_groups = sgf(GroupNames=efs_security_groups)
    efs_security_groupid = [security_group.group_id
                            for security_group in security_groups]

    response = efs_client.describe_mount_targets(FileSystemId=fs_id)
    mount_targets = response["MountTargets"]
    if len(mount_targets) == 0:
        for subnet in subnets:
            cmt = efs_client.create_mount_target
            cmt(FileSystemId=fs_id,
                SubnetId=subnet.id,
                SecurityGroups=efs_security_groupid
               )

    time.sleep(5)
    response = efs_client.describe_mount_targets(FileSystemId=fs_id)
    mount_targets = response["MountTargets"]
    ready = all([m['LifeCycleState'] == 'available' for m in mount_targets])

    while not ready:
        time.sleep(5)
        response = efs_client.describe_mount_targets(FileSystemId=fs_id)
        mount_targets = response["MountTargets"]
        ready = all([m['LifeCycleState'] == 'available' for m in mount_targets])

    return fs_id

def delete_fs(name, region=None):
    """
    Delete the named filesystem.
    """
    efs_client = boto3.client('efs', region_name=region)
    fs_id = fs_id_from_name(name, region=region)
    efs_client.delete_file_system(FileSystemId = fs_id)

def delete_mount_targets(name, region=None):
    """
    Delete the mount targetss associated with a filesystem.
    """
    efs_client = boto3.client('efs', region_name=region)
    fs_id = fs_id_from_name(name, region=region)
    dmt = efs_client.describe_mount_targets
    mount_targets = dmt(FileSystemId=fs_id).get('MountTargets', [])
    for mount_target in mount_targets:
        mount_target_id = mount_target['MountTargetId']
        efs_client.delete_mount_target(MountTargetId=mount_target_id)
