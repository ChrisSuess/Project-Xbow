Three Amber MD jobs run sequentially.

A simple three-step equlibration workflow

The file equilibration.py defines the workflow, while dhfr.yml provides the
input parameters for this instance

before running:

1. Ensure you have Amber or AmberTools installed.
2. Edit dhfr.yml to make sure the name of the executable is right.
3. If you are running the workflow on a Xbow cluster, edit dhfr.yml to set local=False

to run interactively:

  python equilibration.py dhfr.yaml

or as a batch job on an Xbow cluster:

  tsp runjob.sh
