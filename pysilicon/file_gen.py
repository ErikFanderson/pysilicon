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

def timescale(unit,precision):
    return f"`timescale {unit}/{precision}\n"

def define(name,value,tab=4*" "):
    return f'{tab}`define {name} {value}\n'

def localparam(name,value,tab=4*" "):
    return declaration('localparam',name,value,tab)

def declaration(prefix,name,value,tab=4*" "):
    return f'{tab}{prefix} {name} = {value}\n'

def set_var(name,value):
    return f'{name} = {value};\n'

def declare_signal_packed_1d(signal_type,name,length,tab=4*' '):
    if length > 1:
        return f'{tab}{signal_type} [{length-1}:0] {name};\n'
    else:
        return f'{tab}{signal_type} {name};\n'

def declare_signal_2d(signal_type,name,packed_length,unpacked_length,tab=''):
    """ Declares a 2d unpacked array """
    return f'{tab}{signal_type} [{packed_length-1}:0] {name} [{unpacked_length-1}:0];\n'

def wire(name,length=1,tab=''):
    """ Wire supports simple packed array """
    return declare_signal_packed_1d('wire',name,length,tab)

def reg(name,length=1,tab=''):
    """ Reg supports simple packed array """
    return declare_signal_packed_1d('reg',name,length,tab)

def wire_2d(name,packed_length,unpacked_length,tab=''):
    """ Wire supports simple packed array """
    return declare_signal_2d('wire',name,packed_length,unpacked_length,tab)

def reg_2d(name,packed_length,unpacked_length,tab=''):
    """ Wire supports simple packed array """
    return declare_signal_2d('reg',name,packed_length,unpacked_length,tab)

def define_clock(name,half_period,clk_en=None,tab=4*' '):
    """ Defines a clock """
    rstr = ''
    if clk_en is not None:
        rstr = f"{tab}{name} = 0;\n{tab}forever #({half_period}) {name} = {clk_en} ^ {name};\n"
    else:
        rstr = f"{tab}{name} = 0;\n{tab}forever #({half_period}) {name} = !{name};\n"
    return initial_statement(rstr)

def display(msg):
    return f'$display("{msg}");\n'

def vlog_assert(lhs,rhs,pass_variable,msg='',condition='==',tab=4*' '):
    """ Custom assertion """
    rstr = f'if ({lhs} {condition} {rhs}) begin\n'
    rstr += tab+display(f"[PASSED] {msg}")
    rstr += 'end else begin\n'
    rstr += tab+display(f"[FAILED] {msg}")
    rstr += tab+set_var(pass_variable,"1'b0")
    rstr += 'end\n'
    return rstr 

def check_pass_variable(pass_variable,tab=4*' '):
    rstr = display(30*"#")
    rstr += f"if ({pass_variable} !== 1'b1) begin\n"
    rstr += tab+display("# FAILED")
    rstr += f"end else begin\n"
    rstr += tab+display("# PASSED")
    rstr += f"end\n"
    rstr += display(30*"#")
    return rstr

def wait(value):
    return f"#({value});\n"

def reset_init(name,delay=10,start=0,end=1):
    """ Initializes reset """
    rstr = f"{name} = 1'b{start};\n"
    rstr += wait(delay) 
    rstr += f"{name} = 1'b{end};\n"
    return rstr

def dump_all(dumpfile):
    return "$dumpfile({dumpfile});\n$dumpvars();\n"

def dump_vpd():
    return "$vcdpluson();\n"

def wrap_statement(begin: str,end: str,internals):
    """ 
    Calls func and wraps begin and end around it
    :param func function that is called (should return str)
    """
    fstr = begin
    fstr += internals 
    fstr += end 
    return fstr

def initial_statement(internals):
    """ 
    Calls func and wraps intial begin end around it
    :param func function that is called (should return str)
    """
    return wrap_statement("initial begin \n","end\n",internals)

