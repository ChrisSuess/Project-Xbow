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

  * sshfs `brew install sshfs` or `apt-get install sshfs`
  * paramiko `pip install paramiko`
  * boto `pip install boto`

### Running Xbow

Xbow is designed to give you the tools to work how you want to.

The recommended steps to using Xbow are as follows:

   1. Launch an instance `xbow-load`
   2. Fuse filesystems `xbow-fuse`
   3. Transfer data `xbow-aim`
   4. Run job `xbow-fire`
   5. Collect data `xbow-collect`
   6. Terminate instance `xbow-kill`

