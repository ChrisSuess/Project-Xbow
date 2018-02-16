from __future__ import print_function
from xbowflow.pipelines import InterfaceKernel, SubprocessKernel, Pipeline
from xbowflow.clients import dask_client

cx1 = [
        'stage             ?= 0',
        'cycle             ?= 0',
        'shared            $= .',
        'input_file        $= {shared}/tmd_1.in',
        'start_coordinates $= {shared}/csaw.min1',
        'end_coordinates   $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
        'trajectory        $= {shared}/csaw_{cycle}_{rep}.nc',
      ]
c12 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/tmd_2.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
      ]

c23 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/production_md.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
      ]

c34 = [
        'ref_coordinate_list [= {shared}/csaw_{cycle}_{rep}.rst7',
        'reps                [= {rep}',
      ]

c41 = [
        'stage             ?= 0',
        'cycle             ?= {cycle} + 1',
        'input_file        $= {shared}/tmd_1.in',
        'start_coordinates $= {shared}/csaw.min1',
        'ref_coordinates   ]= {ref_coordinate_list}',
        'rep               ]= {reps}',
        'end_coordinates   $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
        'trajectory        $= {shared}/csaw_{cycle}_{rep}.nc',
      ]

amber_template = 'mpirun -np 2 pmemd.MPI -O -c {start_coordinates}'\
                ' -p {shared}/csaw.top'\
                ' -i {input_file}'\
                ' -r {end_coordinates}'\
                ' -ref {ref_coordinates}'\
                ' -x {trajectory}'

coco_template = ' pyCoCo -v -n 2 --dims 4 --grid 13 '\
                ' -t {shared}/csaw_amber.pdb'\
                ' -s "(not water) and (mass > 2.0)" '\
                ' -o {ref_coordinate_list}'\
                ' -i {shared}/*.nc'\
                ' -l {shared}/coco{cycle}{rep}.log'

amber_kernel = SubprocessKernel(amber_template)
coco_kernel = SubprocessKernel(coco_template)

ix1 = InterfaceKernel(cx1)
i12 = InterfaceKernel(c12)
i23 = InterfaceKernel(c23)
i34 = InterfaceKernel(c34)
i41 = InterfaceKernel(c41)

#client = dask_client(local=True)
client = None
prepipe = Pipeline(client, [ix1])
mainpipe = Pipeline(client, [amber_kernel, i12, amber_kernel, i23, amber_kernel, i34, coco_kernel, i41])


ref_coordinates = '/home/ubuntu/shared/CoCo-MD_example/csaw.min1'
inits = [{'rep' : 0, 'ref_coordinates': ref_coordinates}, 
         {'rep' : 1, 'ref_coordinates': ref_coordinates}]

out = prepipe.run(inits)
for i in range(2):
    out = mainpipe.run(out)
print(out)
