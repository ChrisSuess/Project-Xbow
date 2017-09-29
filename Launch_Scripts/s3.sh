#!/bin/bash

export AWS=`curl -s -m 1 http://169.254.169.254/latest/meta-data/instance-id 2> /dev/null`
export AWS_ACCESS_KEY_ID="AKIAIZAZUVG5ANPP774Q"
export AWS_SECRET_ACCESS_KEY="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"

sudo apt-get install -y python-pip
sudo pip install awscli
[ "$AWS_ACCESS_KEY_ID" ] && [ "$AWS_SECRET_ACCESS_KEY" ] && echo -e "$AWS_ACCESS_KEY_ID\n$AWS_SECRET_ACCESS_KEY\n\n" | aws configure

aws s3 sync s3://gromacs gromacs
