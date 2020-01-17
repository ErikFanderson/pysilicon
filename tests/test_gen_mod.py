import os
from scripts.dodo_utility import *

ps = PySilicon(filelist_fname='filelist.yml',config_fname='global_config.yml')

def fake_input(the_prompt):
    prompt_to_return_val = {
        "Module name: ": "test_module_0",
        "Path to module directory: ": "src/tasks" 
    }
    val = prompt_to_return_val[the_prompt]
    return val

def test_gen_mod(monkeypatch):
    ''' tests gen_mod task '''
    monkeypatch.setattr('builtins.input', fake_input)
    ps.gen_mod_action()
    os.system("rm -rf src/tasks/test_module_0")
