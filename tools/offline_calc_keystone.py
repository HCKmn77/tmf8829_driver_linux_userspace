#!/usr/bin/env python3
"""
Offline keystone error calculation from CSV files containing raw distance data.

Reads pre-recorded CSV files with raw distance values per pixel and true rotation stage
angles, then performs offline keystone calculation (plane fitting) to compute X/Y errors.
Plots combined X and Y error comparison across all resolutions.

Usage:
  python offline_calc_keystone.py -i INPUT_DIR [-f]

Input:
  - INPUT_DIR: directory containing keystone_error_{resolution}.csv files
    Each CSV contains columns: timestamp, actual_x, actual_y, keystone_x, keystone_y,
    keystone_z, error_x, error_y, frame_number, warnings, distance_1..N, snr_1..N

Output (in INPUT_DIR):
  - offline_keystone_error.csv: recalculated error results for all resolutions
  - offline_x_error_combined.png: combined X error plot across all resolutions
  - offline_y_error_combined.png: combined Y error plot across all resolutions

Options:
  -f, --fov_correction  Enable FOV correction when computing XYZ coordinates
                         (default: disabled)
  -l, --focal_length    Focal length in micrometers for FOV calibration
                         (default: 560.0, range: 520.0 to 600.0)
"""

import os
import sys
import argparse
import csv
import re
import math
import matplotlib.pyplot as plt


# ============================================================================
# Zone patterns for different resolutions (from tmf8829_keystone.c)
# ============================================================================

PIXEL_ARRAY_8X8 = [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 1, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 1, 0, 1, 1, 0, 1, 0,
    0, 1, 0, 1, 1, 0, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 1, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
]

PIXEL_ARRAY_16X16 = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0,
    0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]

PIXEL_ARRAY_32X32 = [
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]

PIXEL_ARRAY_48X32 = [
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]

def get_zone_pattern(rows, cols):
    """Get zone pattern array for a given resolution."""
    size = rows * cols
    if size == 64:
        return PIXEL_ARRAY_8X8
    elif size == 256:
        return PIXEL_ARRAY_16X16
    elif size == 1024:
        return PIXEL_ARRAY_32X32
    elif size == 1536:
        return PIXEL_ARRAY_48X32
    else:
        raise ValueError(f"Unsupported resolution: {rows}x{cols} (size={size})")


def parse_resolution(res_str):
    """Parse resolution string into (rows, cols).

    The CSV file naming uses 'NxM' format:
      - '8x8'   -> (8, 8)   square
      - '16x16' -> (16, 16) square
      - '32x32' -> (32, 32) square
      - '32x48' -> (32, 48) rectangular (32 rows x 48 cols, TMF8829 48x32 mode)
    """
    parts = res_str.lower().split('x')
    if len(parts) != 2:
        raise ValueError(f"Invalid resolution format: {res_str}")
    val_a, val_b = int(parts[0]), int(parts[1])
    # Detect 48-wide modes (file named as Nx48 or 48xN)
    if val_a == 48 or val_b == 48:
        return (32, 48)  # 32 rows x 48 cols
    elif val_a == val_b:
        return (val_a, val_b)
    else:
        # Default: assume first is rows, second is cols based on common convention
        # But our data files use '32x48' to mean 32x48 grid
        return (val_a, val_b)


# ============================================================================
# XYZ coordinate calculation (ported from tmf8829CalcPixelXYZ)
# ============================================================================

