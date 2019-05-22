Demoing how to write and execute a simple MD/analysis loop using **Crossflow**
on a **Crossbow** cluster.

Starting from the same starting coordinates, four short MD simulations are run.
Each simulation has a different random number seed so generates a different
trajectory.
Each job is sent to a different worker node, so the MD jobs run in parallel.

The four resulting trajectory files are analysed to determine which final
snapshot has the highest rmsd from the starting structure.

Four new MD jobs are then run, starting from this final snapshot.
