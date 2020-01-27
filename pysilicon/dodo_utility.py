from pathlib import Path
import yaml,json
import getpass 
from datetime import datetime
from jinja2 import Template, Environment, BaseLoader, FileSystemLoader
import logging
import sys,os
import jsonschema 

class PySilicon:
    
    def __init__(self):
        self.logger = self.create_logger(name='pysilicon',log_fname='dodo.log')
        # Working and home directory
        self.wd = Path('.').resolve()
        self.home_dir = os.getenv('PYSILICON_HOME')
        self.error_if_empty(self.home_dir,'PYSILICON_HOME variable not set')
        self.home_dir = Path(self.home_dir)
        self.rel_home = self.home_dir.relative_to(self.wd)
        # Read schemas
        self.schemata = self.get_schemata()
        # Generates filelist and config if they don't already exist
        self.gen_config_action()
        # Open filelist and create lists and strings 
        self.filelist = self.validate_yaml('filelist.yml',self.schemata['filelist'])
        # Open global config 
        self.config = self.validate_yaml('config.yml',self.schemata['config'])
        # Check and resolve all source files
        self.filelist = {
            'defines_src':self.check_and_resolve(self.filelist['defines_src']),
            'rtl_src':self.check_and_resolve(self.filelist['rtl_src']),
            'test_src':self.check_and_resolve(self.filelist['test_src'])
        }
        # Create src file strings
        self.filelist_str = self.create_filelist_str_from_dict(self.filelist) 
        self.filelist_list = self.create_filelist_from_dict(self.filelist)
        self.error_if_empty(self.filelist_list,"No files found in global filelist")
        # Generate scratch directory paths
        self.scratch_base_dir = self.check_and_resolve_single(self.config['scratch_dir'],dirs=True)
        self.error_if_empty(self.scratch_base_dir,
            f'Scratch base directory "{self.config["scratch_dir"]}" is invalid')
        self.scratch_base_dir = self.scratch_base_dir / getpass.getuser()
        self.prj_scratch_dir = self.scratch_base_dir / self.config['project_name'] / 'build'
        # Check and resolve search directories
        self.task_dirs = self.check_and_resolve(self.config['task_dirs'],True)

    def validate_yaml(self,yaml_fname,schema):
        ''' loads and validates yaml using schema dict '''
        with open(yaml_fname,'r') as fp:
            loaded_yaml = yaml.load(fp,Loader=yaml.SafeLoader)
        try:
            jsonschema.validate(instance=loaded_yaml,schema=schema)
        except jsonschema.exceptions.ValidationError as err:
            self.logger.error(err)
            self.error_if_empty(lst=[],
                msg=f'YAML file {Path(yaml_fname).resolve()} does not conform to schema')
        return loaded_yaml 

    def get_schemata(self):
        ''' returns dictionary with filename as key and yaml string as value '''
        schemata = {} 
        for f in (self.home_dir / 'schemata').glob('*.json'):
            if f.is_file():
                with open(f,'r') as fp:
                    schemata[f.stem] = json.load(fp)
        return schemata

    def error_if_empty(self,lst,msg):
        ''' errors out and prints msg if list lst is empty '''
        if not lst:
            self.logger.error(msg)
            sys.exit(-1)

    @staticmethod
    def create_logger(name,log_fname):
        ''' creates a logger with stream and filehandler '''
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] [%(threadName)s] [%(levelname)s] %(message)s");
        # Filehandler - outputs to file
        fh = logging.FileHandler(log_fname,mode='w')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        # Streamhandler - outputs to stderr 
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        return logger

    def verify_and_return(self,yaml_fname,schema_fname):
        return ''

    def shell(self,command):
        ''' Logs command and returns exit status '''
        self.logger.info(command)
        return os.system(command)
   
    def check_and_resolve(self,rel_paths,dirs=False):
        ''' Checks and resolves a list of dirs, files, or files and dirs '''
        if rel_paths:
            resolved_paths = []
            for i,path in enumerate(rel_paths):
                rp = self.check_and_resolve_single(path,dirs)
                if rp is not None:
                    resolved_paths.append(rp)
            return resolved_paths
        return []

    def check_and_resolve_single(self,rel_path,dirs=False):
        ''' Checks and resolves a file or dir '''
        if rel_path:
                rp = Path(rel_path).resolve()
                if rp.is_file():
                    return rp
                elif dirs:
                    if rp.is_dir():
                        return rp
                    else:
                        self.logger.warning(f'"{rp}" is neither a file nor a directory.')
                else:
                    self.logger.warning(f'"{rp}" is not a file.')
        return None
   
    @staticmethod
    def strip_and_cat(items,spacer=' '):
        ''' Takes a list of str and strips leading and trailing spaces before concatenating them '''
        if items:
            stripped_items = [str(item).strip() for item in items]
            return spacer.join(stripped_items)
        return ''
    
    @staticmethod
    def create_filelist_from_dict(filelist,test=True):
        ''' Returns a list of files with test files optionally included '''
        if test:
            return filelist['defines_src']+filelist['rtl_src']+filelist['test_src']
        return filelist['defines_src']+filelist['rtl_src']
    
    @staticmethod
    def create_filelist_str_from_dict(filelist,test=True):
        ''' Returns a list of files with test files optionally included '''
        return PySilicon.strip_and_cat(PySilicon.create_filelist_from_dict(filelist,test))
    
    def filter_files(self,file_type,filelist):
        l = []
        for f in filelist[file_type]:
            f = Path(f).resolve()
            if f in self.filelist[file_type]:
                l.append(f)
            else:
                self.logger.warning(f'"{f}" not defined in field "{file_type}" of global filelist')
        return l

    def create_new_filelist(self,filelist,defines=True,rtl=True,test=True):
        ''' filelist: dict with "defines_src", "rtl_src", and "test_src" field'''
        new_filelist = {'defines_src':[],'rtl_src':[],'test_src':[]}
        # DEFINES
        if defines and filelist['defines_src']:
            new_filelist['defines_src'] += filter_files('defines_src',filelist)
        # RTL 
        if rtl and filelist['rtl_src']:
            new_filelist['rtl_src'] += filter_files('rtl_src',filelist)
        # SRC 
        if test and filelist['test_src']:
            new_filelist['test_src'] += filter_files('test_src',filelist)
        # Return new filelist
        if new_filelist['defines_src'] or new_filelist['rtl_src'] or new_filelist['test_src']:
            return new_filelist
        else:
            return self.filelist 

