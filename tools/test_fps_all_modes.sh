#!/bin/bash

# FPS automated test script
# Tests all modes with optional histogram and JSON logging
# Each mode runs for 5 seconds

# Default parameters
ITERATIONS=600
PERIOD=33
TIMEOUT=5
ENABLE_HISTO=0
ENABLE_JSON=0
MODE_RANGE="0 1 2 3 4 5 6 7 8 9 10 11 12 13"

# Print usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "    -H           Show this help message"
    echo "    -h           Enable histogram output (-h flag for tmf8829)"
    echo "    -j           Enable JSON logging (-j flag for tmf8829)"
    echo "    -i <num>     Iterations (default: 600)"
    echo "    -p <num>     Period in ms (default: 33)"
    echo "    -t <num>     Timeout in seconds (default: 5)"
    echo "    -m <modes>   Mode range to test (default: 0-13, e.g., \"0 3 8 11\")"
    echo ""
    echo "Examples:"
    echo "    $0                # Run all modes without histogram and JSON"
    echo "    $0 -h             # Run all modes with histogram"
    echo "    $0 -j             # Run all modes with JSON logging"
    echo "    $0 -h -j          # Run all modes with histogram and JSON"
    echo "    $0 -H -j -i 1000  # Run all modes with histogram, JSON, 1000 iterations"
    echo "    $0 -m \"0 3 8 11\"   # Run only modes 0, 3, 8, 11"
    exit 0
}

# Parse command line options
while getopts "hHjJi:p:t:m:" opt; do
    case $opt in
        H) usage ;;
        h) ENABLE_HISTO=1 ;;
        j) ENABLE_JSON=1 ;;
        i) ITERATIONS=$OPTARG ;;
        p) PERIOD=$OPTARG ;;
        t) TIMEOUT=$OPTARG ;;
        m) MODE_RANGE=$OPTARG ;;
        *) echo "Invalid option: -$opt" >&2; exit 1 ;;
    esac
done

OUTPUT_FILE="fps_test_results_$(date +%Y%m%d_%H%M%S).csv"

# CSV header
echo "Mode,Resolution,Histogram,JSON,Iterations,Period,Frames,Duration(s),FPS" > "$OUTPUT_FILE"

# Mode definitions
declare -A MODE_NAMES
MODE_NAMES[0]="8x8"
MODE_NAMES[1]="8x8_long_range"
MODE_NAMES[2]="8x8_high_accuracy"
MODE_NAMES[3]="8x8_dual"
MODE_NAMES[4]="8x8_long_range_dual"
MODE_NAMES[5]="16x16"
MODE_NAMES[6]="16x16_high_accuracy"
MODE_NAMES[7]="16x16_dual"
MODE_NAMES[8]="32x32"
MODE_NAMES[9]="32x32_high_accuracy"
MODE_NAMES[10]="32x32_dual"
MODE_NAMES[11]="48x32"
MODE_NAMES[12]="48x32_high_accuracy"
MODE_NAMES[13]="48x32_dual"

# Build flags for tmf8829
EXTRA_FLAGS=""
[ $ENABLE_HISTO -eq 1 ] && EXTRA_FLAGS="$EXTRA_FLAGS -h"
[ $ENABLE_JSON -eq 1 ] && EXTRA_FLAGS="$EXTRA_FLAGS -j"

# Run test for a specific mode
run_test() {
    local mode=$1
    local mode_name=$2

    # Run the test and extract FPS statistics line
    local result=$(sudo ./tmf8829 -m $EXTRA_FLAGS -i $ITERATIONS -p $PERIOD -t $TIMEOUT -d $mode 2>&1 | grep "FPS Statistics")

    # Parse the result
    if echo "$result" | grep -q "FPS Statistics:"; then
        local frames=$(echo "$result" | sed 's/.*FPS Statistics: \([0-9]*\) frames.*/\1/')
        local duration=$(echo "$result" | sed 's/.*in \([0-9.]*\) seconds.*/\1/')
        local fps=$(echo "$result" | sed 's/.*= \([0-9.]*\) FPS.*/\1/')
        local histo_str=$( [ $ENABLE_HISTO -eq 1 ] && echo "ON" || echo "OFF" )
        local json_str=$( [ $ENABLE_JSON -eq 1 ] && echo "ON" || echo "OFF" )
        echo "$mode,$mode_name,$histo_str,$json_str,$ITERATIONS,$PERIOD,$frames,$duration,$fps" >> "$OUTPUT_FILE"
        printf "  Mode %d (%s): %.2f FPS\n" "$mode" "$mode_name" "$fps"
    else
        local histo_str=$( [ $ENABLE_HISTO -eq 1 ] && echo "ON" || echo "OFF" )
        local json_str=$( [ $ENABLE_JSON -eq 1 ] && echo "ON" || echo "OFF" )
        printf "  Mode %d (%s): FAILED\n" "$mode" "$mode_name"
        echo "$mode,$mode_name,$histo_str,$json_str,$ITERATIONS,$PERIOD,ERROR,ERROR,ERROR" >> "$OUTPUT_FILE"
    fi
}

echo "========================================="
echo "FPS Automated Test Configuration"
echo "========================================="
echo "Iterations:    $ITERATIONS"
echo "Period:        $PERIOD ms"
echo "Timeout:       $TIMEOUT seconds"
echo "Histogram:     $( [ $ENABLE_HISTO -eq 1 ] && echo "ON" || echo "OFF" )"
echo "JSON:          $( [ $ENABLE_JSON -eq 1 ] && echo "ON" || echo "OFF" )"
echo "Modes:         ${MODE_RANGE// /,}"
echo "Total modes:   $(echo $MODE_RANGE | wc -w)"
echo "========================================="
echo ""
echo "Starting FPS automated test..."
echo ""

# Test each mode
for mode in $MODE_RANGE; do
    mode_name="${MODE_NAMES[$mode]}"
    echo "Testing mode $mode ($mode_name)..."
    run_test "$mode" "$mode_name"
    echo ""
done

echo "========================================="
echo "Test completed!"
echo "Results saved to: $OUTPUT_FILE"
echo ""

# Print summary table
echo "Summary:"
printf "%-28s | %-8s | %-8s | %-6s | %-6s\n" "Mode" "Histogram" "JSON" "Frames" "FPS"
echo "--------------------------------------------------------------------------"
awk -F',' 'NR>1 {printf "%-28s | %-8s | %-8s | %-6s | %-6s\n", $1" ("$2")", $3, $4, $7, $9}' "$OUTPUT_FILE"