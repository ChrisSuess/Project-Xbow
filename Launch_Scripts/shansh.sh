#!/bin/bash

access_key=$(grep -i aws_access_key_id ~/.aws/credentials | awk '{print $3}')
secret_key=$(grep -i aws_secret_access_key ~/.aws/credentials | awk '{print $3}')

echo $access_key $secret_key
