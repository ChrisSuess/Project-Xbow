from __future__ import print_function
from xbowflow.pipelines import InterfaceKernel, SubprocessKernel, Pipeline
from xbowflow.clients import dask_client

cx1 = [
        'tmp             ?= tempfile.mkdtemp()',
        'preamble        $= mkdir -p {tmp}; cd {tmp};',
        'stage           ?= 0',
        'cycle           ?= 0',
        'shared          $= /home/ubuntu/shared/CoCo-MD_example2',
        'input_file      $= {shared}/min1.in',
        'end_coordinates $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
        'ref_coordinates $= {shared}/penta_w.crd',
      ]

a1 = '{preamble} pmemd.CUDA -O -c {shared}/penta_w.crd'\
      ' -p {shared}/[penta_w.top '\
      ' -i {input_file}'\
      ' -r {end_coordinates}'\
      ' -ref {ref_coordinates}'

c12 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/min2.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
      ]

a2 = '{preamble} pmemd.CUDA -O -c {start_coordinates}'\
     ' -p {shared}/penta_w.top'\
     ' -i {input_file}'\
     ' -r {end_coordinates}'\
     ' -ref {ref_coordinates}'

c23 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/md.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
        'trajectory        $= {shared}/ala5_{cycle}_{rep}.nc',
        'energies          $= {shared}/ala5_{cycle}_{rep}.ene',
      ]

a3 = '{preamble} pmemd.CUDA -O -c {start_coordinates}'\
     ' -p {shared}/penta_w.top'\
     ' -i {input_file}'\
     ' -r {end_coordinates}'\
     ' -e {energies}'\
     ' -x {trajectory}'

c34 = [
        'ref_coordinate_list [= {shared}/ala5_{cycle}_{rep}.rst7',
        'reps                [= {rep}',
      ]

c1 = '{preamble} pyCoCo -v --dims 3 --grid 20 '\
     ' -t {shared}/p[enta_w.pdb'\
     ' -s "(not water) and (mass > 2.0)" '\
     ' -o {ref_coordinate_list}'\
     ' -i {shared}/*.nc'\
     ' -l {shared}/coco{cycle}{rep}.log'

c41 = [
        'tmp             ?= tempfile.mkdtemp()',
        'preamble        $= mkdir -p {tmp}; cd {tmp};',
        'stage           ?= 0',
        'cycle           ?= {cycle} + 1',
        'input_file      $= {shared}/min1.in',
        'ref_coordinates ]= {ref_coordinate_list}',
        'rep             ]= {reps}',
        'end_coordinates $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
      ]

ref_coordinates = '/home/ubuntu/shared/CoCo-MD_example2/penta_w.crd'
inits = [{'rep' : 0, 'ref_coordinates': ref_coordinates}, 
         {'rep' : 1, 'ref_coordinates': ref_coordinates}]

ix1 = InterfaceKernel(cx1)
i12 = InterfaceKernel(c12)
i23 = InterfaceKernel(c23)
i34 = InterfaceKernel(c34)
i41 = InterfaceKernel(c41)

amber_kernel_1 = SubprocessKernel(a1)
amber_kernel_2 = SubprocessKernel(a2)
amber_kernel_3 = SubprocessKernel(a3)
coco_kernel = SubprocessKernel(c1)

#client = dask_client()
client = None

prepipe = Pipeline(client, [ix1])
mainpipe = Pipeline(client, [amber_kernel_1, i12, amber_kernel_2, i23, 
                             amber_kernel_3, i34, coco_kernel, i41])
out = prepipe.run(inits)
for i in range(2):
    out = mainpipe.run(out)

# Any errors, print the dictionary
for d in out:
    if d['returncode'] != 0:
        print(d)
