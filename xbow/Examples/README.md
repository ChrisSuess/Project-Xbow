Connecting to the CCPBioSim Server
===============================

To launch the workshop please navigate to the [CCPBioSim Server](http://132.145.243.165/) 

Now change to crossbow directory

    cd crossbow-workshop/
    
This should be an empty folder ready for your journey into the cloud!

Now we are going to need some examples



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


Using **Xbow:Portal**
===============================

Last example we simply booted a head node and added workers 'elastically'. This time we are going to create a cluster with workers ready to go and use **Xbow:Portal** to submit jobs.

    xbow-create_cluster
    
Once this is ready, we need to configure our 'Portal'

    xbow-portal
    
This will return an address. Go ahead and copy this into your browser and try **Xbow:Portal** out!

    
**Xbow:Cluster** and XbowFlow
====================================

Make sure your are in the correct folder

    cd RMSD_loop

You will then need to run:

    xbow-sync

To transfer all the data that is in your current directory on to the cloud.

Then you are going to log in to your **Crossbow** cluster:

    xbow-login

**xbow-sync** will have created a shared folder on your networked filesystem. This can be read by all your machines on your cluster.

Navigate here 

    cd shared/RMSD_loop
    
Which will be a copy of your local directory.

And you will be ready to run your MD/analysis job. Run it by simply using:

    python simple_loop.py
    
You should be getting some helpful output on your screen while your job is run.

When you are finished with your simulation, and if you don't intend to run any other jobs, you can then log out from the cluster by hitting Ctrl+D on your keyboard.

Deleting your **Xbow** Cluster
====================================

If you are not planning on running any more simulations, don't forget to run:

    xbow-delete_cluster

This deletes your scheduler and your worker node(s), but not your filesystem.

The filesystem you created is not deleted so all your data remains safe. This allows you to resume working exactly where you left off however you will still be charged for data storage in the cloud.

If you wish to delete your filesystem use the command

    xbow-delete_filesystem

This further prompts you to help avoid any nasty data deletion accidents!

    
