#!/usr/bin/env tcsh 
conda activate pysilicon
if ( $?PYTHONPATH ) then
    setenv PYTHONPATH ${PYTHONPATH}:${PWD}
else
    setenv PYTHONPATH ${PWD}
endif
