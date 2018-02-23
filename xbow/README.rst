Project-Xbow
============

Xbow has been built to mirror the elasticity of cloud computing. It
provides an easy interface to the cloud but remains incredibly flexible
allowing you to run your science how you like it.

Using Xbow
----------

The following steps assumes your cloud account is set up to work
from the command line. For information on getting AWS to work
from the command line see the section "Setting up AWS" below.

Getting and Installing Xbow
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The recommended method to install Xbow is using PyPi

``pip install xbow``

or using easy_install

``git clone https://github.com/ChrisSuess/Project-Xbow``

``easy_install setup.py``


Running Xbow
~~~~~~~~~~~~

Xbow is designed to give you the tools to set up a cluster in the
cloud.

1. Configure Xbow ``xbow-configure``
2. Launch Xbow ``xbow-create_cluster``
3. Login to Xbow ``xbow-login_instance``
4. Stop Xbow ``xbow-delete_cluster``

Xbowflow is then used in order to run simulations.


Setting up AWS
~~~~~~~~~~~~~~

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

