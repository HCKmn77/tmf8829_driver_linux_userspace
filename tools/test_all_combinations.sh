#!/bin/bash

# Script to test all combinations of Makefile macro definitions

# Get script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=8
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test a specific combination
test_combination() {
    local json="$1"
    local histogram="$2"
    local keystone="$3"
    local test_num="$4"

    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Test ${test_num}/${TOTAL_TESTS}${NC}"
    echo "ENABLE_JSON_LOGGING=$json"
    echo "ENABLE_HISTOGRAM=$histogram"
    echo "ENABLE_KEYSTONE=$keystone"
    echo -e "${YELLOW}========================================${NC}"

    # Backup original Makefile
    cp Makefile Makefile.backup

    # Modify Makefile based on the combination
    if [ "$json" = "1" ]; then
        sed -i 's/^#ENABLE_JSON_LOGGING = 1$/ENABLE_JSON_LOGGING = 1/' Makefile
        sed -i 's/^ENABLE_JSON_LOGGING = 1$/ENABLE_JSON_LOGGING = 1/' Makefile
    else
        sed -i 's/^ENABLE_JSON_LOGGING = 1$/#ENABLE_JSON_LOGGING = 1/' Makefile
    fi

    if [ "$histogram" = "1" ]; then
        sed -i 's/^#ENABLE_HISTOGRAM = 1$/ENABLE_HISTOGRAM = 1/' Makefile
        sed -i 's/^ENABLE_HISTOGRAM = 1$/ENABLE_HISTOGRAM = 1/' Makefile
    else
        sed -i 's/^ENABLE_HISTOGRAM = 1$/#ENABLE_HISTOGRAM = 1/' Makefile
    fi

    if [ "$keystone" = "1" ]; then
        sed -i 's/^#ENABLE_KEYSTONE = 1$/ENABLE_KEYSTONE = 1/' Makefile
        sed -i 's/^ENABLE_KEYSTONE = 1$/ENABLE_KEYSTONE = 1/' Makefile
    else
        sed -i 's/^ENABLE_KEYSTONE = 1$/#ENABLE_KEYSTONE = 1/' Makefile
    fi

    # Clean and build
    make clean > /dev/null 2>&1
    if make > build.log 2>&1; then
        echo -e "${GREEN}✓ Test ${test_num} PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ Test ${test_num} FAILED${NC}"
        echo "Error details:"
        cat build.log
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    # Restore original Makefile
    mv Makefile.backup Makefile

    # Clean up for next test
    make clean > /dev/null 2>&1
    rm -f build.log

    echo ""
}

# Test all 8 combinations
echo -e "${YELLOW}Starting compilation tests for all Makefile macro combinations${NC}"
echo ""

# Test 1: All enabled
test_combination "1" "1" "1" 1

# Test 2: JSON only
test_combination "1" "0" "0" 2

# Test 3: Histogram only
test_combination "0" "1" "0" 3

# Test 4: Keystone only
test_combination "0" "0" "1" 4

# Test 5: JSON + Histogram
test_combination "1" "1" "0" 5

# Test 6: JSON + Keystone
test_combination "1" "0" "1" 6

# Test 7: Histogram + Keystone
test_combination "0" "1" "1" 7

# Test 8: All disabled
test_combination "0" "0" "0" 8

# Summary
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "Total tests: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
