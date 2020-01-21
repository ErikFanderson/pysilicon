// Project: default_project
// Author: Erik Anderson
// Date: 24/12/2019

`default_nettype none
`timescale 1ns/1ps

//---------------------------------------------------------
// Module: default_file_tb
//---------------------------------------------------------
module test_module_0_tb();

// Example parameter declaration
parameter WIDTH = 8;

// Example signal declaration 
reg clk, rst_n;
reg [WIDTH-1:0] d;
wire [WIDTH-1:0] q;

// Example clock declaration 
initial begin
    clk = 1'b0;
    forever #(1) clk = !clk;
end

// Example DUT instantiaton
test_module_0 #(.WIDTH(WIDTH)) dut (
    .i_clk(clk),
    .i_rst_n(rst_n),
    .i_d(d),
    .o_q(q)
); 

// Example Simulation
initial begin
    // $dumpfile(<filename>); $dumpvars(<levels>,<mod/var 0>,...,<mod/var N>);
    rst_n = 1'b0;
    #(1);
    rst_n = 1'b1;
    d = 1'b1;
    #(100);
    $finish;
end

endmodule
//---------------------------------------------------------

`default_nettype wire
