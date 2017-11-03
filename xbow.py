#!/usr/bin/env python2.7 

import argparse
import boto, boto.ec2, boto.ec2.blockdevicemapping, boto.manage
import paramiko
import os, sys, time, errno
import subprocess

def launch_spot_instance(id, profile, spot_wait_sleep=5, instance_wait_sleep=3):
  ec2 = boto.ec2.connect_to_region(profile['region'])

  if not 'key_pair' in profile:
    profile['key_pair'] = ('XBOW-' + id, 'XBOW-' + id + '.pem')
    try:
      print >> sys.stderr, 'Loading Xbow...',
      keypair = ec2.create_key_pair('XBOW-' + id)
      keypair.save('.')
      print >> sys.stderr, 'Loaded.'
    except boto.exception.EC2ResponseError as e:
      if e.code == 'InvalidKeyPair.Duplicate':
        print >> sys.stderr, 'already loaded.'
      else:
        raise e

  if not 'security_group' in profile:
    try:
      print >> sys.stderr, 'Aiming Xbow...',
      sc = ec2.create_security_group('SG-' + id, 'Security Group for ' + id)
      for proto, fromport, toport, ip in profile['firewall']:
        sc.authorize(proto, fromport, toport, ip)
      profile['security_group'] = (sc.id, sc.name)
      print >> sys.stderr, 'Aimed.'
    except boto.exception.EC2ResponseError as e:
      if e.code == 'InvalidGroup.Duplicate':
        print >> sys.stderr, 'already aimed.'
        sc = ec2.get_all_security_groups(groupnames=['SG-' + id])[0]
        profile['security_group'] = (sc.id, sc.name)
      else:
        raise e

  existing_requests = ec2.get_all_spot_instance_requests(filters={'launch.group-id': profile['security_group'][0], 'state': ['open', 'active']})
  if existing_requests:
    if len(existing_requests) > 1:
      raise Exception('Too many existing spot requests')
    print >> sys.stderr, 'Reusing existing spot request'
    spot_req_id = existing_requests[0].id
  else:
    bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
    bdm['/dev/sda1'] = boto.ec2.blockdevicemapping.BlockDeviceType(volume_type='gp2', size=profile['disk_size'], delete_on_termination=profile['disk_delete_on_termination'])
    bdm['/dev/sdb'] = boto.ec2.blockdevicemapping.BlockDeviceType(ephemeral_name='ephemeral0')
    print >> sys.stderr, 'Ready to Fire'
    spot_reqs = ec2.request_spot_instances(
      price=profile['price'], image_id=profile['image_id'], instance_type=profile['type'], placement=profile['region'] + profile['availability_zone'],
      security_groups=[profile['security_group'][1]], key_name=profile['key_pair'][0], block_device_map=bdm)
    spot_req_id = spot_reqs[0].id

  print >> sys.stderr, 'Firing Xbow',
  instance_id = None
  spot_tag_added = False
  while not instance_id:
    spot_req = ec2.get_all_spot_instance_requests(request_ids=[spot_req_id])[0]
    if not spot_tag_added:
      spot_req.add_tag('Name', id)
      spot_tag_added = True
    if spot_req.state == 'failed':
      raise Exception('Spot request failed')
    instance_id = spot_req.instance_id
    if not instance_id:
      print >> sys.stderr, '.',
      time.sleep(spot_wait_sleep)
  print >> sys.stderr

  print >> sys.stderr, 'Retrieving instance by id'
  reservations = ec2.get_all_instances(instance_ids=[instance_id])
  instance = reservations[0].instances[0]
  instance.add_tag('Name', id)
  print >> sys.stderr, 'Got instance: ' + str(instance.id) +  ' [' + instance.state + ']'
  print >> sys.stderr, 'Waiting for instance to boot',
  while not instance.state in ['running', 'terminated', 'shutting-down']:
    print >> sys.stderr, '.',
    time.sleep(instance_wait_sleep)
    instance.update()
  print >> sys.stderr
  if instance.state != 'running':
    raise Exception('Instance was terminated')
  return instance

def connect_to_instance(ip, username, key_filename, timeout=10):
  print >> sys.stderr, 'Connecting to SSH [' + ip + '] ',
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  retries = 0
  while retries < 30:
    try:
      print >> sys.stderr, '.',
      client.connect(ip, username=username, key_filename=key_filename, timeout=timeout)
      break
    except:
      retries += 1
  print >> sys.stderr
  return client

def setup_instance(id, instance, file, user_name, key_name):
  script = open(file, 'r').read().replace('\r', '')

  client = connect_to_instance(instance.ip_address, user_name, key_name)
  session = client.get_transport().open_session()
  session.set_combine_stderr(True)

  print >> sys.stderr, 'Running script: ' + os.path.relpath(file, os.getcwd())
  session.exec_command(script)
  stdout = session.makefile()
  try:
    for line in stdout:
      print line.rstrip()
  except (KeyboardInterrupt, SystemExit):
    print >> sys.stderr, 'Ctrl-C, stopping'
  client.close()
  exit_code = session.recv_exit_status()
  print >> sys.stderr, 'Exit code: ' + str(exit_code)
  return exit_code == 0

