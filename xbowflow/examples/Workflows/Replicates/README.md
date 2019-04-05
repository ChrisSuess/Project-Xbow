Four Gromacs MD jobs run in parallel.

Each job starts from the same tpr file, but writes output data to a separate
subdirectory.

The file multirun.xcf defines the workflow, while bpti.yaml provides the
input parameters for this instance

before running:

0. Make sure your verion of xbowflow >= 0.0.30

1. (Optional) If you want to change the length of the MD job, edit mdrun.mdp 
   and re-run grompp to generate a new bpti.tpr file (see compile.sh).

iTo check the workflow:

  xflow-run --dryrun multirun.xcf bpti.yaml

to run interactively:

  xflow-run multirun.xcf bpti.yaml

or as a batch job:

  tsp runjob.sh
