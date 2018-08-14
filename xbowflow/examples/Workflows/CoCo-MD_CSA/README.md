The files in this folder show how to run a CoCo_MD enhanced sampling simulation
for cyclosporine A, using AMBER as the MD code.

To test the workflow type:
% xflow-run --dryrun cocomd.xcf csa.yaml

This will print out all the commands that would be run.

The file cocomd.xcf contains the workflow definition.
The file csa.yaml contains the inputs for this instance of the workflow.

The other files are the various Amber and pyCoCo input files.

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

% xflow-run cocomd.xcf csa.yaml

Or you can submit it as a background job using tsp:

% tsp xflow-run cocomd.xcf csa.yaml

