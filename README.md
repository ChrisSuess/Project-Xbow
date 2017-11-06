# Project-Xbow

Xbow has been built to mirror the elasticity of cloud computing. It provides an easy interface to the cloud but remains incredibly flexible allowing you to run your science how you like it. 


## Using Xbow

Xbow currently makes use of Amazon Web Services (AWS). If you have never run AWS from the command line an additional configuration step is necessary. If this is already setup you can ignore this step!

   1. Make the directory: `mkdir /home/$USER/.aws/`
   2. Create a file:  `touch /home/$USER/.aws/credentials`
   3. Add access and secret access keys to: `/home/$USER/.aws/credentials`

	[default]
	aws_access_key_id = YOUR_ACCESS_KEY
	aws_secret_access_key = YOUR_SECRET_ACCESS_KEY

   4. Change file permissions of this file for security:  `chmod 400 /home/$USER/.aws/credentials`

 **IMPORTANT: NEVER MAKE THIS VISIBLE OR SHARE THIS INFORMATION!!!** 

### Installing and Configuriing Xbow

Update: pip install or conda package?

#### Prerequisites

Xbow is being developed to work out of the box. For now, the following are currently necessary to be installed before using Xbow.

  * paramiko `pip install paramiko --user`
    * Currently if using Ubuntu installing via pip can fail if this happens use `apt-get install python-paramiko`   
  * boto `pip install boto --user`

### Getting Xbow

`git clone https://github.com/ChrisSuess/Project-Xbow`

### Running Xbow

Xbow is designed to give you the tools to work how you want to.

The recommended steps to using Xbow are as follows:

   1. Load an instance `python xbow.py -n $NAME_OF_JOB`
   2. Check if instance is ready (instances can take several minutes to boot!) `python xbow.py -n $NAME_OF_JOB -r`
   3. Transfer (aim) data from client to cloud `python xbow.py -n $NAME_OF_JOB -a`
   4. Fire job using a bash script `python xbow.py -n $NAME_OF_JOB -s $SCRIPT_NAME`
   5. Collect data from cloud to client `python xbow.py -n $NAME_OF_JOB -c`
   6. Terminate instance `python xbow.py -n $NAME_OF_JOB -t`

   A. To interact directly with the cloud instance `python xbow.py -n $NAME_OF_JOB -i`

### Example

   1. `cd Xbow/Example`
   2. `python ../xbow.py -n TestSim`
   3. `python ../xbow.py -n TestSim -r`
   4. `python ../xbow.py -n TestSim -a`
   5. `python ../xbow.py -n TestSim -s launch_instructions.sh`
   6. `python ../xbow.py -n TestSim -c`
   7. `python ../xbow.py -n TestSim -t`

