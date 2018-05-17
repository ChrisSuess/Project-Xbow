#!/bin/sh
# Compile a short MD simulation on BPTI
gmx grompp -f mdrun.mdp -c bpti.gro -p bpti.top -o bpti-md.tpr
