#!/bin/bash

cd gromacs
echo "running gromacs in $PWD"

export gmx="/usr/local/gromacs/5.1.3/bin/gmx"


which gmx

/usr/local/gromacs/5.1.3/bin/gmx grompp -f min_aa.mdp -c pga_60_r1_aa.gro -p pga_60_r1_aa.top -o pga_60_r1_aa_min.tpr
/usr/local/gromacs/5.1.3/bin/gmx mdrun -s pga_60_r1_aa_min.tpr -o pga_60_r1_aa_min.trr -c pga_60_r1_aa_min.gro -e pga_60_r1_aa_min.edr -g pga_60_r1_aa_min.log

/usr/local/gromacs/5.1.3/bin/gmx grompp -f npt1_aa.mdp -c pga_60_r1_aa_min.gro -p pga_60_r1_aa.top -o pga_60_r1_aa_npt1.tpr
/usr/local/gromacs/5.1.3/bin/gmx mdrun -s pga_60_r1_aa_npt1.tpr -o pga_60_r1_aa_npt1.trr -c pga_60_r1_aa_npt1.gro -e pga_60_r1_aa_npt1.edr -g pga_60_r1_aa_npt1.log -cpo pga_60_r1_aa_npt1.cpt
