The files in this folder show how to run a CoCo-MD enhanced sampling simulation
for cyclosporine A, using AMBER as the MD code.

The workflow goes someting like this:

1. From an ensemble of structures, use pyCoCo to identify unsampled regions
   and generate possible new structures that correspond to them.
2. Using a series of targeted MD simulations, move a well-equilibrated
   structure of the molecule towards each of the CoCo generated structures (as
   these themselves can be too 'rough' for use directly).
3. Run production MD from each of the optimised structures, and add the new
   trajectory data to the ensemble.
4. Go back to step 1, until you have enough data.

Note: this example workflow has fewer cycles, replicates and shorter MD steps 
than a real one should, so it completes in a reasonable time (which may be up 
to 15 minutes).

Assuming you are on a well-configured xbow cluster, you can run the
workflow interactively by issuing the command:

% python run_coco.py

Or you can submit it as a background job using tsp:

% tsp python run_coco.py

The requirements are:

 - Python packages:
   - MDTraj
   - extasycoco
 - Applications:
   - Amber (or AmberTools, if you edit the scriots to use sander instead of pmemd)
