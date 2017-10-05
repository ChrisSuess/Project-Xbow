s3fs gromacs . -o passwd_file=~/.aws/passwd_s3fs

sudo sshfs ubuntu@ec2-54-171-179-57.eu-west-1.compute.amazonaws.com:/home/ubuntu/gromacs ~/Xbow/Mountpoint/TEST/ -o IdentityFile=~/Xbow/XBOW-DEMO.pem -o allow_other
