import os
from scripts.dodo_utility import *
from subprocess import Popen
import pathlib
import pytest

ps = PySilicon()

#----------------------------------------------------------
# Generate module tests 
#----------------------------------------------------------
def fake_input(the_prompt):
    prompt_to_return_val = {
        "Module name: ": "test_module_0",
        "Path to module directory: ": "." 
    }
    val = prompt_to_return_val[the_prompt]
    return val

def setup_module(test_gen_mod):
    ''' Generates infra for testing '''
    Popen("doit",shell=True).wait()
    # Add task_dir to config.yml
    config_str = ''
    with open('config.yml','r') as fp:
        for line in fp:
            if 'task_dirs:' not in line:
                config_str += line
    config_str += 'task_dirs:\n  - test_module_0/'
    with open("config.yml","w") as fp:
        fp.write(config_str)

def teardown_module(test_gen_mod):
    Popen("rm dodo.log config.yml filelist.yml",shell=True).wait()
    Popen("rm -rf test_module_0 __pycache__",shell=True).wait()

def test_gen_mod(monkeypatch):
    ''' tests gen_mod task (makes sure that all generated files are correct) '''
    monkeypatch.setattr('builtins.input',fake_input)
    ps.gen_mod_action()
    assert(Popen("doit",shell=True).wait() == 0)