def calc_pixel_xyz(col, row, fp_mode, distance, fov_correction=None, focal_length=560.0):
    """Calculate 3D point cloud coordinates from distance measurement.

    Ported from tmf8829CalcPixelXYZ() in tmf8829_frameparser.c.

    When fov_correction is None or not provided: uses the ORIGINAL formula
    (pre-FOV-correction commit) with NO offset applied.

    When fov_correction is an integer value: applies FOV correction offset,
    matching the post-commit C code behavior.

    Args:
        focal_length: focal length in micrometers (default: 560.0).
                      Actual device may vary ±40μm, affecting FOV calculation.
                      Smaller focal_length → wider FOV → larger angles.
    """
    rows, cols_res = fp_mode

    span_x = cols_res * 3.0 / 4.0
    span_y = float(rows)

    # Normalized coordinates from center
    x_norm = (float(col) - cols_res / 2.0 + 0.5) / span_x
    y_norm = (float(row) - rows / 2.0 + 0.5) / span_y

    # Apply FOV correction only when explicitly enabled
    if fov_correction is not None:
        fov_corr_x = fov_correction & 0x03
        fov_corr_y = (fov_correction >> 2) & 0x03

        # FOV correction offset: (value - 1.5) / 2.5 / 16
        fov_corrx = ((float(fov_corr_x) - 1.5) / 2.5) / 16.0
        fov_corry = ((float(fov_corr_y) - 1.5) / 2.5) / 16.0

        x_norm -= fov_corrx
        y_norm -= fov_corry

    # Apply focal length calibration:
    # The angle per unit x_norm is proportional to (SPAD_pitch / focal_length).
    # Scale x_norm and y_norm by the ratio of nominal to actual focal length.
    # This correctly adjusts the FOV: shorter focal length → wider FOV.
    FOCAL_LENGTH_NOM = 560.0
    if focal_length != FOCAL_LENGTH_NOM:
        scale = FOCAL_LENGTH_NOM / focal_length
        x_norm *= scale
        y_norm *= scale

    depth_factor = math.sqrt(1.0 + x_norm * x_norm + y_norm * y_norm)
    depth = distance / depth_factor

    return (depth * x_norm, depth * y_norm, depth)


# ============================================================================
# Plane fitting and angle calculation (ported from tmf8829_keystone.c)
# ============================================================================

KEYSTONE_PI = 3.14159265
KEYSTONE_LINEAR_NUMBER = 2  # X, Y dimensions


def _linear_regression(xy, zz, m, n):
    """Ordinary least squares linear regression via Gaussian elimination.

    Args:
        xy: list of m lists, each of length n (independent vars)
        zz: list of length n (dependent variable Z values)
        m: number of independent variables (2 for plane fitting)
        n: number of valid data points

    Returns:
        coef: list of m+1 coefficients [a, b, c] where z = a*x + b*y + c
    """
    mm = m + 1
    # Build normal equation matrix: A^T * A * coef = A^T * z
    mat = [[0.0] * (mm + 1) for _ in range(mm)]  # augmented matrix

    # Last column of A^T*A is sum of ones (for intercept term), last of RHS is sum(z)
    mat[mm - 1][mm - 1] = float(n)

    for j in range(m):
        s = sum(xy[j][i] for i in range(n))
        mat[m][j] = s
        mat[j][m] = s

    for i in range(m):
        for j in range(i, m):
            s = sum(xy[i][k] * xy[j][k] for k in range(n))
            mat[j][i] = s
            mat[i][j] = s

    # RHS vector (last column of augmented matrix)
    rhs_idx = mm
    mat[mm - 1][rhs_idx] = sum(zz[i] for i in range(n))
    for i in range(m):
        mat[i][rhs_idx] = sum(xy[i][j] * zz[j] for j in range(n))

    # Gaussian elimination with partial pivoting
    for col in range(mm):
        # Find pivot
        max_val = abs(mat[col][col])
        max_row = col
        for row in range(col + 1, mm):
            if abs(mat[row][col]) > max_val:
                max_val = abs(mat[row][col])
                max_row = row
        mat[col], mat[max_row] = mat[max_row], mat[col]

        if abs(mat[col][col]) < 1e-15:
            continue
        for row in range(col + 1, mm):
            factor = mat[row][col] / mat[col][col]
            for j in range(col, mm + 1):
                mat[row][j] -= factor * mat[col][j]

    # Back substitution
    coef = [0.0] * mm
    for i in range(mm - 1, -1, -1):
        coef[i] = mat[i][rhs_idx]
        for j in range(i + 1, mm):
            coef[i] -= mat[i][j] * coef[j]
        if abs(mat[i][i]) > 1e-15:
            coef[i] /= mat[i][i]
    return coef


def _vector_dot(a, b, n):
    return sum(a[i] * b[i] for i in range(n))


def _vector_norm(x, n=None):
    """Calculate Euclidean norm of a vector. The n parameter is accepted for API compatibility but ignored."""
    return math.sqrt(sum(v * v for v in x))


def _calc_plane_angle(plane_n):
    """Calculate angles from plane normal vector. Returns (angle_x, angle_y, angle_z)."""
    bases = ([1., 0., 0.], [0., 1., 0.], [0., 0., 1.])
    n = KEYSTONE_LINEAR_NUMBER + 1  # 3

    ax = 90 - math.acos(_vector_dot(plane_n, bases[0], n) /
                        (_vector_norm(plane_n, n) * _vector_norm(bases[0], n))) * 180 / KEYSTONE_PI
    ay = math.acos(_vector_dot(plane_n, bases[1], n) /
                   (_vector_norm(plane_n, n) * _vector_norm(bases[1], n))) * 180 / KEYSTONE_PI - 90
    az = 90 - math.acos(_vector_dot(plane_n, bases[2], n) /
                        (_vector_norm(plane_n, n) * _vector_norm(bases[2], n))) * 180 / KEYSTONE_PI
    return (ax, ay, az)


