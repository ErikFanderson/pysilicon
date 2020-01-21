{% extends "base.tcl" %}
{% block description %}sim.tcl for "{{testbench}}"{% endblock %}
{% block content %}
# Probe all in Simulation History Manager (SHM) format used by Cadence
database -shm -default waves
probe -shm {{testbench}} -depth all -all
run
{% endblock %}
