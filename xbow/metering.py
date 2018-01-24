import boto3
import datetime
import xbow

class SpotMeter(object):
    """
    APPROXIMATE cost meter for a spot instance.
    """
    def __init__(self, instance_type, availability_zone, count = 1):
        """
        initialise the meter.

        Args:
            instance_type (str): The EC2 instance type
            availability_zone (str): The EC2 availability zone
            count (int): The number of instances - multiplier for all costs
        """
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
        """
        Get the current spot price.
        The value is for *count* instances of type *instance_type* in
        availability zone *availability_zone*.

        Returns:
            price (float): The current spot price in US dollars per hour.
        """

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
        """
        Total cost since the meter was started

        Returns:
            cost (float): The total cost in US dollars.
        """
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
        """
        Total time (in hours) the meter has been running.

        Returns:
            time (float): total time in hours.
        """
        period = datetime.datetime.now(self.tz) - self.start_time
        return period.seconds / 3600.0
