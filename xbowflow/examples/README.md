## Xflow examples

You can download this folder using the command:
```
curl https://raw.githubusercontent.com/ChrisSuess/Project-Xbow/devel/xbowflow/examples.tgz -o examples.tgz
```

The **SimpleJobs** folder contains examples of how to run single Amber and Gromacs MD jobs. 

The **Workflows** folder contains a number of subfolders with examoles of
different sorts of workflows. The **Wiki_examples** folder contains workflow 
definition files (\*.xdf) and example job specification files (\*.yml) for the examples in the workflows user guide (see the Wiki).

Each has 'dryrun: True', so can be run in test mode through xflow-run without 
needing to be on a functioning xbow cluster, e.g.:
```
% xflow-run example_1.xdf example_1.yml
```
As these are 'dummy' examples, do not try to run them with 'dryrun: False'!

Also in the **Workflows** folder are two subfolders, **dhfr** and **bpti** that
contain fully-fledged examples of Amber and Gromacs workflows that can be run
for real on a functioning xbow cluster if you set 'dryrun: False'.

The **multirun** folder provides the skeleton files for a workflow that applies
the same MD protocol to a series of different systems (e.g. maybe a wild-type
protein, plus a variety of mutants).

The **CoCo-MD_CSA** and **CoCo-MD_Ala5** folders contain ready-to-run examples 
of CoCo-MD workflows for Cyclosporine A and alanine pentapeptide.
