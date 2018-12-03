This example Jupyter notebook shows am Xflow workflow that:

1. Ensures all required Python packages and applications are installed.
2. Downloads a protein-ligand complex from the PDB.
3. Runs FPocket on the protein to find the cavities.
4. Identifies the largest cavity.
5. Prepares the ligand and receptor for docking using AutoDock Tools.
6. Re-docks the ligand into this cavity using AutoDock Vina.
7. Outputs information about the docking, and similarity between docked poses
and the crystal structure conformation.