def do_plane_fit(data_points):
    """Perform plane fitting on XYZ points to get keystone angles.

    Args:
        data_points: list of dicts/objects with 'x', 'y', 'z' fields (in mm)

    Returns:
        (angle_x, angle_y, angle_z) in degrees, or (0, 0, 0) if insufficient data
    """
    valid = [(p['x'], p['y'], p['z']) for p in data_points
             if not (p['x'] == 0 and p['y'] == 0 and p['z'] == 0)]

    if len(valid) < 3:
        return (0.0, 0.0, 0.0)

    n_pts = len(valid)
    xy = [[valid[i][j] for i in range(n_pts)] for j in range(KEYSTONE_LINEAR_NUMBER)]
    zz = [valid[i][2] for i in range(n_pts)]  # z values

    coef = _linear_regression(xy, zz, KEYSTONE_LINEAR_NUMBER, n_pts)
    if coef is None or len(coef) < 3:
        return (0.0, 0.0, 0.0)

    # Plane coefficients: z = coef[0]*x + coef[1]*y + coef[2]
    # Normal vector: (-coef[0], -coef[1], 1), normalized
    csqrt = math.sqrt(coef[0]**2 + coef[1]**2 + 1.0)
    if csqrt < 1e-15:
        return (0.0, 0.0, 0.0)

    plane_n = [-coef[0] / csqrt, -coef[1] / csqrt, 1.0 / csqrt]
    return _calc_plane_angle(plane_n)


# ============================================================================
# Offline keystone processing
# ============================================================================

def process_csv_row(row_data, rows, cols, use_fov_correction=False, fov_value=0,
                    all_zones=False, snr_threshold=20, focal_length=560.0):
    """Process a single CSV row: extract distances, compute XYZ, do plane fitting.

    Args:
        row_data: dict from csv.DictReader (contains distance_1..N etc.)
        rows, cols: resolution
        use_fov_correction: whether to apply FOV correction in XYZ calculation
        fov_value: FOV correction byte value (default 0 = no correction)
        all_zones: if True, use all non-zero pixels instead of zone pattern only
        snr_threshold: minimum SNR for pixel inclusion (only with -a/--all_zones)
        focal_length: focal length in micrometers (default: 560.0)

    Returns:
        (keystone_x, keystone_y, keystone_z) angles in degrees
    """
    num_pixels = rows * cols

    # Extract distance values from row
    distances = []
    for i in range(1, num_pixels + 1):
        key = 'distance_%d' % i
        try:
            d = float(row_data.get(key, 0))
        except (ValueError, TypeError):
            d = 0.0
        distances.append(d)

    # Extract SNR values from row (may not exist in older CSVs)
    snrs = []
    has_snr_data = True
    for i in range(1, num_pixels + 1):
        key = 'snr_%d' % i
        try:
            s = float(row_data.get(key, -1))
        except (ValueError, TypeError):
            s = -1.0
            has_snr_data = False
        snrs.append(s)

    # Get zone pattern
    zone_pattern = get_zone_pattern(rows, cols)

    # Build XYZ data for plane fitting
    fit_data = []
    skipped_snr = 0
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c

            if all_zones:
                # All-zones mode: use any non-zero pixel (SNR-filtered)
                dist = distances[idx]
                if dist <= 0:
                    continue
                if has_snr_data and snrs[idx] < snr_threshold:
                    skipped_snr += 1
                    continue
            else:
                # Zone-pattern mode: only pixels selected by the zone pattern
                if not zone_pattern[idx]:
                    continue
                dist = distances[idx]
                if dist <= 0:
                    continue

            fov = fov_value if use_fov_correction else None
            px, py, pz = calc_pixel_xyz(c, r, (rows, cols), dist, fov, focal_length)
            fit_data.append({'x': px, 'y': py, 'z': pz})

    # if all_zones and skipped_snr > 0:
    #     print("    [all_zones mode] %d pixel(s) excluded by SNR threshold (< %.1f)" %
    #           (skipped_snr, snr_threshold))

    # Perform plane fitting
    kx, ky, kz = do_plane_fit(fit_data)
    return (kx, ky, kz)


