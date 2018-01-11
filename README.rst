Project-Xbow
============

Xbow has been built to mirror the elasticity of cloud computing. It
provides an easy interface to the cloud but remains incredibly flexible
allowing you to run your science how you like it.

Using Xbow
----------

Xbow currently makes use of Amazon Web Services (AWS). If you have never
run AWS from the command line an additional configuration step is
necessary. If this is already setup you can ignore this step!

When communicating with cloud resources a user must use access keys. The
Access Key and the Secret Access Key are not your standard user name and
password, but are special tokens that allow our services to communicate
with your AWS account by making secure REST or Query protocol requests
to the AWS service API.

To find your Access Key and Secret Access Key:

1. Log in to your AWS Management Console.
2. Click on your user name at the top right of the page.
3. Click on the Security Credentials link from the drop-down menu.
4. Find the Access Credentials section, and copy the latest Access Key
   ID.
5. Click on the Show link in the same row, and copy the Secret Access
   Key.

Then in your terminal:

6. Make the directory: ``mkdir /home/$USER/.aws/``
7. Create a file: ``touch /home/$USER/.aws/credentials``
8. Add access and secret access keys to:
   ``/home/$USER/.aws/credentials``

::

    [default]
    aws_access_key_id = YOUR_ACCESS_KEY
    aws_secret_access_key = YOUR_SECRET_ACCESS_KEY

9. Change file permissions of this file for security:
   ``chmod 400 /home/$USER/.aws/credentials``

Make sure there is no blank space at the end of each line.

**IMPORTANT: NEVER MAKE THIS VISIBLE OR SHARE THIS INFORMATION!!!**

Installing and Configuriing Xbow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Update: pip install or conda package?

Prerequisites
^^^^^^^^^^^^^

Xbow is being developed to work out of the box. For now, the following
are currently necessary to be installed before using Xbow.

-  paramiko ``pip install paramiko --user``

   -  Currently if using a Linux distro (Ubuntu/centOS) is is necessary
      to ``pip install python-gssapi --user``

-  boto ``pip install boto --user``

Getting Xbow
~~~~~~~~~~~~

``git clone https://github.com/ChrisSuess/Project-Xbow``

Running Xbow
~~~~~~~~~~~~

Xbow is designed to give you the tools to work how you want to.

The recommended steps to using Xbow are as follows:

1. Load an instance ``python xbow.py -n $NAME_OF_JOB``
2. Check if instance is ready (instances can take several minutes to
   boot!) ``python xbow.py -n $NAME_OF_JOB -r``
3. Transfer (aim) data from client to cloud
   ``python xbow.py -n $NAME_OF_JOB -a``
4. Fire job using a bash script
   ``python xbow.py -n $NAME_OF_JOB -s $SCRIPT_NAME``
5. Collect data from cloud to client
   ``python xbow.py -n $NAME_OF_JOB -c``
6. Terminate instance ``python xbow.py -n $NAME_OF_JOB -t``

A. To interact directly with the cloud instance
``python xbow.py -n $NAME_OF_JOB -i``

Example
~~~~~~~

1. ``cd Xbow/Example``
2. ``python ../xbow.py -n TestSim``
3. ``python ../xbow.py -n TestSim -r``
4. ``python ../xbow.py -n TestSim -a``
5. ``python ../xbow.py -n TestSim -s launch_instructions.sh``
6. ``python ../xbow.py -n TestSim -c``
7. ``python ../xbow.py -n TestSim -t``

