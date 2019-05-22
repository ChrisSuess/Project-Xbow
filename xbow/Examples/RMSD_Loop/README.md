Simple MD and analysis loop
===========================

This is a simple tutorial on how to write and execute a simple MD and analysis loop using **Crossflow** on a **Crossbow** cluster.

Starting from the same starting coordinates, four short MD simulations of BPTI are run. Each simulation has a different random number seed, so it generates a different trajectory. Each job is sent to a different **Crossbow** worker node, so the four MD jobs run in parallel.

The four resulting trajectory files are subsequently analysed to determine which final snapshot has the highest RMSD from the starting structure. Four new MD jobs are then run, starting from this final snapshot.

If you don't already have a head (scheduler) node booted up, then issue the command:

    xbow-launch
    
This will boot up a scheduler node for you, but not any worker nodes yet.

If you don't already have any worker nodes booted up, then issue the command:

    xbow-create_cluster

Which will then boot up your worker nodes, according to the specifications of your settings.yml file. 

You will then need to run:

    xbow-sync
    
To transfer all the data that is in your current directory on to the cloud.

Then you are going to log in to your **Crossbow** cluster:

    xbow-login
    
And you will be ready to run your MD/analysis job. Run it by simply using:

    python simple_loop.py
    
You should be getting some helpful output on your screen while your job is run.

When you are finished with your simulation, and if you don't intend to run any other jobs, you can then log out from the cluster by hitting Ctrl+D on your keyboard.

If you are not planning on running any more simulations, don't forget to run:

    xbow-delete_cluster

This deletes your scheduler and your worker node(s), but not your filesystem.
