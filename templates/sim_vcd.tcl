{% extends "base.tcl" %}
{% block description %}sim.tcl for "{{testbench}}"{% endblock %}
{% block content %}
# Probe all in Value Change Dump (VCD) format
database -vcd -default waves
probe -vcd {{testbench}} -depth all -all
run
{% endblock %}