def find_csv_files(input_dir):
    """Find all keystone_error_*.csv files in input directory."""
    csv_files = []
    for fname in os.listdir(input_dir):
        if re.match(r'keystone_error_.+\.csv$', fname):
            csv_files.append(os.path.join(input_dir, fname))
    return sorted(csv_files)


def process_csv_file(csv_path, use_fov_correction=False, fov_value=0,
                      all_zones=False, snr_threshold=20, focal_length=560.0):
    """Process one keystone error CSV file and recalculate errors offline.

    Returns:
        resolution_str: e.g. '8x8', '16x16'
        results: list of dicts with recalculated error data
    """
    basename = os.path.basename(csv_path)
    match = re.match(r'keystone_error_(.+)\.csv$', basename)
    if not match:
        print("Warning: Cannot extract resolution from %s, skipping." % basename)
        return None, []

    res_str = match.group(1)
    rows, cols = parse_resolution(res_str)
    num_pixels = rows * cols

    mode_desc = "all_zones (SNR>=%.1f)" % snr_threshold if all_zones else "zone_pattern"
    print("Processing %s: resolution=%s, grid=%dx%d, pixels=%d, mode=%s" %
          (basename, res_str, rows, cols, num_pixels, mode_desc))

    results = []
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                actual_x = float(row.get('actual_x', 0))
                actual_y = float(row.get('actual_y', 0))
            except (ValueError, TypeError):
                continue

            # Recalculate keystone angles offline from raw distances
            kx, ky, kz = process_csv_row(
                row, rows, cols,
                use_fov_correction=use_fov_correction,
                fov_value=fov_value,
                all_zones=all_zones,
                snr_threshold=snr_threshold,
                focal_length=focal_length
            )

            error_x = kx - actual_x
            error_y = ky - actual_y

            results.append({
                'timestamp': row.get('timestamp', ''),
                'actual_x': actual_x,
                'actual_y': actual_y,
                'keystone_x': kx,
                'keystone_y': ky,
                'keystone_z': kz,
                'error_x': error_x,
                'error_y': error_y,
            })

    print("  -> %d records processed" % len(results))
    return res_str, results


