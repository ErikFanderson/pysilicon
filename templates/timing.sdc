{% extends "base.tcl" %}
{% block description %}timing.sdc for "{{top_module}}"{% endblock %}
{% block content %}
# NOTES:
# 1. Genus uses picoseconds and femtofarads as units. It does NOT use nanoseconds and picofards!
# 2. create_clock examples (w/ optional clock domain definition)
#   a. create_clock -domain domain1 -name clk1 -period 720 [get_db ports *SYSCLK]
#   b. create_clock -domain domain2 -name clk2 -period 720 [get_db ports *CLK]

# Custom constraints  
#create_clock -domain <domain> -name <clk_name> -period <period> [get_db ports <filter>]
{% endblock %}
