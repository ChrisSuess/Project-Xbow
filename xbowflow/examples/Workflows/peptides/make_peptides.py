import os
import yaml
import sys
from xbowflow import xflowlib
from distributed.client import as_completed

def pep_generate(client, args):
    """
    This workflow creates Amber format coordinate and topology files for
    a series of tripeptides. Each tripeptide is built in an extended
    conformation, solvated in an octahedral box of TIP3P water, neutralised
    by the addition of sufficient Na+ or Cl- counterions, and subjected to
    a three-stage equilibration procedure. Files for each system are then
    written out to separate subdirectories.

    Arguments:
        client: an Xflow distributed client
        args: a dictionary with run-time parameters (in this case, read in
            from a .yaml file).
    """
    # Create and configure MD kernels:
    cmd = '{mdexe} -O -i mdin -o mdout -c inpcrd -p prmtop -r restrt -ref refc -x mdcrd'.format(**args)
    mdrun1 = xflowlib.SubprocessKernel(cmd)
    mdrun1.set_inputs(['inpcrd', 'refc', 'prmtop'])
    mdrun1.set_outputs(['restrt', 'mdcrd', 'mdout'])
    mdrun1.set_constant('mdin', args['mdin1'])

    # The second and third MD stages are just like the first, except for
    # the MD input file
    mdrun2 = mdrun1.copy()
    mdrun2.set_constant('mdin', args['mdin2'])

    mdrun3 = mdrun1.copy()
    mdrun3.set_constant('mdin', args['mdin3'])
    
    # Creare and configure the kernel to generate tleap input files:
    def makeleapinput(rseq):
        """
        Make a tleap input file for an amino acid sequence.
        Arguments:
            rseq (list): a list of amino acids given as three-letter codes.

        Returns:
            CompressdFileContents: the tleap input file.
        """
        with open('tleap.in', 'w') as f:
            f.write('source leaprc.protein.ff14SB\n')
            f.write('source leaprc.water.tip3p\n')
            f.write('pep = sequence {{ {} }}\n'.format(' '.join(rseq)))
            f.write('solvateoct pep TIP3PBOX 8.0\n')
            f.write('addions pep Na+ 0\n')
            f.write('addions pep Cl- 0\n')
            f.write('saveamberparm pep prmtop inpcrd\n')
            f.write('quit\n')
        return xflowlib.CompressedFileContents('tleap.in')
    # Make a FuntionKernel from this Python function:
    mkleapin = xflowlib.FunctionKernel(makeleapinput)
    mkleapin.set_inputs(['rseq'])
    mkleapin.set_outputs(['leapin'])

    # Creare and configure the kernel to run tleap:
    tcmd = '{tleapexe} -f leapin'.format(**args)
    doleap = xflowlib.SubprocessKernel(tcmd)
    doleap.set_inputs(['leapin'])
    doleap.set_outputs(['prmtop', 'inpcrd'])

    # Workflow step 1:
    # Generate the list of peptides required to be built, from the
    # user-supplied list of alternative amino acids at each position:
    peptides = []
    for p1 in args['aa1']:
        for p2 in args['aa2']:
            for p3 in args['aa3']:
                peptides.append([p1, p2, p3])

    # Workflow step 2:
    # Create the tleap input files:
    leapins = client.map(mkleapin, peptides)

    # Workflow step 3:
    # Run tleap on each peptide:
    prmtops, inpcrds = client.map(doleap, leapins)
    refcs = inpcrds

    # Workflow step 4:
    # Run the three-stage equilibration process:
    # 1: restrained energy minimistion
    restarts, mdcrds, mdouts = client.map(mdrun1, inpcrds, refcs, prmtops)
    # 2: Unrestrained energy minimisation
    restarts, mdcrds, mdouts = client.map(mdrun2, restarts, refcs, prmtops)
    # 3: a short md run
    restarts, mdcrds, mdouts = client.map(mdrun3, restarts, refcs, prmtops)

    # Workflow step 5:
    # Create subdirectories for each peptide, and write out the required files
    for trajfile in as_completed(mdcrds):
        i = mdcrds.index(trajfile)
        pepname = '_'.join(peptides[i])
        print('Peptide {} completed'.format(pepname))
        if not os.path.exists(pepname):
            os.mkdir(pepname)
            peppath = os.path.join(pepname, pepname)
        inpcrds[i].result().write(peppath + '.crd')
        prmtops[i].result().write(peppath + '.prmtop')
        mdouts[i].result().write(peppath + '.mdout')
        restarts[i].result().write(peppath + '.rst')
        trajfile.result().write(peppath + '.nc')
        
if __name__ == '__main__':
    # Get an Xflow client:
    client = xflowlib.XflowClient(local=True)

    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Run the job:
    pep_generate(client, args)
