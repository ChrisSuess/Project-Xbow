# Project-Xbow

Xbow has been built to mirror the elasticity of cloud computing. It provides an easy interface to the cloud but remains incredibly flexible allowing you to run your science your way.

## Using Xbow

Xbow currently makes use of Amazon Web Services (AWS). If you have never run AWS from the command line an additional configuration step is necessary. If this is already setup you can ignore this step!

   1. Make the directory: "/home/$USER/.aws/"
   2. Create a file:  "credentials"
   3. Change file permissions of this file for security:  "chmod 400 credentials"  
   4. Add:

	[default]
	aws_access_key_id = 
	aws_secret_access_key =

   5. Add access and secret access keys

 **IMPORTANT: NEVER MAKE THIS VISIBLE OR SHARE THIS INFORMATION!!!** 

### Installing Xbow

Update: pip install or conda package?

### Running Xbow

#### To launch an instance: 

    $ python xbow.py -n NAME_OF_JOB -p AWS

Instances take several moments to bootup so user must wait until it is ready to accept jobs.

#### To run a script on instance: 

    $ python xbow.py -n NAME_OF_JOB -p AWS -s SCRIPT_NAME

#### To get SSH details of instance: 

    $ python xbow.py -n NAME_OF_JOB -p AWS -i

#### To Fuse Local and AWS HDD and copy files add -f

#### To collect data add -c

#### To terminate instance add -t 
