import xbow

class InterfaceKernel(object):
    def __init__(self, connections):
        self.connections = connections
        self.operation = 'link'
        for con in connections:
            if con[1] == '>':
                self.operation = 'scatter'
            if con[1] == '<':
                self.operation = 'gather'

    def run(self, inputs):
        
        self.scatterwidth = None
        for tup in self.connections:
            if tup[1] == '>':
                scatterwidth = len(tup[2].format(**inputs).split())
                if self.scatterwidth is not None:
                    if self.scatterwidth != scatterwidth:
                        raise ValueError('Error - inconsistent widths in scatter interface')
                else:
                    self.scatterwidth = scatterwidth
                            
        if self.operation == 'link':
            outputs = inputs.copy()
            if 'returncode' in inputs:
                if inputs['returncode'] != 0:
                    return outputs
            try:
                for connection in self.connections:
                    if connection[1] == '=':
                        outputs[connection[0]] = connection[2].format(**outputs)
                    elif connection[1] == '+':
                        outputs[connection[0]] = int(inputs[connection[0]]) + int(connection[2])
                    else:
                        raise ValueError('Error - unknown interface operation {}'.format(connection))
                outputs['cmd'] = outputs['template'].format(**outputs)
                outputs['returncode'] = 0
                return outputs
            except:
                outputs['returncode'] = 1
                outputs['cmd'] = 'interface'
                outputs['output'] = sys.exc_info()
                return outputs
        elif self.operation == 'gather':
            try:
                outputs = inputs[0].copy()
                for inp in inputs:
                    if inp['returncode'] != 0:
                        outputs = inp.copy()
                if outputs['returncode'] != 0:
                    return outputs
                for connection in self.connections:
                    if connection[1] == '<':
                        outputs[connection[0]] = connection[2].format(**outputs)
                    if connection[0] == 'template':
                        outputs['template'] = connection[2]
                for inp in inputs[1:]:
                    for connection in self.connections:
                        if not connection[0] =='template':
                            if connection[1] == '<':
                                outputs[connection[0]] = outputs[connection[0]] + ' ' + connection[2].format(**inp)
                
                outputs['cmd'] = outputs['template'].format(**outputs)
                outputs['returncode'] = 0
                return outputs
            except:
                raise
                outputs['returncode'] = 1
                outputs['cmd'] = 'interface'
                outputs['output'] = sys.exc_info()
                outputs['problem'] = tmpout
                return outputs
        else:
            if inputs['returncode'] != 0:
                outputs = [inputs] * self.scatterwidth
                return outputs
            try:
                outputs = []
                for i in range(self.scatterwidth):
                    output = inputs.copy()
                    for connection in self.connections:
                        if connection[1] == '>':
                            output[connection[0]] = connection[2].format(**output).split()[i]                         
                        elif connection[1] == '+':
                            output[connection[0]] = int(output[connection[0]]) + int(connection[2])
                        elif connection[1] == '=':
                            output[connection[0]] = connection[2].format(**output)
                    output['cmd'] = output['template'].format(**output)
                    output['returncode'] = 0
                    outputs.append(output)
                return outputs
            except:
                raise
                for i in range(self.scatterwidth):
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
            result = subprocess.check_output(inputs['cmd'].split(), stderr=subprocess.STDOUT)
            outputs['output'] = result
        except subprocess.CalledProcessError as e:
            outputs['returncode'] = e.returncode
            outputs['cmd'] = e.cmd
            outputs['output'] = e.output
        return outputs

    def quotefixlist(self, cmd):
        l = []
        join = False
        for w in cmd.split():
            if join:
                l[-1] += ' ' + w
            else:
                l.append(w)
            if '"' in w:
                join = not join
        return l

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
        intermediates = [inputs]
        for ki in self.kilist:
            inp = intermediates[-1]
            if isinstance(inp, list) and ki.operation != 'gather':
                intermediates.append(self.client.map(ki.run, inp, pure=False))
            else:
                intermediates.append(self.client.submit(ki.run, inp, pure=False))
        outputs = intermediates[-1]
        if isinstance(outputs, list):
            outputs = self.client.gather(outputs)
        else:
            outputs = outputs.result()
        return outputs
