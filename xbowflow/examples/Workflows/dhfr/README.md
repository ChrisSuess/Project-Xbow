Three Amber MD jobs run sequentially.

A simple three-step equlibration workflow

The file multirun.xcf defines the workflow, while dhfr.yml provides the
input parameters for this instance

before running:

0. Make sure your verion of xbowflow >= 0.0.30

To check the workflow:

  xflow-run --dryrun multirun.xcf dhfr.yaml

to run interactively:

  xflow-run multirun.xcf dhfr.yaml

or as a batch job:

  tsp runjob.sh