#----------------------------------------------------------
# Utility Methods
#----------------------------------------------------------
    def find_tasks(self,env_files):
        ''' Recursively searches directories for environment files that will help create tasks '''
        fnames = []
        for d in self.task_dirs:
            for f in (self.wd / d).rglob('*.yml'):
                f = f.resolve()
                if f.name in env_files:
                    fnames.append(str(f)) 
        return fnames

    def return_scratch_path(self,dirname,module):
        now = datetime.now()
        return self.prj_scratch_dir / dirname / module / now.strftime("%m-%d-%Y-%H:%M:%S") 
    
    @staticmethod
    def unlink_missing_ok(dirname):
        ''' Unlinks directory if it exists '''
        try: 
            (dirname).unlink()
        except FileNotFoundError:
            pass
    
    def symlink_scratch(self,exp_dir):
        ''' Unlinks and then relinks project build dir from scratch '''
        self.unlink_missing_ok(self.wd / 'build')
        self.unlink_missing_ok(exp_dir.parents[0] / 'current')
        Path(self.wd / 'build').symlink_to(self.prj_scratch_dir,target_is_directory=True)
        (exp_dir.parents[0] / 'current').symlink_to(exp_dir)
   
    def check_and_cat(self,filelist):
        ''' Checks list of files and then concatenates them into string '''
        return self.strip_and_cat(self.check_and_resolve(filelist))
    
    def gen_sim_tcl(self,template_path,exp_dir,config):
        ''' Generates sim.tcl from template '''
        # Create syn.tcl
        self.jinja_render(
            template_path=template_path,
            output_file_path=exp_dir / 'sim.tcl',
            testbench=config['testbench']
        )
    
    def gen_syn_tcl(self,template_path,exp_dir,config):
        ''' Generates syn.tcl from template '''
        # Create syn.tcl
        self.jinja_render(
            template_path=template_path,
            output_file_path=exp_dir / 'syn.tcl',
            top_module=config['top'],
            hdl_files=config['hdl_files'],
            sdc_file=self.check_and_resolve_single(config['sdc']),
            libs=self.check_and_cat(self.config['libs_'+config['libs']]),
            lefs=self.check_and_cat(self.config['lefs']),
            cap_table_file=self.check_and_resolve_single(self.config['cap_table_file']),
            qrc_tech_file=self.check_and_resolve_single(self.config['qrc_tech_file'])
        )
    
    def jinja_render(self,template_path,output_file_path,**kwargs):
        ''' Loads template and outputs to file '''
        with open(template_path,'r') as fp:
            fsl = FileSystemLoader(f"{self.home_dir / 'templates'}")
            template = Environment(loader=fsl).from_string(fp.read())
        now = datetime.now()
        with open(output_file_path,'w') as fp:
            fp.write(template.render(kwargs,
                uname=getpass.getuser(),
                date=now.strftime("%m/%d/%Y-%H:%M:%S"))
            )
    
    def return_define_flags(self,syn_filelist):
        ''' Creates define flags for syn_par modules '''
        define_flags = []
        for f in syn_filelist:
            flag = '-define ' + f.name.split('.')[0].upper() + '_SYN_PAR'
            self.logger.info(f'Auto define flag: "{flag}"')
            define_flags.append(flag)
        return define_flags

    def create_scratch_dir(self,dirname,module):
        ''' creates scratch directory and builds symlink '''
        exp_dir = self.return_scratch_path(dirname,module)
        exp_dir.mkdir(parents=True,exist_ok=True)
        self.symlink_scratch(exp_dir)
        return exp_dir

