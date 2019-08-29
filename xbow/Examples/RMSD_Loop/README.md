Simple MD and analysis loop
===========================

This is a simple example of how to write and execute a simple MD and analysis loop using **Crossflow** on a **Crossbow** cluster.

Background:
----------

The workflow is designed to create a trajectory that links two different conformations of BPTI, as observed by Shaw et al. in their seminal [ANTON simulations](https://science.sciencemag.org/content/330/6002/341). In the original publication, two major conformational states are seen, but it takes about 35 microseconds before the first transition between them is observed.

This workflow uses a basic version of what is sometimes called [milestoning](https://pdfs.semanticscholar.org/4929/1ad147b918ee315ce5d1a1d0eb221ae81bdb.pdf).
Starting from the same starting coordinates, *N* short MD simulations of BPTI are run. Each simulation has a different random number seed, so it generates a different trajectory. Each job is sent to a different **Crossbow** worker node, so the *N* MD jobs run in parallel.

The *N* resulting trajectory files are subsequently analysed to determine which final snapshot has the lowest RMSD from the target structure. *N* new MD jobs are then run, starting from this final snapshot. The loop is repeated as many times as desired, gradually building up a continuous trajectory that links the starting and final conformations (if run long enough!).

Instructions:
-------------

Create a **Crossbow** cluster with an appropriate configuration. We would suggest GPU nodes for the workers (maybe p2.xlarge), and 4, 6, or 12 of them (assuming you will be running 12 replicate simulations each cycle). Edit your $HOME/.xbow/settings.yml file as required.

The cluster will need to be provisioned with the neccessary software at launch time - Gromacs for the MD runs, and the Python package MDTraj for the analysis. A provisioning script `provisioning.dat` is provided. Use this with the `xbow-crreate_cluster` command to create and launch your **Crossbow** cluster:

    xbow-create_cluster -s provisioning.dat

Once the cluster is up, You will need to run:

    xbow-sync

To transfer all the data that is in your current directory on to the cloud.

Then you log in to your **Crossbow** cluster:

    xbow-login
    
Navigate to the $HOME/shared/RMSD_Loop directory and you will be ready to run your MD/analysis job. Run it by simply using:

    python3 simple_loop.py
    
You should be getting some helpful output on your screen while your job is run.

When you are finished with your simulation, and if you don't intend to run any other jobs, you can then log out from the cluster by hitting Ctrl+D on your keyboard.

If you are not planning on running any more simulations, don't forget to run:

    xbow-delete_cluster

This deletes your scheduler and your worker node(s), but not your filesystem.
