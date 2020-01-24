#!/usr/bin/perl

# This script generates a scan chain according to scan fields defined in a
# scan chain configuration file. The generated scan chain requires the
# ReadSegment.v and WriteSegment.v modules

use strict;
use POSIX;

# Default Parameters
my $TwoPhase = 1;
my $ConfigLatch = 1;

if (@ARGV < 2)
{
    print "This script generates a scan chain according to scan fields defined in a\n" .
            "scan chain configuration file. The generated scan chain requires the\n" .
            "ReadSegment.v and WriteSegment.v modules. Optionally, this can also\n" .
            "generate a verilog macro file containing the scan chain definition.\n\n";
            
    print "USAGE: gen-scan-chain.pl CFGFILE OUTPUTFILE [DEFFILE] [DEFPREFIX]\n";
    exit(0);
}

my $cfgFile = $ARGV[0];
my $outFile = $ARGV[1];
my $defFile = $ARGV[2];
my $defPrefix = $ARGV[3];

# perl mode flag for parsing
my $perlMode = 0;

my $moduleName;
my @chainConfig;
my @signals;
my %param;
open CFGFILE, "<$cfgFile" or die "Cannot open scan chain configuration file '$cfgFile'!";

my $evalCode;

# Parse each line in the scan chain configuration file
foreach(<CFGFILE>)
{
    my $line = $_;
    chomp($line);
    
    # begin/end perl mode
    if ($line =~ /^\s*begin:perl\s*$/)
    {
        $perlMode = 1;
        $evalCode = "";
    }
    elsif ($line =~ /^\s*end:perl\s*$/)
    {
        $perlMode = 0;
        eval $evalCode or die "Expression evaluation error: $@Eval code: \n$evalCode\n";
    }
    # if in perl mode, evaluate the line as a perl expression
    elsif ($perlMode)
    {
        $evalCode .= $line . "\n";
    }
    # Module name of the generated scan chain
    elsif ($line =~ /^\s*Name\s*=\s*(\w+)\s*$/)
    {
        $moduleName = $1;
    }
    # Config field definition
    elsif ($line =~ /^\s*([\w]+)\s+([RW]?)\s+(\S+)\s+(\S+)\s*$/)
    {
        # Evaluate the field width expression
        my $fieldWidth = eval $3 or die "Expression evaluation error:\n    $3\n";
        # Evaluate the field multiplier expression
        my $fieldMult = eval $4 or die "Expression evaluation error:\n    $4\n";
        # Add to the list of config fields
        addField($1, $2, $fieldWidth, $fieldMult);
    }
        
}
close CFGFILE;

if (!$moduleName)
{
    $moduleName = 'ScanChain';
    printf("Warning: no scan chain module name given, defaulting to 'ScanChain'\n");
}

open OUTFILE, ">$outFile" or die "Cannot write to output verilog file '$outFile'!";

writeHeader();
writePorts();
writeParameters();
writeIODeclarations();
writeSignals();
writeSegInstances();
writeVerif();
writeEndModule();

close OUTFILE;

if ($defFile)
{
    open OUTFILE, ">$defFile" or die "Cannot write to definition file '$defFile'!";
    writeDefFile();
    close OUTFILE;
}

printf("Scan chain '%s' generated\n", $moduleName);

# Subroutines
sub writeHeader()
{
    writeCommentSeparator(0);
    printf(OUTFILE "// This file was auto generated with the command:\n");
    printf(OUTFILE "// gen-scan-chain.pl $cfgFile $outFile $defFile $defPrefix\n");
    printf(OUTFILE "// Config file contents:\n");
    printf(OUTFILE "//    %32s    %6s    %6s    %6s\n", "Field Name", "Dir", "Width", "Mult");
    writeCommentSeparator(0);
    my $chainLength = 0;
    for (my $i = 0; $i < @chainConfig; $i++)
    {
        # Total field width = field width x field multiplier
        my $totalFieldWidth = $chainConfig[$i][2] * $chainConfig[$i][3];        
        printf(OUTFILE "//    %32s    %6s    %6d    %6d\n", $chainConfig[$i][0], $chainConfig[$i][1], $chainConfig[$i][2], $chainConfig[$i][3]);
        # Sum chain length
        $chainLength = $chainLength + $totalFieldWidth;
    }
    printf(OUTFILE "//\n// Scan Chain Module Name = %s\n", $moduleName);
    printf(OUTFILE "// Scanchain Length = %d\n", $chainLength);
    writeCommentSeparator(0);
    printf(OUTFILE "\n`timescale 1ns/1ps\n\n");
}

