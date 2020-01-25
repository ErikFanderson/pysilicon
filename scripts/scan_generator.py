#!/usr/bin/env python
import os,sys
import argparse
from pathlib import Path
import yaml
from sympy.parsing.sympy_parser import parse_expr
import copy
import jsonschema
import json
   
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

#----------------------------------------------------------
# Scan generator class (uses argparse) 
#----------------------------------------------------------
class ScanGenerator:
    ''' Simple class for generating tex hw files '''
    def __init__(self):
        # Pysilicon check
        self.home_dir = os.getenv('PYSILICON_HOME')
        if self.home_dir is None:
            print('PYSILICON_HOME variable not set')
            sys.exit(-1)
        self.home_dir = Path(self.home_dir)
        # Argparse check
        self.options = self.parse_args()
        if Path(self.options.config).is_file() is False:
            sys.exit(-1)
        self.gen_chain()
    
    def parse_args(self):
        ''' Parse arguments '''
        parser = argparse.ArgumentParser(description="Generates verilog scan chains.")
        parser.add_argument(
            '-c', '--config',
            required=True,
            help='Scan chain configuration file.'
        )
        return parser.parse_args()

    def evaluate_cells(self,config):
        ''' Uses parameters to evaluate cells '''
        self.full_width = 0
        params = config['parameters']
        for cell in config['cells']:
            for item,val in cell.items():
                if isinstance(val,str) and item in ['width','mult']:
                    cell[item] = parse_expr(val,params)
            self.full_width += cell['width']*cell['mult']
        return config
    
    def gen_chain(self):
        ''' Generates all files for scan chain '''
        # Read Config
        self.config = validate_yaml(self.options.config,str(self.home_dir/'schemata/scan.json'))
        self.og_config = copy.deepcopy(self.config)
        self.config = self.evaluate_cells(self.config)
        with open(self.config['name']+'.v','w') as sfp:
            with open(self.config['name']+'_defines.v','w') as dfp:
                self.gen_src(sfp,dfp)

    def gen_src(self,sfp,dfp):
        ''' generates the verilog source '''
        # Populate cell
        cw = 0 # current width
        for cell in self.config['cells']:
            cell['full_width'] = cell['width']*cell['mult'] 
            cell['full_name'] = self.config['prefix']+'_'+cell['name'] 
            cell['min_pos'] = cw 
            cell['max_pos'] = cell['full_width']+cw-1
            cw += cell['full_width']
        # Sin and Sout
        for i,cell in enumerate(self.config['cells']):
            if i == 0:
                cell['sin'] = 'SIn' 
            else:
                cell['sin'] = f"{self.config['cells'][i-1]['full_name']}_to_{cell['full_name']}" 
            try:
                cell['sout'] = f"{cell['full_name']}_to_{self.config['cells'][i+1]['full_name']}" 
            except IndexError:
                cell['sout'] = 'SOut' 
        # Generate files 
        self.write_src(sfp)
        self.write_defines(dfp)

    def write_src(self,fp):
        ''' Writes src file '''
        fstr = '' 
        # YAML config 
        fstr += yaml_comment(self.og_config,f'Scan chain "{self.config["name"]}" YAML configuration file')
        fstr += begin_section("Module declaration")
        fstr += default_nettype('none')
        # Module Declaration
        total_def = f'[`{self.config["prefix"]}_TotalLength-1:0]'
        fstr += vlog_mod_begin(self.config['name'],
            {'name': 'SClkP','io': 'input','datatype': 'wire','vec': None},
            {'name': 'SClkN','io': 'input','datatype': 'wire','vec': None},
            {'name': 'SReset','io': 'input','datatype': 'wire','vec': None},
            {'name': 'SEnable','io': 'input','datatype': 'wire','vec': None},
            {'name': 'SUpdate','io': 'input','datatype': 'wire','vec': None},
            {'name': 'SIn','io': 'input','datatype': 'wire','vec': None},
            {'name': 'SOut','io': 'output','datatype': 'wire','vec': None},
            {'name': 'Cfg','io': 'inout','datatype': 'wire','vec': total_def}
        )
        fstr += '\n'
        # Wire declarations for connecting sout to sin of segments
        fstr += begin_section("Signal declarations for connecting Sin and Sout of segments")
        for cell in self.config['cells']:
            if cell['sout'] != 'SOut': 
                fstr += f"wire {cell['sout']};\n" 
        fstr += end_section()
        # Define and connect segments
        fstr += begin_section("Segment instantiation")
        for i,cell in enumerate(self.config['cells']):
            if cell['R/W'] == 'R':
                fstr += vlog_mod_inst("ReadSegment",cell['full_name'],
                    ports=[
                    {'port': 'SClkP','signal': 'SClkP'},
                    {'port': 'SClkN','signal': 'SClkN'},
                    {'port': 'SEnable','signal': 'SEnable'},
                    {'port': 'CfgIn','signal': f'Cfg[`{cell["full_name"]}]'},
                    {'port': 'SIn','signal': cell['sin']},
                    {'port': 'SOut','signal': cell['sout']}],
                    parameters=[
                    {'param': 'PWidth','value': '`'+cell['full_name']+'_Width'},
                    {'param': 'TwoPhase','value': '`'+self.config['prefix']+'_TwoPhase'}
                    ]
                )
            else:
                fstr += vlog_mod_inst("WriteSegment",cell['full_name'],
                    ports=[
                    {'port': 'SClkP','signal': 'SClkP'},
                    {'port': 'SClkN','signal': 'SClkN'},
                    {'port': 'SReset','signal': 'SReset'},
                    {'port': 'SEnable','signal': 'SEnable'},
                    {'port': 'SUpdate','signal': 'SUpdate'},
                    {'port': 'CfgOut','signal': f'Cfg[`{cell["full_name"]}]'},
                    {'port': 'SIn','signal': cell['sin']},
                    {'port': 'SOut','signal': cell['sout']}],
                    parameters=[
                    {'param': 'PWidth','value': '`'+cell['full_name']+'_Width'},
                    {'param': 'TwoPhase','value': '`'+self.config['prefix']+'_TwoPhase'},
                    {'param': 'ConfigLatch','value': '`'+self.config['prefix']+'_ConfigLatch'}
                    ]
               )
        fstr += end_section()
        # Write to file
        fstr += 'endmodule\n'
        fstr += end_section() 
        fp.write(fstr)

    def write_defines(self,fp):
        ''' Writes the defines file '''
        fstr = '' 
        # YAML config 
        fstr += yaml_comment(self.og_config,
            f'Scan chain "{self.config["name"]}" YAML configuration file')
        # Define the parameters
        tp = 1 
        if self.config['two_phase'] is False:
            tp = 0 
        cl = 1 
        if self.config['config_latch'] is False:
            cl = 0 
        fstr += begin_section("Parameters") 
        fstr += define(self.config['prefix']+'_TwoPhase',tp,tab='')
        fstr += define(self.config['prefix']+'_ConfigLatch',tp,tab='')
        fstr += end_section() 
        # defines total length 
        fstr += begin_section("Total scan chain length") 
        fstr += define(self.config['prefix']+'_TotalLength',self.full_width,tab='')
        fstr += end_section() 
        # iterate through cells and define flattened widths 
        fstr += begin_section("Defines for flattened segment widths") 
        for cell in self.config['cells']:
            fstr += define(cell['full_name']+'_Width',cell['full_width'],tab='')
        fstr += end_section()
        # iterate through cells and define flattened vectors 
        fstr += begin_section("Defines for flattened vector segments") 
        for cell in self.config['cells']:
            fstr += define(cell['full_name'],f"{cell['max_pos']}:{cell['min_pos']}",tab='')
        fstr += end_section()
        # iterate through cells and define mult functions 
        fstr += begin_section("Defines for multi-vector segments") 
        for cell in self.config['cells']:
            name = cell['full_name'] + '_idx(n)'
            value = f"(n * {cell['width']} + {cell['min_pos']}) +: {cell['width']}" 
            fstr += define(name,value,tab='')
        fstr += end_section()
        fp.write(fstr)
   
if __name__=='__main__':
    sg = ScanGenerator()
