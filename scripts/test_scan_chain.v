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
// name: test_scan_chain
// parameters:
//   x: 6
//   y: 7
// prefix: TSC
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
    inout wire [`TSC_TotalLength] Cfg
);

