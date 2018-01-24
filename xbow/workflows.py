import subprocess
import xbow

class Interface(object):
    def __init__(self, cxns):
        self.cxns = cxns

    def run(self, inputs):
        if isinstance(inputs, list):
            self.interfacetype = 'gather'
        else:
            self.interfacetype = 'linear'
            self.width = None
            for tup in self.cxns:
                if tup[1] == '>':
                    self.interfacetype = 'scatter'
                    width = len(tup[2].format(**inputs).split())
                    if self.width is not None:
                        if self.width != width:
                            raise ValueError('Error - inconsistent widths in scatter interface')
                    else:
                        self.width = width
                            
        if self.interfacetype == 'linear':
            outputs = inputs.copy()
            if 'returncode' in inputs:
                if inputs['returncode'] != 0:
                    return outputs
            try:
                for cxn in self.cxns:
                    if cxn[1] == '=':
                        outputs[cxn[0]] = cxn[2].format(**outputs)
                    elif cxn[1] == '+':
                        outputs[cxn[0]] = int(inputs[cxn[0]]) + int(cxn[2])
                    else:
                        raise ValueError('Error - unknown interface operation {}'.format(cxn))
                outputs['cmd'] = outputs['template'].format(**outputs)
                outputs['returncode'] = 0
                return outputs
            except:
                outputs['returncode'] = 1
                outputs['cmd'] = 'interface'
                outputs['output'] = sys.exc_info()
                return outputs
        elif self.interfacetype == 'gather':
            try:
                outputs = inputs[0].copy()
                for cxn in self.cxns:
                    if cxn[1] == '<':
                        outputs[cxn[0]] = cxn[2].format(**outputs)
                    if cxn[0] == 'template':
                        outputs['template'] = cxn[2]
                for inp in inputs[1:]:
                    for cxn in self.cxns:
                        if not cxn[0] =='template':
                            if cxn[1] == '<':
                                outputs[cxn[0]] = outputs[cxn[0]] + ' ' + cxn[2].format(**inp)
                
                outputs['cmd'] = outputs['template'].format(**outputs)
                outputs['returncode'] = 0
                return outputs
            except:
                raise
                outputs['returncode'] = 1
                outputs['cmd'] = 'interface'
                outputs['output'] = sys.exc_info()
                return outputs
        else:
            try:
                outputs = []
                for i in range(self.width):
                    output = inputs.copy()
                    for cxn in self.cxns:
                        if cxn[1] == '>':
                            output[cxn[0]] = cxn[2].format(**output).split()[i]                         
                        elif cxn[1] == '+':
                            output[cxn[0]] = int(output[cxn[0]]) + int(cxn[2])
                        elif cxn[1] == '=':
                            output[cxn[0]] = cxn[2].format(**output)
                    output['cmd'] = output['template'].format(**output)
                    output['returncode'] = 0
                    outputs.append(output)
                return outputs
            except:
                raise
                for i in range(self.width):
                    outputs[i]['returncode'] = 1
                    outputs[i]['cmd'] = 'interface'
                    outputs[i]['output'] = sys.exc_info()
                return outputs
        
class GenericKernel(object):
    def __init__(self):
        self.operation = 'compute'

    def run(self, inputs):
        outputs = inputs
        if 'returncode' in inputs:
            if inputs['returncode'] != 0:
                return outputs
        try:
            result = subprocess.check_output(outputs['cmd'].split(), stderr=subprocess.STDOUT)
            outputs['output'] = result
        except subprocess.CalledProcessError as e:
            outputs['returncode'] = e.returncode
            outputs['cmd'] = e.cmd
            outputs['output'] = e.output
        return outputs

class DummyKernel(object):
    def __init__(self):
        self.operation = 'compute'
    
    def run(self, inputs, fail=False):
        outputs = inputs
        if outputs['returncode'] != 0:
            return outputs
        if fail:
            outputs['returncode'] = 1
            outputs['output'] = 'DummyKernel failed'
        else:
            outputs['returncode'] = 0
            outputs['cmd'] = 'DummyKernel ran with {}'.format(outputs['cmd'])
        return outputs

class Pipeline(object):
    def __init__(self, client, kilist):
        self.client = client
        self.kilist = kilist

    def run(self, inputs):
        intlist = [inputs]
        for ki in self.kilist:
            inp = intlist[-1]
            if isinstance(inp, list) and ki.operation != 'gather':
                intlist.append(self.client.map(ki.run, inp, pure=False))
            else:
                intlist.append(self.client.submit(ki.run, inp, pure=False))
        outputs = intlist[-1]
        if isinstance(outputs, list):
            outputs = self.client.gather(outputs)
        else:
            outputs = outputs.result()
        return outputs