def vlog_mod_inst(name,inst,parameters,ports):
    ''' 
    Writes beginning of verilog module
    :param ports list of {port:,signal:} 
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
    rstr = '#(\n' if parameters else f'{inst} (\n' 
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
    rstr = '#(\n' if parameters else ''
    for i,p in enumerate(parameters):
        rstr += f"{tab}parameter {p['param']} = {p['value']}" 
        if (len(parameters)-1)==i:
            rstr += '\n) ('
        else:
            rstr += ',\n'
    return rstr

def vlog_mod_dec_ports(ports,tab=4*" "):
    ''' ports for declaration '''
    rstr = '\n' if ports else ');\n\n'
    for i,p in enumerate(ports):
        if p["vec"] is not None:
            rstr += f'{tab}{p["io"]} {p["datatype"]} {p["vec"]} {p["name"]}'
        else:
            rstr += f'{tab}{p["io"]} {p["datatype"]} {p["name"]}'
        if (len(ports)-1)==i:
            rstr += '\n);\n\n'
        else:
            rstr += ',\n'
    return rstr

def vlog_mod_dec(name,ports,parameters):
    ''' Writes beginning of verilog module
    :param ports list of {name:,io:,datatype:,vec:} 
    :param parameters list of {param:,value:} 
    '''
    rstr = f'module {name} '
    rstr += vlog_mod_dec_params(parameters)
    rstr += vlog_mod_dec_ports(ports)
    return rstr

def add_tabs(string,tab=4*' '):
    """ Adds tabs to every new line """
    string_list = [s+'\n' for s in string.splitlines()]
    string_list[0] = tab + string_list[0]
    return tab.join(string_list) 

def vlog_task(name,ports,variables,internals='',tab=4*' '):
    ''' Writes beginning of verilog module
    :param name name of task
    :param ports list of {name:,io:,datatype:,vec:} 
    :param variables list of {name:,datatype:,length} 
    :param func function to fill out internal (returns str)
    '''
    rstr = begin_section(f"Task Declaration: {name} ")
    # Declare ports
    rstr += f'task {name} (\n' if ports else f'task {name} ();\n'
    for i,p in enumerate(ports):
        rstr += tab + f'{p["io"]} {p["datatype"]} {p["vec"]} {p["name"]}'.replace('  ',' ')
        if (len(ports)-1)==i:
            rstr += '\n);\n'
        else:
            rstr += ',\n'
    # Declare variables
    for v in variables:
        rstr += declare_signal_packed_1d(v['datatype'],v['name'],v['length'],tab)
    rstr += "begin\n"
    rstr += add_tabs(internals,tab)
    rstr += "end\nendtask\n"
    rstr += end_section()
    return rstr

def two_phase_scan_task(name,clk_en,s_in,s_out,s_en,s_update,scan_cycle):
    """ Two phase scan task """
    scan_str="""// Enable scan
{clk_en} = 1'b1;
{s_en} = 1'b1;

// MSB bits are scanned in first            
for (i = 0; i < length; i = i + 1) begin
    j = length-1-i;
    // Scan In
    {s_in} = scan_in_data[j]; // Scan In
    // Scan Out
    scan_out_data[j] = {s_out}; // Scan Out
    #({scan_cycle});
end

// Disable scan 
#({scan_cycle});
{clk_en} = 1'b0;
{s_en} = 1'b0;

// Update
#({scan_cycle});
{s_update} = 1'b1;
#({scan_cycle});
{s_update} = 1'b0;
#({scan_cycle});
"""
    rstr = vlog_task(
        name=name,
        ports=[
            {"name": "scan_in_data", "io": "input", "datatype": '', "vec": f"[4095:0]"},
            {"name": "scan_out_data", "io": "output", "datatype": "reg", "vec": f"[4095:0]"},
            {"name": "length", "io": "input", "datatype": "integer","vec":''},
        ],
        variables=[
            {"name": "i", "datatype": "integer", "length": 1},
            {"name": "j", "datatype": "integer", "length": 1}
        ],
        internals=scan_str
    )
    return rstr

def vlog_file(name,ports,parameters,internals,time_unit='1ns',time_precision='1ps',config=None):
    """ 
    Full verilog module declaration
    :param ports list of {name:,io:,datatype:,vec:} 
    :param parameters list of {param:,value:} 
    :param func function to generate internals of module (returns str)
    :param config dictionary that defines verilog module 
    """
    rstr = ''
    if config is not None:
        rstr += yaml_comment(config,"Autogenerated verilog module: {name}")
    rstr += begin_section(f"Module declaration: {name}") 
    rstr += default_nettype("none")
    rstr += timescale(time_unit,time_precision)
    rstr += vlog_mod_dec(name,ports,parameters)
    rstr += internals 
    rstr += 'endmodule\n'
    rstr += default_nettype("wire")
    rstr += end_section()
    return rstr
