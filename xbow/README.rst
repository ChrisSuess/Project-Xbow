Project-Xbow
============

**Xbow** allows you to create your own custom compute cluster in the cloud. The cluster has a "head' node that you communicate with and can log in to, a number of 'worker' nodes to run your jobs, and a shared file system that links them all together.

Currently **Xbow** runs only on Amazon Web Services (AWS), and you must have an AWS account set up before you can use **Xbow**.


Getting and Installing **Xbow**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The recommended method to install **Xbow** is using pip::

    pip install xbow

but if you prefer you can use easy_install::

    git clone https://github.com/ChrisSuess/Project-Xbow
    easy_install setup.py


Configuring **Xbow**
~~~~~~~~~~~~~~~~~~~~~

Before configuring **Xbow**, you must configure your AWS environment. Follow the instructions `here <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html>`_ to do that.


Then you can configure **Xbow** itself, by running the command::

    xbow-configure

This command creates a directory ``$HOME/.xbow`` containing a number of files, including ``settings.yml`` which you can edit at any time in the future to adjust the make-up of your **Xbow** cluster.

Creating an Xbow Filesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If this is the first time you have used **Xbow** you will need to create a shared filesystem for use with **Xbow**. This is done by running the command::

    xbow-create_filesystem

This only needs to be performed once and **Xbow** handles all the configuration settings.

Creating an **Xbow** Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a new **Xbow** cluster, run the command::

    xbow-create_cluster

This command will create the head node, worker nodes, and shared file system according to the specification in your ``settings.yml`` file.

Using Your **Xbow** Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Log in to the head node using the command::

    xbow-login_instance

The simplest way to run jobs on your **Xbow** cluster is to use the **Xflow** tool. See `here <https://github.com/ChrisSuess/Project-Xbow/wiki/An-Introduction-to-Xbowflow-Workflows>`_ for details.

Transferring Data to your **Xbow** Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Xbow** treats data as *buckets* and syncs the working directory with the cluster.

To **Sync** data between your machine and your **Xbow** cluster use the command::

    xbow-sync

Deleting Your **Xbow** Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Remember that, as a cloud resource, you are paying for your **Xbow** cluster whether you are using it or not, so once your jobs are finished, you should delete it. Deleting the cluster does NOT delete the shared file system though, so at any time you can create a new **Xbow** cluster and your data will still be there. 

To delete the entire cluster::

    xbow-delete_cluster

To delete the workers and keep the head node alive use the command::

    xbow-delete_workers

Running an Example **Xbow** Job
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Download an example from the link below::

``curl https://raw.githubusercontent.com/ChrisSuess/Project-Xbow/devel/xbowflow/examples.tgz -o examples.tgz``

#. This has downloaded a compressed file featuring several examples. To uncompress this::

``tar -xvf examples.tgz``

This should create a new folder called *examples*. For this example we are going to use the files in the folder *SimpleJobs*.

``cd examples/SimpleJobs``

#. Now we must create our **Xbow** environment.

If this is the first time using **Xbow** you need to create a filesystem.

``xbow-create_filesystem``

If a filesystem already exists **Xbow** will detect this.

Next we need to create the **Xbow** cluster.

``xbow-create_cluster``

#. Navigate to the directory containing the example files. Sync the data with **Xbow** cluster::

``xbow-sync``

#. Login to your **Xbow** cluster::

``xbow-login``

#. Navigate to the directory containing the example files::

``cd shared/$Example_files``

#. Using **Xflow** run the example::

``xflow-exec csh run.dhfr`` 

#. Log off **Xbow** cluster::

``ctrl + d``

#. Sync the data back from the **Xbow** cluster::

``xbow-sync``

#. Delete the cluster::

``xbow-delete_cluster``