sub writePorts()
{
    #Write fixed I/O
    printf(OUTFILE "module %s(\n", $moduleName);
    writeCommentHeader(2, "Scan Chain I/O");
        printf(OUTFILE
        "        SClkP,\n" .
        "        SClkN,\n" .
        "        SReset,\n" .
        "        SEnable,\n" .
        "        SUpdate,\n" .
        "        SIn,\n" .
        "        SOut,\n"
    );
    writeCommentSeparator(2);
    printf(OUTFILE "\n");
    
    #Write scan chain configuration I/O
    writeCommentHeader(2, "Configuration I/O");
    printf(OUTFILE "        %s,\n", "ScanBitsRd");
    printf(OUTFILE "        %s\n", "ScanBitsWr");
    writeCommentSeparator(2);
    printf(OUTFILE "    );\n\n");
}

sub writeParameters()
{
    writeCommentHeader(1, "Chain Parameters");
    printf(OUTFILE
        "    parameter TwoPhase =                            %d;\n" .
        "    parameter ConfigLatch =                         %d;\n",
        $TwoPhase, $ConfigLatch
    );
    writeCommentSeparator(1);
    printf(OUTFILE "\n");

    writeCommentHeader(1, "Configuration Constants");
    printf(OUTFILE "    localparam %-32s %s;\n", "ChainLength =", '`' . $defPrefix . 'ScanChainLength');
    for (my $i = 0; $i < @chainConfig; $i++)
    {
        # Total field width = field width x field multiplier
        my $totalFieldWidth = $chainConfig[$i][2] * $chainConfig[$i][3];        
        # Print localparam
        printf(OUTFILE "    localparam %-32s %d;\n", $chainConfig[$i][0] . "Width =", $totalFieldWidth);
    }
    writeCommentSeparator(1);
    printf(OUTFILE "\n");
}

sub writeIODeclarations
{
    writeCommentHeader(1, "Scan Chain I/O");
    printf(OUTFILE
        "    input wire                           SClkP;\n" .
        "    input wire                           SClkN;\n" .
        "    input wire                           SReset;\n" .
        "    input wire                           SEnable;\n" .
        "    input wire                           SUpdate;\n" .
        "    input wire                           SIn;\n" .
        "    output wire                          SOut;\n"

    );
    writeCommentSeparator(1);
    printf(OUTFILE "\n");
    writeCommentHeader(1, "Configuration I/O");
    printf(OUTFILE "    %-12s %-23s %s;\n", "input wire", "[ChainLength-1:0]", "ScanBitsRd");
    printf(OUTFILE "    %-12s %-23s %s;\n", "output wire", "[ChainLength-1:0]", "ScanBitsWr");
    writeCommentSeparator(1);
    printf(OUTFILE "\n");
}

sub writeSignals
{
    writeCommentHeader(1, "Signals");
    $signals[0] = "SIn";
    my $currentSeg = $chainConfig[0][0];
    for (my $i = 1; $i < @chainConfig; $i++)
    {
        $signals[$i] = $currentSeg . "To" . $chainConfig[$i][0];
        printf(OUTFILE "    %-12s %-23s %s;\n", "wire", "", $signals[$i]);
        $currentSeg = $chainConfig[$i][0];
    }
    $signals[@chainConfig] = "SOut";
    writeCommentSeparator(1);
    printf(OUTFILE "\n");
}

sub writeSegInstances
{
    writeCommentHeader(1, "Scan Segment Instantiations");
    for (my $i = 0; $i < @chainConfig; $i++)
    {
        # If it is a read-type type scan chain
        if ($chainConfig[$i][1] eq "R")
        {
            printf(OUTFILE
                "    ReadSegment             #       (   .PWidth         (%s),\n" .
                "                                        .TwoPhase       (TwoPhase))\n" .
                "        %-24s    (   .SClkP          (SClkP),\n" .
                "                                        .SClkN          (SClkN),\n" .
                "                                        .SEnable        (SEnable),\n" .
                "                                        .CfgIn          (%s),\n" .
                "                                        .SIn            (%s),\n" .
                "                                        .SOut           (%s));\n\n",
                $chainConfig[$i][0] . "Width", $chainConfig[$i][0] . "Seg",
                "ScanBitsRd[`$defPrefix$chainConfig[$i][0]]", $signals[$i], $signals[$i+1]
            );
        }
        # If it is a write-type type scan chain
        else
        {
            printf(OUTFILE
                "    WriteSegment             #      (   .PWidth         (%s),\n" .
                "                                        .TwoPhase       (TwoPhase),\n" .
                "                                        .ConfigLatch    (ConfigLatch))\n" .
                "        %-24s    (   .SClkP          (SClkP),\n" .
                "                                        .SClkN          (SClkN),\n" .
                "                                        .SReset         (SReset),\n" .
                "                                        .SEnable        (SEnable),\n" .
                "                                        .SUpdate        (SUpdate),\n" .
                "                                        .CfgOut         (%s),\n" .
                "                                        .SIn            (%s),\n" .
                "                                        .SOut           (%s));\n\n",
                $chainConfig[$i][0] . "Width", $chainConfig[$i][0] . "Seg",
                "ScanBitsWr[`$defPrefix$chainConfig[$i][0]]", $signals[$i], $signals[$i+1]
            );
        }
    }
    writeCommentSeparator(1);
    printf(OUTFILE "\n");
}

