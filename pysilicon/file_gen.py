import os,sys
import jsonschema
import json,yaml

#----------------------------------------------------------
# Utility functions 
#----------------------------------------------------------
def validate_yaml(yaml_fname,schema_fname):
    ''' loads and validates yaml using schema dict '''
    with open(schema_fname,'r') as fp:
        loaded_schema = json.load(fp)
    with open(yaml_fname,'r') as fp:
        loaded_yaml = yaml.load(fp,Loader=yaml.SafeLoader)
    try:
        jsonschema.validate(instance=loaded_yaml,schema=loaded_schema)
    except jsonschema.exceptions.ValidationError as err:
        print(f'{err}\nYAML file {Path(yaml_fname).resolve()} does not conform to schema')
        sys.exit(-1)
    return loaded_yaml 

#----------------------------------------------------------
# Generic code gen functions 
#----------------------------------------------------------
def comment(msg,sym='//'):
    return f'{sym} {msg}\n'

def begin_section(msg,sym='//'):
    ''' Writes fancy comment '''
    rstr = ''
    rstr += f'{sym}{80*"-"}\n'
    rstr += comment(msg,sym)
    rstr += f'{sym}{80*"-"}\n'
    return rstr

def end_section(sym='//'):
    ''' Writes fancy comment '''
    return f'{sym}{80*"-"}\n\n'

def yaml_comment(yml_obj,msg):
    rstr = ''
    rstr += begin_section(msg)
    for line in yaml.dump(yml_obj).splitlines():
        rstr += comment(line)
    rstr += end_section()
    return rstr
    
#----------------------------------------------------------
# Verilog code gen functions 
#----------------------------------------------------------
def default_nettype(nettype):
    return f"`default_nettype {nettype}\n"

def define(name,value,tab=4*" "):
    return f'{tab}`define {name} {value}\n'

def localparam(name,value,tab=4*" "):
    return declaration('localparam',name,value,tab)

def declaration(prefix,name,value,tab=4*" "):
    return f'{tab}{prefix} {name} = {value}\n'

def vlog_mod_inst(name,inst,parameters,ports):
    ''' Writes beginning of verilog module
    ports: list of {name:,io:,datatype:,vec:} 
    '''
    rstr = f'{name} '
    rstr += vlog_mod_inst_params(inst,parameters)
    rstr += vlog_mod_inst_ports(ports)
    return rstr

def vlog_mod_inst_ports(ports,tab=4*" "):
    ''' ports for instantiation '''
    rstr = ''
    for i,port in enumerate(ports):
        rstr += f"{tab}.{port['port']}({port['signal']})" 
        if (len(ports)-1)==i:
            rstr += '\n);\n'
        else:
            rstr += ',\n'
    return rstr

def vlog_mod_inst_params(inst,parameters,tab=4*' '):
    ''' parameters for instantiation '''
    rstr = f'{inst} (\n'
    if parameters:
        rstr = f'(\n'
    for i,p in enumerate(parameters):
        rstr += f"{tab}.{p['param']}({p['value']})" 
        if (len(parameters)-1)==i:
            rstr += f'\n) {inst} (\n'
        else:
            rstr += ',\n'
    return rstr

def vlog_mod_begin(name,*ports):
    ''' Writes beginning of verilog module
    ports: list of {name:,io:,datatype:,vec:} 
    '''
    rstr = f'module {name}(\n'
    for i,p in enumerate(ports):
        rstr += vlog_port(p['name'],p['io'],p['datatype'],p['vec'],last=(len(ports)-1)==i)
    return rstr

def vlog_port(name,io,datatype,vec=None,last=False,tab=4*' '):
    rstr = ''
    if vec:
        rstr += f'{tab}{io} {datatype} {vec} {name}'
    else:
        rstr += f'{tab}{io} {datatype} {name}'
    if last:
        rstr += '\n);\n'
    else:
       rstr += ',\n'
    return rstr

