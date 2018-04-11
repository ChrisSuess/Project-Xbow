Project-Xbow
============

Xbow allows you to create your own custom compute cluster in the cloud. The cluster has a "head' node that you communicate with and can log in to, a number of 'worker' nodes to run your jobs, and a shared file system that links them all together.

Currently Xbow runs only on Amazon Web Services (AWS), and you must have an AWS account set up before you can use Xbow.


Getting and Installing Xbow
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The recommended method to install Xbow is using PyPi::

pip install xbow

or using easy_install

``git clone https://github.com/ChrisSuess/Project-Xbow``

``easy_install setup.py``


Configuring Xbow
~~~~~~~~~~~~~~~~

Before configuring Xbow, you must configure your AWS environment. Follow the instructions here: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html to do that.

Then you can configure Xbow itself, by running the command:

``xbow-configure``

This command creates a directory `$HOME/.xbow` containing a number of files, including `settings.yml` which you can edit at any time in the future to adjust the make-up of your Xbow cluster.


Creating an Xbow Cluster
~~~~~~~~~~~~~~~~~~~~~~~~

To create a new Xbow cluster, run the command:

``xbow-create_cluster``

This command will create the head node, worker nodes, and shared file system according to the specification in your `settings.yml` file.

Using Your Xbow Cluster
~~~~~~~~~~~~~~~~~~~~~~~

Log in to the head node using the command:

``xbow-login_instance``

The simplest way to run jobs on your Xbow cluster is to use the `Xflow` tool. See here for details.

Deleting Your Xbow Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~

Remember that, as a cloud resource, you are paying for your Xbow cluster whether you are using it or not, so once your jobs are finished, you should delete it. Deleting the cluster does NOT delete the shared file system though, so at any time you can create a new Xbow cluster and your data will still be there. 

To delete the cluster give the command:

``xbow-delete_cluster``
