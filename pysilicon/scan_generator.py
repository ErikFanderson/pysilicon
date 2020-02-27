#!/usr/bin/env python
import os,sys
import argparse
from pathlib import Path
from sympy.parsing.sympy_parser import parse_expr
import copy
from pysilicon.file_gen import *
import math
import re
import yaml

#----------------------------------------------------------
# Scan generator class (uses argparse) 
#----------------------------------------------------------
class ScanGenerator:
    ''' Verilog Scan Chain Generator '''
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
            'config',
            help='Scan chain configuration file.'
        )
        parser.add_argument(
            '-rw', '--read-write',
            action='store_true',
            help='Generates final module with separate read and write io ports.'
        )
        parser.add_argument(
            '-p', '--prefix',
            default=None,
            help='Optionally define a prefix. Default: Name specified in config'
        )
        parser.add_argument(
            '-b', '--bypass',
            action='store_true',
            help='Optionally generate a module for bypassing scan-serial interface for testing purposes.'
        )
        parser.add_argument(
            '-c', '--config-translate',
            action='store_true',
            help='Translates legacy *.cfg configuration file into YAML config. Other flags are ignored if this flag is passed.'
        )
        return parser.parse_args()

    def evaluate_cells(self,config):
        ''' Uses parameters to evaluate cells '''
        self.full_width = 0
        params = config['parameters']
        # Supported functions
        full_params = {
            "log2": lambda x: math.ceil(math.log2(x)),   
            "clog2": lambda x: math.ceil(math.log2(x)),   
            "flog2": lambda x: math.floor(math.log2(x))
        } 
        # Evaluate params
        for p,val in config['parameters'].items():
            if not isinstance(val,int):
                full_params.update(params)
                params[p] = parse_expr(val,full_params)
        # Evaluate cells
        full_params.update(params)
        for cell in config['cells']:
            for item,val in cell.items():
                if isinstance(val,str) and item in ['width','mult']:
                    cell[item] = parse_expr(val,full_params)
            self.full_width += cell['width']*cell['mult']
        return config
   
    def get_scan_bits_ports(self):
        """Returns list of scan bits ports that is used in multiple files""" 
        # Scan Bits Ports
        total_def = f'[`{self.config["prefix"]}_ScanChainLength-1:0]'
        scan_bits_ports = [{'name': 'ScanBits','io': 'inout','datatype': 'wire','vec': total_def}]
        if self.options.read_write:
            scan_bits_ports = [{'name': 'ScanBitsRd','io': 'input','datatype': 'wire','vec': total_def},
            {'name': 'ScanBitsWr','io': 'output','datatype': 'wire','vec': total_def}]
        return scan_bits_ports

    def gen_chain(self):
        ''' Generates all files for scan chain '''
        # Read Config
        if self.options.config_translate:
            with open(self.options.config,'r') as fp:
                fstr = fp.read()
                with open(Path(self.options.config).stem + '.yml','w') as fp:
                    fp.write(self.translate_cfg(fstr))
                    print(f'File "{Path(self.options.config).stem}.yml" generated successfully.')
        else:
            self.config = validate_yaml(self.options.config,str(self.home_dir/'schemata/scan.json'))
            self.og_config = copy.deepcopy(self.config)
            self.config = self.evaluate_cells(self.config)
            self.config['prefix'] = self.options.prefix if self.options.prefix is not None else self.config['name'] 
            self.config['scan_bits_ports'] = self.get_scan_bits_ports() 
            # Generate basic files
            with open(self.config['name']+'.v','w') as sfp:
                with open(self.config['name']+'_defines.v','w') as dfp:
                    self.gen_src(sfp,dfp)
                    print(f'File "{self.config["name"]}.v" generated successfully.')
                    print(f'File "{self.config["name"]}_defines.v" generated successfully.')
            # Generate optional files
            if self.options.bypass:
                # Core
                rstr = self.gen_bypass_core()
                with open(self.config['name']+'_bypass_core.v','w') as bfp:
                    bfp.write(rstr)
                print(f'File "{self.config["name"]}_bypass_core.v" generated successfully.')
                # Wrapper
                rstr = self.gen_bypass_wrapper()
                with open(self.config['name']+'_bypass.v','w') as bfp:
                    bfp.write(rstr)
                print(f'File "{self.config["name"]}_bypass.v" generated successfully.')

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
        fstr += vlog_mod_dec(self.config['name'],ports=[
                {'name': 'SClkP','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SClkN','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SReset','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SEnable','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SUpdate','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SIn','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SOut','io': 'output','datatype': 'wire','vec': None}]+self.config['scan_bits_ports'],
            parameters=[
                {'param': 'TwoPhase','value': '1'},
                {'param': 'ConfigLatch','value': '1'},
            ]
        )
        # Wire declarations for connecting sout to sin of segments
        fstr += begin_section("Signal declarations for connecting Sin and Sout of segments")
        for cell in self.config['cells']:
            if cell['sout'] != 'SOut': 
                fstr += f"wire {cell['sout']};\n" 
        fstr += end_section()
        # Define and connect segments
        fstr += begin_section("Segment instantiation")
        scan_bits_rd = 'ScanBitsRd' if self.options.read_write else 'ScanBits' 
        scan_bits_wr = 'ScanBitsWr' if self.options.read_write else 'ScanBits' 
        for i,cell in enumerate(self.config['cells']):
            if cell['R/W'] == 'R':
                fstr += vlog_mod_inst("ReadSegment",cell['full_name'],
                    ports=[
                    {'port': 'SClkP','signal': 'SClkP'},
                    {'port': 'SClkN','signal': 'SClkN'},
                    {'port': 'SEnable','signal': 'SEnable'},
                    {'port': 'CfgIn','signal': f'{scan_bits_rd}[`{cell["full_name"]}]'},
                    {'port': 'SIn','signal': cell['sin']},
                    {'port': 'SOut','signal': cell['sout']}],
                    parameters=[
                    {'param': 'PWidth','value': '`'+cell['full_name']+'_Width'},
                    {'param': 'TwoPhase','value': 'TwoPhase'}
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
                    {'port': 'CfgOut','signal': f'{scan_bits_wr}[`{cell["full_name"]}]'},
                    {'port': 'SIn','signal': cell['sin']},
                    {'port': 'SOut','signal': cell['sout']}],
                    parameters=[
                    {'param': 'PWidth','value': '`'+cell['full_name']+'_Width'},
                    {'param': 'TwoPhase','value': 'TwoPhase'},
                    {'param': 'ConfigLatch','value': 'ConfigLatch'}
                    ]
               )
        fstr += end_section()
        # Write to file
        fstr += default_nettype("wire") 
        fstr += 'endmodule\n'
        fstr += end_section() 
        fp.write(fstr)

    def write_defines(self,fp):
        ''' Writes the defines file '''
        fstr = '' 
        # YAML config 
        fstr += yaml_comment(self.og_config,
            f'Scan chain "{self.config["name"]}" YAML configuration file')
        # defines total length 
        fstr += begin_section("Total scan chain length") 
        fstr += define(self.config['prefix']+'_ScanChainLength',self.full_width,tab='')
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

    def gen_bypass_wrapper(self):
        """Wrapper around core file that can be used for custom task generation"""
        # Instantiate core
        scan_ports = [
            {'port': 'ScanBitsRd','signal': 'ScanBitsRd'},
            {'port': 'ScanBitsWr','signal': 'ScanBitsWr'}
        ] if self.options.read_write else [
            {'port': 'ScanBits','signal': 'ScanBits'}
        ]
        internals = vlog_mod_inst(f"{self.config['name']}_bypass_core",'core',
            ports=[
                {'port': 'SClkP','signal': 'SClkP'},
                {'port': 'SClkN','signal': 'SClkN'},
                {'port': 'SEnable','signal': 'SEnable'},
                {'port': 'SIn','signal': 'SIn'},
                {'port': 'SOut','signal': 'SOut'}]+scan_ports,
            parameters=[
                {'param': 'TwoPhase','value': '1'},
                {'param': 'ConfigLatch','value': '1'},
            ]
        )
        # Blank Space for Custom Tasks
        internals += begin_section("Custom Tasks")
        internals += end_section()
        # Return Wrapper
        return vlog_file(
            name=self.config['name'],
            ports=[
                {'name': 'SClkP','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SClkN','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SReset','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SEnable','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SUpdate','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SIn','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SOut','io': 'output','datatype': 'wire','vec': None}]+
                self.config['scan_bits_ports'],
            parameters=[
                {'param': 'TwoPhase','value': '1'},
                {'param': 'ConfigLatch','value': '1'},
            ],
            internals=internals,
            config=self.og_config
        )

    def gen_bypass_core(self):
        """Generates bypass core vlog file"""
        scan_bits_ports = copy.deepcopy(self.config['scan_bits_ports'])
        if self.options.read_write:
            scan_bits_ports[1]['datatype'] = "reg"
        return vlog_file(
            name=self.config['name']+"_bypass_core",
            ports=[
                {'name': 'SClkP','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SClkN','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SReset','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SEnable','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SUpdate','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SIn','io': 'input','datatype': 'wire','vec': None},
                {'name': 'SOut','io': 'output','datatype': 'wire','vec': None}]+scan_bits_ports,
            parameters=[
                {'param': 'TwoPhase','value': '1'},
                {'param': 'ConfigLatch','value': '1'},
            ],
            internals=self.gen_bypass_tasks(),
            config=self.og_config
        )

    def gen_bypass_tasks(self):
        """Generates string of tasks for setting and getting scan chain bits directly"""
        rstr = ''
        for cell in self.config['cells']:
            if cell['R/W'] == 'W':
                rstr += self.gen_bypass_write_tasks(cell)
            else:
                rstr += self.gen_bypass_read_tasks(cell)
        return rstr
  
    def gen_bypass_read_tasks(self,cell):
        """Generates read task for getting scan chain bits directly"""
        rstr = ''
        sb = "ScanBitsRd" if self.options.read_write else "ScanBits"
        idx_port = {"name": "idx", "io": "input", "datatype": 'int', "vec": ''}
        out_port = {"name": "out", "io": "output", "datatype": 'reg', "vec": f'[{cell["width"]-1}:0]'}
        ports = [out_port] if (cell['mult'] == 1) else [out_port,idx_port]
        rhs = f"{sb}[`{cell['full_name']}]" if (cell['mult'] == 1) else f"{sb}[`{cell['full_name']}_idx(idx)]"
        internals = set_var('out',rhs)
        rstr += vlog_task(name='get_' + cell['full_name'],ports=ports,variables=[],internals=internals)
        return rstr

    def gen_bypass_write_tasks(self,cell):
        """Generates write tasks for setting and getting scan chain bits directly"""
        rstr = ''
        sb = "ScanBitsWr" if self.options.read_write else "ScanBits"
        idx_port = {"name": "idx", "io": "input", "datatype": 'int', "vec": ''}
        # Set
        in_port = {"name": "in", "io": "input", "datatype": '', "vec": f'[{cell["width"]-1}:0]'}
        ports = [in_port] if (cell['mult'] == 1) else [in_port,idx_port]
        lhs = f"{sb}[`{cell['full_name']}]" if (cell['mult'] == 1) else f"{sb}[`{cell['full_name']}_idx(idx)]"
        internals = set_var(lhs,"in")
        rstr += vlog_task(name='set_' + cell['full_name'],ports=ports,variables=[],internals=internals)
        # Get
        out_port = {"name": "out", "io": "output", "datatype": 'reg', "vec": f'[{cell["width"]-1}:0]'}
        ports = [out_port] if (cell['mult'] == 1) else [out_port,idx_port]
        rhs = f"{sb}[`{cell['full_name']}]" if (cell['mult'] == 1) else f"{sb}[`{cell['full_name']}_idx(idx)]"
        internals = set_var('out',rhs)
        rstr += vlog_task(name='get_' + cell['full_name'],ports=ports,variables=[],internals=internals)
        return rstr
  
    def translate_cfg(self,cfg_str):
        """Translates from the legacy *.cfg file format to the new YAML format"""
        yml = {"name": None,"parameters": {}, "cells": [] }
        # Regex
        re_params = re.compile('^\s*\$param{\s*"([a-zA-Z0-9_]+)"\s*}\s*=\s*([^;]+);?\s*$')
        re_name = re.compile('^\s*Name\s*=\s([a-zA-Z0-9_]+)\s*$')
        re_cell = re.compile('^\s*([a-zA-Z0-9_]+)\s+([RWrw])\s+([^;\s]+)\s+([^;\s]+)\s*$')
        for line in cfg_str.split('\n'): 
            p = re_params.search(line)
            n = re_name.search(line)
            c = re_cell.search(line)
            # Check to see which one matched
            if p is not None:
                rhs = self.sub_perl_params(p.group(2))
                rhs = self.attempt_int_conv(rhs)
                yml['parameters'][p.group(1)] = rhs
            elif n is not None:
                yml['name'] = n.group(1)
            elif c is not None:
                width = self.sub_perl_params(c.group(3))
                width = self.attempt_int_conv(width)
                mult = self.sub_perl_params(c.group(4))
                mult = self.attempt_int_conv(mult)
                yml['cells'].append(self.return_cell(c.group(1),c.group(2),width,mult))
        return yaml.dump(yml)
                
    def attempt_int_conv(self,val):
        """Attempts to convert to integer"""
        try:
            return int(val)
        except ValueError:
            return val

    def return_cell(self,name,r_w,width,mult):
        return {"name": name, "R/W": r_w, "width": width, "mult": mult}

    def sub_perl_params(self,line):
        """substitute params nonsense with just name of param"""
        re_param = re.compile('\$param{\s*"([a-zA-Z0-9_]+)"\s*}')
        p = re_param.sub(r'\1',line)
        return p 

if __name__=='__main__':
    sg = ScanGenerator()