def compute_error_stats(results):
    """Group errors by (actual_x, actual_y) and compute median/min/max/count."""
    error_dict = {}
    for r in results:
        key = (r['actual_x'], r['actual_y'])
        error_dict.setdefault(key, []).append((r['error_x'], r['error_y']))

    def median(vals):
        s = sorted(vals)
        n = len(s)
        return (s[n//2 - 1] + s[n//2]) / 2 if n % 2 == 0 else s[n//2]

    stats_by_key = {}
    for key, errs in error_dict.items():
        exs = [e[0] for e in errs]
        eys = [e[1] for e in errs]
        stats_by_key[key] = {
            'median_x': median(exs), 'min_x': min(exs), 'max_x': max(exs),
            'median_y': median(eys), 'min_y': min(eys), 'max_y': max(eys),
            'count': len(errs),
        }
    return stats_by_key


# ============================================================================
# Plotting functions (similar style to plot_x_error_combined.py)
# ============================================================================

def plot_combined_errors(all_data, input_dir, use_fov_correction, all_zones=False, snr_threshold=20, focal_length=560.0):
    """Plot combined X and Y error across all resolutions."""
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

    fov_tag = "_fov_corr" if use_fov_correction else ""
    zone_tag = "_allzones_snr%d" % int(snr_threshold) if all_zones else ""
    fl_tag = "_fl%d" % int(focal_length) if focal_length != 560.0 else ""

    # Build descriptive title suffix
    parts = []
    if use_fov_correction:
        parts.append("FOV correction")
    if all_zones:
        parts.append("all zones (SNR>=%.0f)" % snr_threshold)
    else:
        parts.append("zone pattern")
    if focal_length != 560.0:
        parts.append("f=%.1fum" % focal_length)
    title_suffix = " (" + ", ".join(parts) + ")"

    # --- X Error Plot ---
    plt.figure(figsize=(12, 7))
    for idx, (resolution, data) in enumerate(sorted(all_data.items())):
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        ax_vals = data['actual_x']
        med_x = data['median_x']
        lo_x = [med_x[i] - data['min_x'][i] for i in range(len(ax_vals))]
        hi_x = [data['max_x'][i] - med_x[i] for i in range(len(ax_vals))]
        plt.errorbar(ax_vals, med_x, yerr=[lo_x, hi_x],
                     marker=marker, linestyle='-', capsize=3,
                     color=color, label=resolution, markersize=5, linewidth=1.5, elinewidth=1)
    plt.xlabel('Actual X angle (deg)', fontsize=12)
    plt.ylabel('X error (deg)', fontsize=12)
    plt.title('Offline Keystone X Error vs Actual X Angle (All Resolutions)%s\n'
              'Error bars: min ~ max, dot: median' % title_suffix, fontsize=13)
    plt.legend(title='Resolution', loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    out_path = os.path.join(input_dir, 'offline_x_error_combined%s%s%s.png' % (fov_tag, zone_tag, fl_tag))
    plt.savefig(out_path, dpi=300)
    print("X error plot saved to %s" % out_path)
    plt.close()

    # --- Y Error Plot ---
    plt.figure(figsize=(12, 7))
    for idx, (resolution, data) in enumerate(sorted(all_data.items())):
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        ax_vals = data['actual_x']
        med_y = data['median_y']
        lo_y = [med_y[i] - data['min_y'][i] for i in range(len(ax_vals))]
        hi_y = [data['max_y'][i] - med_y[i] for i in range(len(ax_vals))]
        plt.errorbar(ax_vals, med_y, yerr=[lo_y, hi_y],
                     marker=marker, linestyle='-', capsize=3,
                     color=color, label=resolution, markersize=5, linewidth=1.5, elinewidth=1)
    plt.xlabel('Actual X angle (deg)', fontsize=12)
    plt.ylabel('Y error (deg)', fontsize=12)
    plt.title('Offline Keystone Y Error vs Actual X Angle (All Resolutions)%s\n'
              'Error bars: min ~ max, dot: median' % title_suffix, fontsize=13)
    plt.legend(title='Resolution', loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    out_path = os.path.join(input_dir, 'offline_y_error_combined%s%s%s.png' % (fov_tag, zone_tag, fl_tag))
    plt.savefig(out_path, dpi=300)
    print("Y error plot saved to %s" % out_path)
    plt.close()


def aggregate_stats_for_plot(results):
    """Aggregate error statistics per unique actual_x value for plotting.

    Returns dict with keys: actual_x, median_x, min_x, max_x, median_y, min_y, max_y, count
    """
    error_dict = {}
    for r in results:
        key = (r['actual_x'], r['actual_y'])
        error_dict.setdefault(key, []).append((r['error_x'], r['error_y']))

    def median_fn(vals):
        s = sorted(vals)
        n = len(s)
        return (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]

    # Group by actual_x (assuming actual_y is constant within each group)
    x_groups = {}
    for (ax, ay), errs in error_dict.items():
        x_groups.setdefault(ax, []).extend(errs)

    sorted_x = sorted(x_groups.keys())
    med_x, mn_x, mx_x = [], [], []
    med_y, mn_y, my_y = [], [], []
    counts = []
    for ax in sorted_x:
        errs = x_groups[ax]
        exs = [e[0] for e in errs]
        eys = [e[1] for e in errs]
        med_x.append(median_fn(exs))
        mn_x.append(min(exs))
        mx_x.append(max(exs))
        med_y.append(median_fn(eys))
        mn_y.append(min(eys))
        my_y.append(max(eys))
        counts.append(len(errs))

    return {
        'actual_x': sorted_x,
        'median_x': med_x, 'min_x': mn_x, 'max_x': mx_x,
        'median_y': med_y, 'min_y': mn_y, 'max_y': my_y,
        'count': counts,
    }


# ============================================================================
# Main
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description='Offline keystone error calculation from CSV files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python offline_calc_keystone.py -i ./data/keystone/0415/analysis/
  python offline_calc_keystone.py -i ./data/keystone/0415/analysis/ -f
  python offline_calc_keystone.py -i ./data/keystone/0415/analysis/ -f -v 0x02
  python offline_calc_keystone.py -i ./data/keystone/0415/analysis/ -a
  python offline_calc_keystone.py -i ./data/keystone/0415/analysis/ -a -s 20
  python offline_calc_keystone.py -i ./data/keystone/0415/analysis/ -l 540.0
        """,
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input directory containing keystone_error_{resolution}.csv files '
             '(one per resolution: 8x8, 16x16, 32x32, 32x48)'
    )
    parser.add_argument(
        '-f', '--fov_correction',
        action='store_true',
        default=False,
        help='Enable FOV correction when computing XYZ coordinates. '
             'By default (without this flag), XYZ is computed without FOV correction.'
    )
    parser.add_argument(
        '-v', '--fov_value',
        type=lambda x: int(x, 0),
        default=0x02,
        help='FOV correction byte value in hex or decimal (e.g. 0x02, 2). '
             'bits[1:0]=X correction, bits[3:2]=Y correction. '
             'Default: 0x02 (X=2, Y=0). '
             'Only used when -f/--fov_correction is enabled.'
    )
    parser.add_argument(
        '-a', '--all_zones',
        action='store_true',
        default=False,
        help='Use all non-zero distance pixels for plane fitting. '
             'By default (without this flag), only pixels in the zone pattern are used.'
    )
    parser.add_argument(
        '-s', '--snr',
        type=float,
        default=20,
        help='Minimum SNR threshold for a pixel to be included in plane fitting. '
             'Only used with -a/--all_zones. Pixels with SNR below this value or zero distance are excluded. '
             'Default: 20.'
    )
    parser.add_argument(
        '-l', '--focal_length',
        type=float,
        default=560.0,
        help='Focal length in micrometers for FOV calibration. '
             'The TMF8829 nominal focal length is 560um with ±40um tolerance. '
             'Adjusting this value changes the FOV calculation: '
             'smaller value → wider FOV, larger value → narrower FOV. '
             'Default: 560.0.'
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = args.input
    use_fov = args.fov_correction
    fov_value = args.fov_value
    all_zones = args.all_zones
    snr_threshold = args.snr
    focal_length = args.focal_length

    if not os.path.isdir(input_dir):
        print("Error: %s is not a valid directory." % input_dir)
        sys.exit(1)

    print("=" * 60)
    print("Offline Keystone Error Calculator")
    print("=" * 60)
    print("Input directory : %s" % input_dir)
    print("FOV correction : %s%s" %
          ('Enabled' if use_fov else 'Disabled',
           (" (value=0x%02X, X=%d, Y=%d)" % (fov_value, fov_value & 0x03, (fov_value >> 2) & 0x03)) if use_fov else ""))
    print("Focal length    : %.1f um (nominal: 560.0 um, offset: %+.1f um)" %
          (focal_length, focal_length - 560.0))
    print("Pixel selection : %s%s" %
          ("all_zones" if all_zones else "zone_pattern",
           (" (SNR >= %.1f)" % snr_threshold) if all_zones else ""))
    print()

    # Find CSV files
    csv_files = find_csv_files(input_dir)
    if not csv_files:
        print("No keystone_error_*.csv files found in %s" % input_dir)
        sys.exit(1)
    print("Found %d CSV files:" % len(csv_files))
    for cf in csv_files:
        print("  - %s" % os.path.basename(cf))
    print()

    # Process each CSV file
    all_results = {}  # resolution_str -> aggregated stats for plotting
    all_raw = {}      # resolution_str -> raw results for CSV output

    for csv_path in csv_files:
        res_str, results = process_csv_file(csv_path, use_fov_correction=use_fov,
                                             fov_value=fov_value,
                                             all_zones=all_zones,
                                             snr_threshold=snr_threshold,
                                             focal_length=focal_length)
        if res_str is None:
            continue
        if results:
            all_raw[res_str] = results
            all_results[res_str] = aggregate_stats_for_plot(results)

    if not all_results:
        print("No valid data processed.")
        sys.exit(1)

    # Build output filename tag
    fov_tag = "_fov_corr" if use_fov else ""
    zone_tag = "_allzones_snr%d" % int(snr_threshold) if all_zones else ""
    fl_tag = "_fl%d" % int(focal_length) if focal_length != 560.0 else ""

    output_csv = os.path.join(input_dir, 'offline_keystone_error%s%s%s.csv' % (fov_tag, zone_tag, fl_tag))
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['resolution', 'timestamp', 'actual_x', 'actual_y',
                         'keystone_x', 'keystone_y', 'keystone_z', 'error_x', 'error_y'])
        for res_str in sorted(all_raw.keys()):
            for r in all_raw[res_str]:
                writer.writerow([
                    res_str, r['timestamp'], r['actual_x'], r['actual_y'],
                    "%.4f" % r['keystone_x'], "%.4f" % r['keystone_y'], "%.4f" % r['keystone_z'],
                    "%.4f" % r['error_x'], "%.4f" % r['error_y']
                ])
    print("\nOutput CSV saved to %s" % output_csv)

    # Generate plots
    print("\nGenerating plots...")
    plot_combined_errors(all_results, input_dir, use_fov, all_zones, snr_threshold, focal_length)
    print("\nDone.")


if __name__ == '__main__':
    main()
