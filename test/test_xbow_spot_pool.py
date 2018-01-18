import unittest
from xbow import xbow

class TestSpotPoolMethods(unittest.TestCase):

    def test_spot_pool_methods1(self):

        region = 'eu-west-1'
        price = '0.4'
        instance_type = 'm4.large'
        image_id = 'ami-117de368' # new image created 16th Jan
        ec2_security_groups = ['efs-walkthrough1-ec2-sg']
        efs_security_groups = ['efs-walkthrough1-mt-sg']
        shared_file_system = 'MyTestFileSystem'
        mount_point = '/home/ubuntu/shared'
        sip = xbow.SpotInstancesPool(count=2,
                        launch_group='TestLaunchGroup',
                        price=price,
                        image_id=image_id,
                        instance_type=instance_type,
                        shared_file_system=shared_file_system,
                        mount_point=mount_point,
                        security_groups=ec2_security_groups,
                        )
        self.assertEqual(sip.status, 'ready')

    def test_spot_pool_methods2(self):
        sip = xbow.SpotInstancesPool(launch_group='TestLaunchGroup')
        self.assertEqual(sip.status, 'ready'),
        sip.terminate()
        sip.update()
        self.assertEqual(sip.status, 'unavailable'),
