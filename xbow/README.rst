Project-Xbow
============

**Xbow** allows you to create your own custom compute cluster in the cloud. The cluster has a "head' node that you communicate with and can log in to, a number of 'worker' nodes to run your jobs, and a shared file system that links them all together.
See `Xbow Architecture <https://github.com/ChrisSuess/Project-Xbow/tree/xbow-lab/xbow#xbow-architecture>`_ for more details.

Currently **Xbow** runs only on Amazon Web Services (AWS), and you must have an AWS account set up before you can use **Xbow**. Follow the instructions `here <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html>`_ to do that. Once you have reached the point where you have a ``$HOME/.aws`` folder containing a ``config`` and ``credentials`` file you are ready to use **Xbow**!

Getting and Installing **Xbow**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The recommended method to install **Xbow** is using pip::

    pip install xbow

Using **Xbow** and Building your Lab
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to boot a **Xbow** Cluster run the command::

    xbow lab

If this is the first time you have run **Xbow** then it will first configure **Xbow** and get everything ready to build your lab. 
This command creates a directory ``$HOME/.xbow`` containing a number of files, including ``settings.yml`` which you can edit at any time in the future to adjust the make-up of your **Xbow** cluster. See the section **Xbow** `settings <https://github.com/ChrisSuess/Project-Xbow/tree/xbow-lab/xbow#xbow-settings-file>`_ file for more info on this. As part of the configuration step the ``xbow lab`` command will create a shared filesystem in the 'cloud' which will be attached
to every cloud resource you boot up. It also creates temporary credential files which allow you to login to your resources.
After all these checks have been done it creates a head node ready for you to use your lab.

Using **Xbow:Lab**
~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are several ways to use your **Xbow:Lab** which have been designed to accomadate most users needs:

- `Xbow:Portal <https://github.com/ChrisSuess/Project-Xbow/tree/xbow-lab/xbow#xbowportal>`_. A Browser based GUI that allows you to submit your jobs to your **Xbow:Lab**
- `Xbow:Note <https://github.com/ChrisSuess/Project-Xbow/tree/xbow-lab/xbow#xbownote>`_. A Jupyter Notebook running on your **Xbow:Lab**
- `Xbow:Flow <https://github.com/ChrisSuess/Project-Xbow/tree/xbow-lab/xbow#xbowflow>`_. A tool to allow you to run your jobs that makes use of the workflow language **xbowflow**. **Xbow:Flow** can be run on your local workstation or remotely using **Xbow:Login**  
- `Xbow:Login <https://github.com/ChrisSuess/Project-Xbow/tree/xbow-lab/xbow#xbowlogin>`_. A simple way to login to your **Xbow:Lab** and run your jobs using **Xbow:Flow**

**Xbow:Portal**
~~~~~~~~~~~~~~~~~

**Xbow:Portal** creates a browser based GUI. To start this::

    xbow portal

.. image:: pics/XbowPortal.png
    :height: 20px

Using **Xbow:Portal** allows you to monitor the progress of your jobs, view and download output files, or check your cluster status from other devices such as Tablets and Mobile phones.

**Xbow:Note**
~~~~~~~~~~~~~~~~~

**Xbow:Note** is a Jupyter Notebook running on your **Xbow:Lab**. To start your notebook::

    xbow note

**Xbow:Flow**
~~~~~~~~~~~~~~~~

**Xbow** has been designed to require you to make minimal changes to the way you are used to running jobs on your local machine. Running jobs using **Xbow** can be as simple as the following example::

If your local job runs like this::

    executable -a arg1 -b arg2 -c arg3

Simply change it to::

    xbow flow executable -a arg1 -b arg2 -c arg3

Running this **Xbow:Flow** command will:

- Boot a worker/workers
- Transfer your data to your **Xbow:Lab**
- Run your simulation
- Shut your worker/workers down
- Bring your data back to your local resource (if you want it to!)

By default the command ``xbow flow`` will use the specifications in the ``~/.xbow/settings.yml`` file. These can be overridden by adding the flags:

-c   type of compute resource eg. p2.xlarge
-n   number of workers
--max-cost   the maximum cost you are willing to spend on your job   

**Xbow:Flow** uses the workflow language **Xbowflow** which allows you to run more complex jobs and workflows using the **Xflow** tool. See `here <https://github.com/ChrisSuess/Project-Xbow/wiki/An-Introduction-to-Xbowflow-Workflows>`_ for more details.

**Xbow:Login**
~~~~~~~~~~~~~~~~~~

Using **Xbow:Lab** can be done entirely remotely but if you prefer to work directly on the head node this is possible with the command::

    xbow login

All your jobs can be run using the same commands from **Xbow:Flow**. As you are on the head node it is assumed all your data is already here so no data staging is done.

**Xbow:Status**
~~~~~~~~~~~~~~~~~~

**Xbow** file transfer
~~~~~~~~~~~~~~~~~~~~~~

Transferring data back and forth to remote machines can sometimes be awkward. **Xbow** has upload and download commands make this easier::

    xbow upload 

and:: 

    xbow download

Closing your **Xbow:Lab**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Remember that, as a cloud resource, you are paying for your **Xbow** cluster whether you are using it or not. **Xbow** will always shut idle machines down in order keep all costs to a minimum. However there are still some minimal costs. If you are finished using **Xbow** and want to completely clear your cloud footprint you need to issue the command::

    xbow lab --shutdown

This will terminate your head node and clean up your private keys and security groups. It will also prompt to see if you wanted to delete your filesystem.

Running an Example **Xbow** Job
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are many example jobs on how to use **Xbow** see `here <https://github.com/ChrisSuess/Project-Xbow/tree/master/xbow/Examples>`_ for more details.

**Xbow** Settings File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your settings.yml file will look like this::

    ### USER SPECIFIC SETTINGS ###
    cluster_name: mycluster                 # your cluster name; type it in the prompt while xbow-config
    scheduler_name: myclusterSchd           # your scheduler name
    worker_pool_name: myclusterWork         # your worker(s) name
    shared_file_system: myclusterFS         # your filesystem name
    creation_token: myclusterFS
    mount_point: /home/ubuntu/shared        # path to where your filesystem is mounted

    ### CLUSTER SPECIFIC SETTINGS ###
    region: eu-west-1                       # AWS region where your instance will be launched 
    price: '0.15'                           # max spot price in US dollars
    image_id: ami-4fgh647925ats             # Amazon Machine Image (AMI)
    scheduler_instance_type: t2.small       # scheduler instance type (hardware)
    worker_instance_type: c5.xlarge         # worker instance type (hardware)
    pool_size: 10                           # how many workers required

    ### SECURITY SPECIFIC SETTINGS ###
    ec2_security_groups: ['SG-1']
    efs_security_groups: ['SG-2']

The default values in ``settings.yml`` will launch a **Xbow** cliuster consisting of a head node and two worker nodes. The
head node will be a ``t2.small`` instance and each worker will be a ``g2.2xlarge`` instance. The head node is a conventional
instance but the workers are "spot" instances - see the AWS documentation `here <https://aws.amazon.com/ec2/spot/>`_.

**Xbow** Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: pics/xbow_diagram_v2.png
