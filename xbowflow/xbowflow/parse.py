def parse_functemplate(template):
    '''Parse a function template to identify the function name and
       output key.'''
    modname = template[0:template.index('.')]
    i = template.index('.') + 1
    j = template.index('(')
    funcname = template[i:j]
    i = template.rindex('{') + 1
    j = template.rindex('}')
    outkey = template[i:j]
    return modname, funcname, outkey
