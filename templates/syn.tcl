{% extends "base.tcl" %}
{% block description %}syn.tcl for "{{top_module}}"{% endblock %}
{% block content %}
#-------------------------------------------------------------------------
# Load liberty timing files
#-------------------------------------------------------------------------
set_db library {{"{"}}{{libs}}{{"}"}}
#-------------------------------------------------------------------------

{% if lefs -%}
#-------------------------------------------------------------------------
# PLE - Simple Flow
#-------------------------------------------------------------------------
# 1. Load lef files
set_db lef_stop_on_error true
set_db lef_library {{"{"}}{{lefs}}{{"}"}}
{%- if cap_table_file %}
# 2a. Load cap table files
set_db cap_table_file {{cap_table_file}}
{%- endif -%}
{%- if qrc_tech_file %}
# 2b. Load qrc tech file (takes precedence over cap table) 
set_db qrc_tech_file {{qrc_tech_file}}
{%- endif %}
#-------------------------------------------------------------------------

{% endif -%}
#-------------------------------------------------------------------------
# Load and elaborate the design
#-------------------------------------------------------------------------
{% for hdl_file in hdl_files -%}
read_hdl {{hdl_file}} 
{% endfor -%}
elaborate {{top_module}}
#-------------------------------------------------------------------------

#-------------------------------------------------------------------------
# Check design and read SDC file 
#-------------------------------------------------------------------------
# Check design for any errors
check_design > reports/syn_check_design.txt
# Load in the constraints file
read_sdc {{sdc_file}} -stop_on_errors
### Specify a floorplan
##specify_floorplan ${VERILOG_TOPLEVEL} -width 60 -height 15
#################################################################
#-------------------------------------------------------------------------

# Add optimization constraints
#

# Synthesize the design
syn_generic
syn_map

# Analyze design
report_ple > reports/report_ple.txt
report_area > reports/report_area.txt
report_timing > reports/report_timing.txt
report_gates > reports/report_gates.txt

# Export design
write_hdl > {{top_module}}.mapped.v
write_sdc > constraints.sdc
write_db -all_root_attributes -script snapshots/final.tcl
#
## export design for Innovus
##-----------------------
##write_design [-basename string] [-gzip_files] [-tcf]
##[-innovus] [-hierarchical] [design]
{% endblock %}
