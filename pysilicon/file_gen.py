import os,sys
import jsonschema
import json,yaml
from pathlib import Path

# TODO Replace parameters, ports etc... with List[NamedTuples]!
# NOTE Any function that returns a string should add a new line! 
# NOTE I.e. always assume that you are starting from a new line

#----------------------------------------------------------
# Utility functions 
#----------------------------------------------------------
def validate_yaml(yaml_fname,schema_fname):
    ''' loads and validates yaml using schema fname '''
    with open(schema_fname,'r') as fp:
        loaded_schema = json.load(fp)
    with open(yaml_fname,'r') as fp:
        loaded_yaml = yaml.load(fp,Loader=yaml.SafeLoader)
    try:
        jsonschema.validate(instance=loaded_yaml,schema=loaded_schema)
    except jsonschema.exceptions.ValidationError as err:
        print(f'{err}\nYAML file "{yaml_fname}" does not conform to schema "{schema_fname}"')
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

def wrap_statement(begin: str,end: str,func):
    """ 
    Calls func and wraps begin and end around it
    :param func function that is called (should return str)
    """
    fstr = begin
    fstr += func()
    fstr += end 
    return fstr

def initial_statement(func):
    """ 
    Calls func and wraps intial begin end around it
    :param func function that is called (should return str)
    """
    return wrap_statement("initial begin \n","end\n",func)

def vlog_mod_inst(name,inst,parameters,ports):
    ''' 
    Writes beginning of verilog module
    :param ports list of {name:,io:,datatype:,vec:} 
    :param parameters list of {param:,value:} 
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

def vlog_mod_dec_params(parameters,tab=4*' '):
    ''' 
    Module declaration
    For declaration. parameter is a dict with 'param' field and 'value' field 
    :param parameters {param: str, value: Any} 
    '''
    rstr = '\n' if parameters else ''
    for i,p in enumerate(parameters):
        rstr += f"{tab}parameter {p['param']} = {p['value']}" 
        if (len(parameters)-1)==i:
            rstr += '\n) ('
        else:
            rstr += ',\n'
    return rstr

def vlog_mod_dec_ports(ports,tab=4*" "):
    ''' ports for declaration '''
    rstr = '\n' if ports else ');\n'
    for i,p in enumerate(ports):
        if p["vec"] is not None:
            rstr += f'{tab}{p["io"]} {p["datatype"]} {p["vec"]} {p["name"]}'
        else:
            rstr += f'{tab}{p["io"]} {p["datatype"]} {p["name"]}'
        if (len(ports)-1)==i:
            rstr += '\n);\n'
        else:
            rstr += ',\n'
    return rstr

def vlog_mod_dec(name,ports,parameters):
    ''' Writes beginning of verilog module
    :param ports list of {name:,io:,datatype:,vec:} 
    :param parameters list of {param:,value:} 
    '''
    rstr = f'module {name} ('
    rstr += vlog_mod_dec_params(parameters)
    rstr += vlog_mod_dec_ports(ports)
    return rstr
