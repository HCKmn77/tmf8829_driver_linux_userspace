#!/bin/bash
# Run TMF8829 with different resolutions
# Rename the saved JSON files with mode information

# Mode definitions:
# 0: 8x8
# 1: 8x8 long range
# 2: 8x8 high accuracy
# 3: 8x8 dual mode
# 4: 8x8 long range dual mode
# 5: 16x16
# 6: 16x16 high accuracy
# 7: 16x16 dual mode
# 8: 32x32
# 9: 32x32 high accuracy
# 10: 32x32 dual mode
# 11: 48x32
# 12: 48x32 high accuracy
# 13: 48x32 dual mode

# Mode names for renaming
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

# Default parameters
DURATION_SET=false
DURATION=""
SAVE_JSON=false
SAVE_HISTO=false

# Parse command line arguments
while getopts "t:jh" opt; do
    case $opt in
        t)
            DURATION_SET=true
            DURATION=$OPTARG
            ;;
        j)
            SAVE_JSON=true
            ;;
        h)
            SAVE_HISTO=true
            ;;
        \?)
            echo "Usage: $0 [-t duration] [-j] [-h]"
            echo "  -t duration: duration for each mode in seconds (default: 5, use program default)"
            echo "  -j: save JSON files and rename them with mode information"
            echo "  -h: save histogram data"
            exit 1
            ;;
    esac
done

# Executable path
PROGRAM="./tmf8829"

# Check if program exists
if [ ! -f "$PROGRAM" ]; then
    echo "Error: $PROGRAM not found"
    exit 1
fi

# Create output directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="all_modes_test_logs_${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

# Log file path
LOG_FILE="${OUTPUT_DIR}/all_modes.log"

{
    echo "Starting multi-resolution test..."
    if [ "$DURATION_SET" = true ]; then
        echo "Each mode will run for ${DURATION} seconds"
    else
        echo "Each mode will run for default duration (5 seconds)"
    fi
    echo "Save JSON: $SAVE_JSON"
    echo "Save Histogram: $SAVE_HISTO"
    echo "Output directory: $OUTPUT_DIR"
    echo "=============================================="
} | tee -a "$LOG_FILE"

# Run each mode
for mode in 0 1 2 3 4 5 6 7 8 9 10 11 12 13; do
    mode_name="${MODE_NAMES[$mode]}"
    echo ""
    echo "----------------------------------------------"
    echo "Running mode $mode: $mode_name"
    echo "----------------------------------------------"
    
    # Build command arguments
    CMD_ARGS="-m -d $mode"

    # Add duration if specified
    if [ "$DURATION_SET" = true ]; then
        CMD_ARGS="$CMD_ARGS -t $DURATION"
    fi

    # Add histogram option if enabled
    if [ "$SAVE_HISTO" = true ]; then
        CMD_ARGS="$CMD_ARGS -h"
    fi
    
    # Add JSON option if enabled
    if [ "$SAVE_JSON" = true ]; then
        # Run the program with JSON option
        sudo $PROGRAM $CMD_ARGS -j
    else
        # Run the program without JSON option
        sudo $PROGRAM $CMD_ARGS
    fi

    # Rename JSON files if enabled
    if [ "$SAVE_JSON" = true ]; then
        # Build suffix based on whether histogram is enabled
        if [ "$SAVE_HISTO" = true ]; then
            suffix="${mode_name}_histo"
        else
            suffix="$mode_name"
        fi

        # Find the latest json.gz file
        latest_file=$(ls -t tmf8829_UID*.json.gz 2>/dev/null | head -n 1)

        if [ -n "$latest_file" ]; then
            # Extract the base name without extension
            base="${latest_file%.json.gz}"
            new_name="${base}-${suffix}.json.gz"
            echo "Renaming: $latest_file -> $new_name"
            mv "$latest_file" "$new_name"
            # Move to output directory
            mv "$new_name" "$OUTPUT_DIR/"
        fi
    fi
    
    echo "Mode $mode ($mode_name) completed"
    
    # Small delay between tests
    sleep 2
done | tee -a "$LOG_FILE"

echo ""
echo "=============================================="
echo "All tests completed!" | tee -a "$LOG_FILE"

if [ "$SAVE_JSON" = true ]; then
    if [ "$SAVE_HISTO" = true ]; then
        echo "Generated JSON files with histogram:" | tee -a "$LOG_FILE"
    else
        echo "Generated JSON files:" | tee -a "$LOG_FILE"
    fi
    ls -la "${OUTPUT_DIR}"/*.json.gz 2>/dev/null | tee -a "$LOG_FILE"
fi

echo ""
echo "Test results saved to: $OUTPUT_DIR" | tee -a "$LOG_FILE"