sub writeVerif
{
    writeCommentHeader(1, "For Testing");
    printf(OUTFILE "`ifdef NCVLOG\n");
    printf(OUTFILE "`endif\n");
    writeCommentSeparator(1);
}

sub writeDefFile
{
    writeHeader();
    writeCommentHeader(0, "Scan Chain Length");    
    # Calculate total scan chain length
    my $chainLength = 0;
    for (my $i = 0; $i < @chainConfig; $i++)
    {
        # Total field width = field width x field multiplier
        my $totalFieldWidth = $chainConfig[$i][2] * $chainConfig[$i][3];        
        $chainLength += $totalFieldWidth;
    }
    printf(OUTFILE "`define %-28s %d\n", $defPrefix . 'ScanChainLength', $chainLength);
    writeCommentSeparator(0);
    printf(OUTFILE "\n");

    writeCommentHeader(0, "Full Bit Vector Defs");
    my $curIndex = 0;
    for (my $i = 0; $i < @chainConfig; $i++)
    {   
        # Total field width = field width x field multiplier
        my $totalFieldWidth = $chainConfig[$i][2] * $chainConfig[$i][3];        
        # Print the define for the full field in the format of:
        # `define FIELDNAME(n)     HI:LO
        printf(OUTFILE "`define %-36s %6d:%-6d\n",             
            $defPrefix . $chainConfig[$i][0],
            $curIndex + $totalFieldWidth - 1, $curIndex);

        $curIndex += $totalFieldWidth;
    }    
    writeCommentSeparator(0);
    printf(OUTFILE "\n");
    writeCommentHeader(0, "Indexed Bit Vector Defs");
    $curIndex = 0;
    for (my $i = 0; $i < @chainConfig; $i++)
    {   
        # Total field width = field width x field multiplier
        my $totalFieldWidth = $chainConfig[$i][2] * $chainConfig[$i][3];        
        # Print the define for the field in the format of:
        # `define FIELDNAME(n)     (n * WIDTH + LO)+:WIDTH //  HI:LO
        printf(OUTFILE "`define %-36s (n * %-6d + %6d)+:%6d // %6d:%-6d\n",             
            $defPrefix . $chainConfig[$i][0] . "_idx(n)", $chainConfig[$i][2],
            $curIndex, $chainConfig[$i][2],
            $curIndex + $totalFieldWidth - 1, $curIndex);

        $curIndex += $totalFieldWidth;
    }
    writeCommentSeparator(0);
}

sub writeEndModule
{
    printf(OUTFILE "endmodule\n");
}

sub writeCommentSeparator
{
    my $string = "";
    for (my $i = 0; $i < $_[0]; $i++)
    {
        $string .= "    ";
    }
    
    $string .= "//";
    for (my $i = 0; $i < 91 - $_[0]*8; $i++)
    {
        $string .= "-";
    }
    printf(OUTFILE "%s\n", $string);
}

sub writeCommentHeader
{
    writeCommentSeparator($_[0]);
    my $string = "";
    for (my $i = 0; $i < $_[0]; $i++)
    {
        $string .= "    ";
    }
    $string .= "//";
    printf(OUTFILE "%s    %s\n", $string, $_[1]);
    writeCommentSeparator($_[0]);
}

sub addField
{
    my $fieldName = $_[0];
    my $fieldDir = $_[1];
    my $fieldWidth = $_[2];
    my $fieldMult = $_[3];

    if (!$fieldWidth) {die "Field width for '$fieldName' cannot be 0 or undefined!"};
    if (!$fieldMult) {die "Field multiplier for '$fieldName' cannot be 0 or undefined!"};

    # Add to the list of config fields
    push(@chainConfig, [$fieldName, $fieldDir, $fieldWidth, $fieldMult]);
}

sub log2
{
    return ceil(log($_[0])/log(2));
}
