// Project: default_project
// Author: Erik Anderson
// Date: 24/12/2019

`default_nettype none
`timescale 1ns/1ps

//---------------------------------------------------------
// Module: default_file
//---------------------------------------------------------
module test_module_1 #(
    parameter WIDTH = 10
) (
   input wire i_clk, 
   input wire i_rst_n,
   input wire [WIDTH-1:0] i_d,
   output reg [WIDTH-1:0] o_q
);

always @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n)
        o_q <= {WIDTH{1'b0}};
    else
        o_q <= i_d;
end

endmodule
//---------------------------------------------------------

`default_nettype wire
