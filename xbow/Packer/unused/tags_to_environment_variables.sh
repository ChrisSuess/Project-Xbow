#!/bin/sh
######
# Author: Marcello de Sales (marcello.desales@gmail.com)
# Description: Create Create Environment Variables in EC2 Hosts from EC2 Host Tags
# 
### Requirements:  
# * Install jq library (sudo apt-get install -y jq)
# * Install the EC2 Instance Metadata Query Tool (http://aws.amazon.com/code/1825)
#
### Installation:
# * Add the Policy EC2:DescribeTags to a User
# * aws configure
# * Souce it to the user's ~/.profile that has permissions
#### 
# Add tags to an EC2 host or Image Profile
# Reboot and verify the result of $(env).

# Loads the Tags from the current instance
getInstanceTags () {
  # http://aws.amazon.com/code/1825 EC2 Instance Metadata Query Tool
  INSTANCE_ID=$(/usr/local/bin/ec2-metadata -i | awk '{print $2}')
  REGION=$(/usr/local/bin/ec2-metadata -z | awk '{print substr($2, 1, length($2)-1)}')

  # Describe the tags of this instance
  aws ec2 describe-tags --region $REGION --filters "Name=resource-id,Values=$INSTANCE_ID"
}

# Convert the tags to environment variables.
# Based on https://github.com/berpj/ec2-tags-env/pull/1
mkdir -p /run/metadata
tags_to_env () {
    tags=$1

    for key in $(echo $tags | /usr/bin/jq -r ".[][].Key"); do
        value=$(echo $tags | /usr/bin/jq -r ".[][] | select(.Key==\"$key\") | .Value")
        key=$(echo $key | /usr/bin/tr '-' '_' | /usr/bin/tr '[:lower:]' '[:upper:]')
        echo "Exporting $key=$value"
        export $key="$value"
        echo "$key=$value" >> /run/metadata/xbow
    done
}

# Execute the commands
instanceTags=$(getInstanceTags)
tags_to_env "$instanceTags"
