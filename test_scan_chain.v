//--------------------------------------------------------------------------------
// Scan chain "test_scan_chain" YAML configuration file
//--------------------------------------------------------------------------------
// cells:
// - R/W: R
//   mult: y
//   name: test0
//   width: x
// - R/W: W
//   mult: 1
//   name: test1
//   width: x*y+3
// - R/W: W
//   mult: 1
//   name: test2
//   width: 1
// - R/W: R
//   mult: 1
//   name: test3
//   width: 16
// config_latch: true
// name: test_scan_chain
// parameters:
//   x: 6
//   y: 7
// prefix: TSC
// two_phase: true
//--------------------------------------------------------------------------------

//--------------------------------------------------------------------------------
// Module declaration
//--------------------------------------------------------------------------------
`default_nettype none
module test_scan_chain(
    input wire SClkP,
    input wire SClkN,
    input wire SReset,
    input wire SEnable,
    input wire SUpdate,
    input wire SIn,
    output wire SOut,
    inout wire [`TSC_TotalLength-1:0] Cfg
);

//--------------------------------------------------------------------------------
// Signal declarations for connecting Sin and Sout of segments
//--------------------------------------------------------------------------------
wire TSC_test0_to_TSC_test1;
wire TSC_test1_to_TSC_test2;
wire TSC_test2_to_TSC_test3;
//--------------------------------------------------------------------------------

//--------------------------------------------------------------------------------
// Segment instantiation
//--------------------------------------------------------------------------------
ReadSegment (
    .PWidth(`TSC_test0_Width),
    .TwoPhase(`TSC_TwoPhase)
) TSC_test0 (
    .SClkP(SClkP),
    .SClkN(SClkN),
    .SEnable(SEnable),
    .CfgIn(Cfg[`TSC_test0]),
    .SIn(SIn),
    .SOut(TSC_test0_to_TSC_test1)
);
WriteSegment (
    .PWidth(`TSC_test1_Width),
    .TwoPhase(`TSC_TwoPhase),
    .ConfigLatch(`TSC_ConfigLatch)
) TSC_test1 (
    .SClkP(SClkP),
    .SClkN(SClkN),
    .SReset(SReset),
    .SEnable(SEnable),
    .SUpdate(SUpdate),
    .CfgOut(Cfg[`TSC_test1]),
    .SIn(TSC_test0_to_TSC_test1),
    .SOut(TSC_test1_to_TSC_test2)
);
WriteSegment (
    .PWidth(`TSC_test2_Width),
    .TwoPhase(`TSC_TwoPhase),
    .ConfigLatch(`TSC_ConfigLatch)
) TSC_test2 (
    .SClkP(SClkP),
    .SClkN(SClkN),
    .SReset(SReset),
    .SEnable(SEnable),
    .SUpdate(SUpdate),
    .CfgOut(Cfg[`TSC_test2]),
    .SIn(TSC_test1_to_TSC_test2),
    .SOut(TSC_test2_to_TSC_test3)
);
ReadSegment (
    .PWidth(`TSC_test3_Width),
    .TwoPhase(`TSC_TwoPhase)
) TSC_test3 (
    .SClkP(SClkP),
    .SClkN(SClkN),
    .SEnable(SEnable),
    .CfgIn(Cfg[`TSC_test3]),
    .SIn(TSC_test2_to_TSC_test3),
    .SOut(SOut)
);
//--------------------------------------------------------------------------------

endmodule
//--------------------------------------------------------------------------------

