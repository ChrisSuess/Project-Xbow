Getting and Installing **AWS**
===============================

This configures AWS on your machine. For this workshop we have provided you with trial accounts which you should have received by email.

    pip install awscli

Then run

    aws configure

Which will prompt you for your credentials provided.


Getting and Installing **Xbow**
===============================

The recommended method to install **Xbow** is using pip

    pip install xbow
    
Then configure Xbow using

    xbow-config
    
Finally for this workshop we will need a filesystem

    xbow-create_filesystem

Using **Xbow-Launch**
===============================

In this example you will run a short MD job on BPTI using Gromacs.

You will be issuing the following commands locally (i.e. on your local machine, without logging in to the **Xbow** cluster) but your job will be submitted and run on the cloud.

If you don't already have a head (scheduler) node booted up, then issue the command:

    xbow-launch
    
This will boot up a scheduler node for you, but not any worker nodes yet.

Navigate to the gromacs example folder.

    cd gromacs

Then issue the command:

    xbow-submit gmx mdrun -deffnm bpti-md

Which will boot up a worker node, upload your data, and start running your job on the worker.

You can use:

    xbow-check

To check on the progress of your job. If your job is finished, you'll have the option to download your data (you will be prompted). When your data is downloaded, it is also deleted from the cloud.

If you are not planning on running any more simulations, don't forget to run:

    xbow-delete_cluster

This deletes your scheduler and your worker node(s), but not your filesystem.
    
    
