import boto3
import datetime

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