#----------------------------------------------------------
# Task Action Methods
#----------------------------------------------------------
    def sim_action(self,sim_type,config):
        ''' Action fn for simulation '''
        self.logger.info(f'Start sim_{sim_type} task "{config["name"]}"')
        # Retrieve syn and par behavior models - as well as auto define flags
        filelist = config['hdl_files']
        define_flags = []
        if sim_type != 'rtl':
            syn_fl = self.check_and_resolve(config['syn_par_filelist'])
            filelist += syn_fl 
            filelist += self.check_and_resolve(self.config['std_cell_rtl'])
            define_flags = self.return_define_flags(syn_fl) 
        flist_str = self.strip_and_cat(filelist)
        # Create scratch directory
        exp_dir = self.create_scratch_dir('sim_'+sim_type,config['name'])
        # Format flags
        try:
            flags = self.strip_and_cat(config['sim_flags']+define_flags)
        except TypeError:
            flags = self.strip_and_cat(define_flags)
        tb = config['testbench']
        # Generate simulation TCL file
        try:
            self.gen_sim_tcl(self.wd / config['tcl_template'],exp_dir,config)
        except TypeError:
            self.gen_sim_tcl(self.home_dir / "templates/sim_default.tcl",exp_dir,config)
        # CD into scratch dir and run simulation 
        self.shell(f'cp dodo.log {exp_dir}; cd {exp_dir}; xrun {flags} {flist_str} -top {tb} -input {exp_dir / "sim.tcl"}')
    
    def syn_action(self,config):
        ''' Action fn for synthesis '''
        self.logger.info(f'Start syn task "{config["name"]}"')
        # Create scratch directory
        exp_dir = self.create_scratch_dir('syn',config['name'])
        # Generate syn.tcl
        self.gen_syn_tcl(self.wd / config['tcl_template'],exp_dir,config),
        # Format flags
        flags = self.strip_and_cat(config['syn_flags'])
        # CD into scratch dir and run simulation 
        self.shell(f'cp dodo.log {exp_dir}; cd {exp_dir}; genus {flags} -f {exp_dir / "syn.tcl"}')
    
    def gen_mod_action(self):
        ''' action portion of gen_module task '''
        # Get module and directory names
        module_name = input("Module name: ")
        rel_parent_path = input("Path to module directory: ")
        parent_path = Path(rel_parent_path).resolve()
        while(not(parent_path.is_dir())):
            rel_parent_path = input(f'"{parent_path}" is invalid path! Path to module directory: ')
            parent_path = Path(rel_parent_path).resolve()
        rel_mod_dir = Path(rel_parent_path) / module_name
        mod_dir = parent_path / module_name
        mod_dir.mkdir()
        # Render jinja templates
        self.jinja_render(self.home_dir/"templates/syn.yml",mod_dir/"syn.yml",
            top_module=module_name,mod_dir=rel_mod_dir,rel_home=self.rel_home)
        self.jinja_render(self.home_dir / "templates/sim_rtl.yml",mod_dir / "sim_rtl.yml",
            top_module=module_name,rel_home=self.rel_home)
        self.jinja_render(self.home_dir / "templates/sim_syn.yml",mod_dir / "sim_syn.yml",
            top_module=module_name,rel_home=self.rel_home)
        self.jinja_render(self.home_dir / "templates/sim_par.yml",mod_dir / "sim_par.yml",
            top_module=module_name,rel_home=self.rel_home)
        self.jinja_render(self.home_dir / "templates/timing.sdc",mod_dir / "timing.sdc",
            top_module=module_name)
        self.logger.info(f'Module "{module_name}" generated at "{mod_dir}"')

    def gen_config_action(self,possible_to_overwrite=False):
        ''' action portion of gen_config task '''
        # Filelist
        if (self.wd / 'filelist.yml').is_file():
            if possible_to_overwrite:
                response = input('filelist.yml exists in working directory. Replace?(Y/n)')
                if response.lower() == 'y':
                    self.jinja_render(self.home_dir/"templates/filelist.yml",
                        self.wd/'filelist.yml',home_dir=self.home_dir)
        else:
            self.jinja_render(self.home_dir/"templates/filelist.yml",
                        self.wd/'filelist.yml',home_dir=self.home_dir)
        # Config 
        if (self.wd / 'config.yml').is_file():
            if possible_to_overwrite:
                response = input('config.yml exists in working directory. Replace?(Y/n)')
                if response.lower() == 'y':
                    self.jinja_render(self.home_dir/"templates/config.yml",self.wd/'config.yml')
        else:
            self.jinja_render(self.home_dir/"templates/config.yml",self.wd/'config.yml')
