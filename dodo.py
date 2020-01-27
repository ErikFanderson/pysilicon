# Files that will generate tasks
# 1. sim_rtl => sim_rtl.yml
# 2. sim_syn => sim_syn.yml
# 3. sim_par => sim_par.yml
# 4. syn => syn.yml
# 5. par => par.yml

# TODO
# 1. Add tasks for generating testbench and source files
# 2. Split up filelist into inc_dirs and standalone files 
# 3. UVM integration?

# 0. Only have the tasks be validated once!
# 1. Replace current tests with simple ALU test
# 2. Need to finish synthesis tcl stuff (sdc, write for innovus etc...)!
#       a. Need to verify that PLE works    
#       b. need to write out to innovus
#       c. PLE genus flow
#           iii. DEF floorplan file (on a module-by-module basis?) - recommended!
#       f. "define optimization settings" 
#       f. Understand how multiple libraries work together... Why use max or min?
# 5. Add in support for the experiments test flow
# 8. Add place and route tasks
# 12. README!
# 13. pytest
# 14. Need to make sure that SDC path in syn.yml is relative to working directory!

from pysilicon.dodo_utility import *

#----------------------------------------------------------
# DOIT Config 
#----------------------------------------------------------
DOIT_CONFIG = {
    'default_tasks': []
}

ps = PySilicon()

#----------------------------------------------------------
# Synthesis Task 
#----------------------------------------------------------
def task_syn():
    ''' Basic synthesis method '''
    # Search in Analog, Digital, and Misc
    fnames = ps.find_tasks(['syn.yml'])
    # Generate tasks
    for f in fnames:
        config = ps.validate_yaml(f,ps.schemata['syn'])
        filelist = ps.create_new_filelist(config['filelist'],test=False)
        config['hdl_files'] = ps.create_filelist_from_dict(filelist,test=False) 
        yield {
            'name': config['name'],
            'file_dep': config['hdl_files'],
            'targets': [config['name']+'syn.txt'],
            'actions': [(ps.syn_action,[config])],
            'verbosity': 2
        }

#----------------------------------------------------------
# Simulation Task Methods
#----------------------------------------------------------
def sim(sim_type):
    ''' Basic simulation method '''
    # Search in Analog, Digital, and Misc
    fnames = ps.find_tasks(['sim_'+sim_type+'.yml'])
    # Generate tasks
    for f in fnames:
        config = ps.validate_yaml(f,ps.schemata['sim_'+sim_type])
        filelist = ps.create_new_filelist(config['filelist']) 
        config['hdl_files'] = ps.create_filelist_from_dict(filelist) 
        yield {
            'name': config['name'],
            'file_dep': config['hdl_files'],
            'targets': [sim_type+'_'+config['name']+'_target.txt'],
            'actions': [(ps.sim_action,[sim_type,config])],
            'verbosity': 2
        }

def task_sim_rtl():
    ''' Performs RTL simulation for a given block '''
    return sim("rtl")

def task_sim_syn():
    ''' Performs post-synthesis simulation for a given block '''
    return sim("syn")

def task_sim_par():
    ''' Performs post-PAR simulation for a given block '''
    return sim("par")

#----------------------------------------------------------
# Clean Task Methods 
#----------------------------------------------------------
def clean_sim(sim_type):
    ''' Basic simulation clean method '''
    # Search in Analog, Digital, and Misc
    fnames = ps.find_tasks(['sim_'+sim_type+'.yml'])
    # Generate tasks
    for f in fnames:
        config = ps.validate_yaml(f,ps.schemata['sim_'+sim_type])
        exp_dir = ps.return_scratch_path('sim_'+sim_type,config['name'])
        yield {
            'name': config['name'],
            'actions': [f'rm -rf {exp_dir.parents[0]}'],
            'verbosity': 2
        }

def task_clean_sim_rtl():
    ''' Cleans RTL simulation exp dir for a given block '''
    return clean_sim("rtl")

def task_clean_sim_syn():
    ''' Cleans post-syntheis simulation exp dir for a given block '''
    return clean_sim("syn")

def task_clean_sim_par():
    ''' Cleans post-PAR exp dir for a given block '''
    return clean_sim("par")

def task_clean_syn():
    ''' Cleans synthesis results '''
    # Search in Analog, Digital, and Misc
    fnames = ps.find_tasks(['syn.yml'])
    # Generate tasks
    for f in fnames:
        config = ps.validate_yaml(f,ps.schemata['syn'])
        exp_dir = ps.return_scratch_path('syn',config['name'])
        yield {
            'name': config['name'],
            'actions': [f'rm -rf {exp_dir.parents[0]}'],
            'verbosity': 2 
        }

def task_clean_scratch():
    ''' Deletes all files in scratch directory for this project '''
    return {
        'actions': [f'rm -f {ps.wd / "build"};rm -rf {ps.scratch_base_dir / ps.config["project_name"]}'],
        'verbosity': 2
    }

#----------------------------------------------------------
# Module generation tasks 
#----------------------------------------------------------
def task_gen_mod():
    ''' Generates a new module directory w/ default sim, syn, and par config files '''
    return {
        'actions': [ps.gen_mod_action],
        'verbosity': 2
    }

def task_gen_config():
    ''' Generates a default global_config.yml and a default filelist.yml '''
    return {
        'actions': [(ps.gen_config_action,[True])],
        'verbosity': 2
    }

