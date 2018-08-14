The files in this folder show how to run a CoCo_MD enhanced sampling simulation
for alanine pentapeptide, using AMBER as the MD code.

The workflow goes someting like this:

1. From an ensemble of structures, use pyCoCo to identify unsampled regions
   and generate possible new structures that correspond to them.
2. Using a set of targeted MD simulations, move a well-equilibrated structure 
   of the molecule towards each of the CoCo generated structures (as these 
   themselves can be too 'rough' for use directly).
3. Run production MD from each of the optimised structures, and add the new
   trajectory data to the ensemble.
4. Go back to step 1, until you have enough data.

In this case the system is the alanine pentapeptide, and the length of the 
simulations and number of cycles are much smaller than for real use, so the 
job runs in a reasonable time (which, depending on your worker instance type, 
may still be up to 15 minutes).

Each cycle generates a number of new files, of which the most relevant are 
two new trajectory files, and a CoCo log file.


To check the workflow:

  xflow-run --dryrun cocomd.xcf ala5.yaml

To submit the job:

  tsp xflowrun cocomd.xcf ala5.yaml

