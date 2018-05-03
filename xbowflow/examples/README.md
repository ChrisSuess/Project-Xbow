## Xflow examples

The **SimpleExamples** folder contains an example of how to run a single Amber MD job. 

The **Workflows** folder contains the example definition files (\*.xdf) and example job specification files (\*.yml) for the examples in the workflows user guide.

Each has 'dryrun: True', so can be run in test mode through xflow-run without 
needing to be on a functioning xbow cluster, e.g.:

% xflow-run example_1.xdf example_1.yml
