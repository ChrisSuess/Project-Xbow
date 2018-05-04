#!/usr/bin/env bash
# Run a simple AMBER MD job
pmemd.cuda -i dhfr.mdin -o dhfr.mdout -c dhfr.crd -r dhfr.rst -p dhfr.prmtop -inf dhfr.mdinfo -x dhfr.nc -O
