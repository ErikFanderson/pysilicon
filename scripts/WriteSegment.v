
`timescale 1ns/1ps

// Read/write-able scan chain segment

module WriteSegment(
        SClkP,
        SClkN,
        SReset,
        SEnable,
        SUpdate,
        CfgOut,
        SIn,
        SOut    
    );

    //-----------------------------------------------------------------------------------
    //    Parameters
    //-----------------------------------------------------------------------------------
    parameter PWidth =              8;
    parameter TwoPhase =            1;
    parameter ConfigLatch =         1;    //If 0, it uses a register to hold config bit
    //-----------------------------------------------------------------------------------

    //-----------------------------------------------------------------------------------
    //    I/O
    //-----------------------------------------------------------------------------------
    input wire                      SClkP;
    input wire                      SClkN;
    input wire                      SReset;
    input wire                      SEnable;
    input wire                      SUpdate;
    output reg  [PWidth-1:0]        CfgOut;
    input wire                      SIn;
    output wire                     SOut;
    //-----------------------------------------------------------------------------------

    //-----------------------------------------------------------------------------------
    //    Signals
    //-----------------------------------------------------------------------------------
    reg         [PWidth-1:0]        M;
    reg         [PWidth-1:0]        Q;
    wire        [PWidth-1:0]        NextVal;
    //-----------------------------------------------------------------------------------

    //-----------------------------------------------------------------------------------
    //    Assigns
    //-----------------------------------------------------------------------------------
    assign SOut =                   Q[PWidth-1];

    //Most significant bit is the first bit that is shifted in
    generate if (PWidth <= 1) begin
        assign NextVal = (SEnable) ? SIn : CfgOut;
    end else begin
        assign NextVal = (SEnable) ? {Q[PWidth-2:0], SIn} : CfgOut;
    end endgenerate
    //-----------------------------------------------------------------------------------

    //-----------------------------------------------------------------------------------
    //    Chain
    //-----------------------------------------------------------------------------------
    generate if (TwoPhase == 1) begin
        always @ ( * ) if (SClkN) M = NextVal;
        always @ ( * ) if (SClkP) Q = M;
    end else begin
        always @ (posedge SClkP) Q <= NextVal;
    end endgenerate
    //-----------------------------------------------------------------------------------

    //-----------------------------------------------------------------------------------
    //    Configuration Latch/Register
    //-----------------------------------------------------------------------------------
    generate if (ConfigLatch == 1) begin
        //Have to say that this is an asynchronous reset because cadence and synopsys are
        //stupid about inferring latches with asynchronous S/R
        //cadence async_set_reset "SReset"
        //synopsys async_set_reset "SReset"
        always @ ( * ) begin
            if (SReset) CfgOut = {PWidth{1'b0}};
            else if (SUpdate) CfgOut = Q;
        end
    end else begin
        always @ (posedge SClkP or posedge SReset) begin
            if (SReset) CfgOut <= {PWidth{1'b0}};
            else if (SUpdate) CfgOut <= Q;
        end
    end endgenerate
    //-----------------------------------------------------------------------------------

endmodule
