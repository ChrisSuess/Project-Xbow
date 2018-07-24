#!/bin/sh
# Compile a short MD simulation on BPTI
for i in rep?; do
    gmx grompp -f mdrun.mdp -c bpti.gro -p bpti.top -o $i/bpti-md.tpr
done
