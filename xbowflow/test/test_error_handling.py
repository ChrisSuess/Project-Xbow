from xbowflow import xflowlib
from xbowflow.clients import XflowClient

ls = xflowlib.SubprocessKernel('ls {x} > result')
ls.set_inputs(['x'])
ls.set_outputs(['result'])

if __name__ == '__main__':
    client = XflowClient(local=True)
    testdata = 'crap'
    result = client.submit(ls, testdata)
    result.result().save('ls-result.log')
    client.close()