#def terminate_instance()

if __name__ == '__main__':
 
  profiles = {
    'Default': {
      'region': 'eu-west-1',
      'availability_zone': 'a',
      'price': '0.03',
      'type': 'm4.large',
      'image_id': 'ami-9d8421e4',
      'username': 'ubuntu',
      #'key_pair': ('AWS-EU', 'eu-key.pem'),
      'disk_size': 20,
      'disk_delete_on_termination': True,
      'scripts': [],
      'firewall': [ ('tcp', 22, 22, '0.0.0.0/0') ]
    },
    'Gromacs': {
      'region': 'eu-west-1',
      'availability_zone': 'a',
      'price': '0.03',
      'type': 'm4.large',
      'image_id': 'ami-9d8421e4',
      'username': 'ubuntu',
      #'key_pair': ('AWS-EU', 'eu-key.pem'),
      'disk_size': 20,
      'disk_delete_on_termination': True,
      'scripts': [],
      'firewall': [ ('tcp', 22, 22, '0.0.0.0/0') ]
    },
    'Amber': {
      'region': 'eu-west-1',
      'availability_zone': 'a',
      'price': '0.03',
      'type': 'm4.large',
      'image_id': 'ami-9d8421e4',
      'username': 'ubuntu',
      #'key_pair': ('AWS-EU', 'eu-key.pem'),
      'disk_size': 20,
      'disk_delete_on_termination': True,
      'scripts': [],
      'firewall': [ ('tcp', 22, 22, '0.0.0.0/0') ]
    }
  }
  
  parser = argparse.ArgumentParser(description='Launch spot instance')
  parser.add_argument('-n', '--name', help='Name', required=True)
  parser.add_argument('-p', '--profile', help='Profile', default=profiles.keys()[0], choices=profiles.keys())
  parser.add_argument('-s', '--script', help='Script path', action='append', default=[])
  parser.add_argument('-i', '--interactive', help='Connect to SSH', action='store_true')
  parser.add_argument('-f', '--fuse', help='Shows command to Fuse client with EC2', action='store_true')
  parser.add_argument('-a', '--aim', help='Transfers data from client with EC2', action='store_true')
  parser.add_argument('-c', '--collect', help='Collects data simulation', action='store_true')
  parser.add_argument('-r', '--ready', help='Check if instance is ready', action='store_true')
  parser.add_argument('-t', '--terminate', help='Terminates Instance', action='store_true')
  args = parser.parse_args()

  profile = profiles[args.profile]
  cwd = os.getcwd()
  file_path = cwd + "/.mount"
  base = os.path.basename(cwd)

  try:
    instance = launch_spot_instance(args.name, profile)
  except boto.exception.NoAuthHandlerFound:
    print >> sys.stderr, 'Error: No credentials found, try setting the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables'
    sys.exit(1)

  for script in profile['scripts'] + args.script:
    if not setup_instance(id=args.name, instance=instance, file=script, user_name=profile['username'], key_name=profile['key_pair'][1]):
      break

  if args.interactive:
    print 'ssh ' + profile['username'] + '@' + instance.ip_address + ' -i ' + profile['key_pair'][1] + ' -oStrictHostKeyChecking=no'

  if args.fuse:
    print 'Fusing file systems'
    try:
        os.mkdir(file_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    subprocess.call('sshfs ' + profile['username'] + '@' + instance.dns_name + ':/home/ubuntu/ ' + file_path + ' -o IdentityFile=' + cwd + '/' + profile['key_pair'][1] + ' -o allow_other -oStrictHostKeyChecking=no', shell=True)

  if args.aim:
    print 'Transfering data to the cloud'
    subprocess.call('rsync -avz -e "ssh -i ' + profile['key_pair'][1] + '" ' + cwd + '/* ' +  profile['username'] + '@' + instance.dns_name + ':/home/ubuntu/' + base, shell=True)

  if args.collect:
    print 'Collecting Data'
    subprocess.call('rsync -avz -e "ssh -i ' + profile['key_pair'][1] + '" ' + profile['username'] + '@' + instance.dns_name + ':/home/ubuntu/' + base + '/* ' + cwd + '/', shell=True) 

  if args.ready:
    ami = instance.id
    ec2 = boto.ec2.connect_to_region(profile['region'])
    existing_instances = ec2.get_all_instance_status(instance_ids=ami)
    print 'Checking if the instance: ' + ami + ' is ready'
    print 'When both systems checks are ok Xbow is ready to fire!'
    for instance in existing_instances:
      print 'System Status is: ' + instance.system_status.status + '\n' + 'Instance Status is: ' + instance.instance_status.status

  if args.terminate:
    instance = instance.id
    print 'Terminating the instance: ' + instance
    ec2 = boto.ec2.connect_to_region(profile['region'])
    ec2.terminate_instances(instance_ids=instance)
