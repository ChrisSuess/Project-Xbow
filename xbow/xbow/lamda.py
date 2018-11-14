from __future__ import print_function
import json
import boto3
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

print('INFO: Loading function')

DRY_RUN = True  # Do not send e-mail, or shut down instances

MAIL_AFTER_DAYS = 3
SHUTDOWN_AFTER_DAYS = 6
THRESHOLD = 1  # cpu percent
EXCLUDE_TAG = 'AutoStopPreventedBy'  # Case insensitive
#MAIL_FROM = 'christian.suess1@nottingham.ac.uk'
#MAIL_TO = 'christian.suess1@nottingham.ac.uk'
#MAIL_TEXT = '''
#The following instances where inactive for the last %(days)s days. and will be shut down in
#%(deadline)s days. Please use them, or tag them with the key %(tag)s and your name as the value
#to prevent this. \n\n %(instances)s
#'''
ASG_TAG = 'aws:autoscaling:groupName' # This is always added by AWS for autoscaling groups

ec2 = boto3.client('ec2')
cw = boto3.client('cloudwatch')
ses = boto3.client('ses')

def lambda_handler():

    if DRY_RUN:
        print('INFO: running in Dry Run mode, no action will be taken')

    now = datetime.now(tzlocal()) 
    now = now - timedelta(seconds=now.second, microseconds=now.microsecond)
    # round down to the nearest minute, just like cloudwatch
    # starttime = now - timedelta(days=SHUTDOWN_AFTER_DAYS)
    starttime = now - timedelta(minutes=15) # check 15 last minutes for cpu activity

    # Create empty variables
    stop_instances = []
    spot = []
    mail_instances = []
    active_instances = []
    skipped_instances = []
    asg_instances = []

    # Return only instances in launch group (worker name settings.yml)

    describe_response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:name', 'Values': [name]},
            {'Name': 'instance-state-name', 'Values': ['running']},
        ]
    )

    for reservation in describe_response['Reservations']:
        # Build the dimensions from the instances
        for instance in reservation['Instances']:

            instance_id = instance['InstanceId']
            sir = instance['SpotInstanceRequestId']
            
            # Get statistics from cloudwatch
            statistics_response = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=starttime,
                EndTime=now + timedelta(minutes=2),  # Add 2 minutes to compensate rounding
                Period=60 * 60 * 24,  # time period to evaluate in seconds
                Statistics=['Maximum'],
            )

            # Default - Not active between now and shutdown threshold
            stop = True
            mail = True
            
            for datapoint in statistics_response['Datapoints']:
                if datapoint['Maximum'] > THRESHOLD:
                    timestamp = datapoint['Timestamp']
                    if timestamp >= now - timedelta(days=MAIL_AFTER_DAYS):
                        # Active between now and mail threshold
                        stop = False
                        mail = False
                    elif timestamp >= now - timedelta(days=SHUTDOWN_AFTER_DAYS):
                        # Active between mail threshold and shutdown threshold
                        stop = False

            if stop:
                spot.append(sir)
                stop_instances.append(instance_id)
            elif mail:
                mail_instances.append(instance_id)
            else:
                active_instances.append(instance_id)

    """
    #Work in progress
    if not DRY_RUN and len(mail_instances) > 0:
        mail_response = ses.send_email(
            Source=MAIL_FROM,
            Destination={
                'ToAddresses': [MAIL_TO]
            },
            Message={
                'Subject': {
                    'Data': 'EC2 instances will be shut down',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': MAIL_TEXT % {
                            'days': MAIL_AFTER_DAYS,
                            'deadline': SHUTDOWN_AFTER_DAYS - MAIL_AFTER_DAYS,
                            'tag': EXCLUDE_TAG,
                            'instances': '\n'.join(mail_instances)
                        },
                        'Charset': 'UTF-8',
                    }
                }
            }
        )

        print('INFO: mail sent with id %s' % mail_response['MessageId'])
    """

    if not DRY_RUN and len(stop_instances) > 0:
        #print("Terminating Idle Worker... it won't be back")
        ec2_client.cancel_spot_instance_requests(SpotInstanceRequestIds=spot, DryRun=False)
        ec2.terminate_instances(InstanceIds=stop_instances, DryRun=False)

    print(json.dumps({
        'skipped': skipped_instances,
        'autoscaling': asg_instances,
        'active': active_instances,
        'mail': mail_instances,
        'stop': stop_instances,
        'stop-spot': spot
    }))
