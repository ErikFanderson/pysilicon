#!/usr/bin/env tcsh 

# Set PYTHONPATH accordingly
if ( $?PYTHONPATH ) then
    setenv PYTHONPATH ${PYTHONPATH}:${PWD}
else
    setenv PYTHONPATH ${PWD}
endif
