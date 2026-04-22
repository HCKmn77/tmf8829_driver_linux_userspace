#!/usr/bin/env python3
"""
Compute error between actual rotation stage angles and keystone calculated angles.

Usage:
  python compute_keystone_error.py -r REAL_LOG -k KEYSTONE_LOG [-j JSON_FILE]

Input files:
  - REAL_LOG: log of rotation stage actual angles (x, y) with timestamps
  - KEYSTONE_LOG: keystone algorithm calculated angles (x, y, z) with timestamps
  - JSON_FILE (optional): raw JSON file with distance and snr data per frame

Output:
  - keystone_error_{resolution}.csv: CSV file with all filtered measurements, columns: timestamp, actual_x, actual_y, keystone_x, keystone_y, keystone_z, error_x, error_y[, frame_number, warnings, distance_1..N, snr_1..N]
  - keystone_error_x_y{y}_{resolution}.png: line plot of x error vs actual x angle with error bars
  - keystone_error_y_y{y}_{resolution}.png: line plot of y error vs actual x angle with error bars  
  - keystone_error_combined_y{y}_{resolution}.png: combined plot of both x and y errors
  (resolution is extracted from keystone log, e.g., '8x8', '16x16', etc.)

Filtering: Only measurements between 2 and 8 seconds after each angle change are kept.
"""

import re
import csv
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import sys
import os
import argparse
import gzip
import json as json_lib

def parse_sofn_log(filepath):
    """
    Parse sofn log file to extract timestamps and actual angles.
    Each line format: "2026-04-01 14:54:06 set_x_to_-30.00_y_to_0.00 delay:10s"
    Returns list of (datetime, x, y)
    """
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?set_x_to_([-\d\.]+)_y_to_([-\d\.]+)')
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = pattern.search(line)
            if match:
                timestamp_str, x_str, y_str = match.groups()
                ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                x = float(x_str)
                y = float(y_str)
                data.append((ts, x, y))
    return data

def parse_keystone_log(filepath):
    """
    Parse keystone log file to extract timestamps, frame numbers and keystone angles.
    Each line format: "[2026-04-01 14:54:10][F=#1][sys=19060] Keystone angles: X=-27.52 deg, Y=0.09 deg, Z=62.48 deg"
    Returns list of (datetime, frame_number, x, y, z)
    """
    pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\[F=#(\d+)\]\[sys=\d+\].*?X=([-\d\.]+) deg.*?Y=([-\d\.]+) deg.*?Z=([-\d\.]+) deg')
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = pattern.search(line)
            if match:
                timestamp_str, frame_num_str, x_str, y_str, z_str = match.groups()
                ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                frame_num = int(frame_num_str)
                x = float(x_str)
                y = float(y_str)
                z = float(z_str)
                data.append((ts, frame_num, x, y, z))
    return data

def parse_json_file(filepath):
    """
    Parse gzipped JSON file to extract frame data.
    Returns dict mapping frame_number -> {warnings, distances, snrs}
    where distances and snr are flat lists of first peak values for each pixel (row-major order).
    """
    frame_data = {}
    try:
        open_func = gzip.open if filepath.endswith('.gz') else open
        with open_func(filepath, 'rt', encoding='utf-8') as f:
            data = json_lib.load(f)
        
        result_set = data.get('Result_Set', [])
        for frame in result_set:
            info = frame.get('info', {})
            frame_num = info.get('frame_number')
            warnings = info.get('warnings', 0)
            
            results = frame.get('results', [])
            distances = []
            snrs = []
            
            for row in results:
                for pixel in row:
                    peaks = pixel.get('peaks', [])
                    if peaks:
                        # Only use the first peak
                        first_peak = peaks[0]
                        distances.append(first_peak.get('distance', 0))
                        snrs.append(first_peak.get('snr', 0))
                    else:
                        distances.append(0)
                        snrs.append(0)
            
            frame_data[frame_num] = {
                'warnings': warnings,
                'distances': distances,
                'snrs': snrs
            }
        
        print(f"Loaded JSON: {len(frame_data)} frames, each with {len(distances) if distances else 0} pixels")
    
    except Exception as e:
        print(f"Warning: Could not parse JSON file {filepath}: {e}")
    
    return frame_data


def extract_resolution_from_keystone_log(filepath):
    """
    Extract resolution (res) from keystone log file.
    Looks for lines containing 'res=' and returns the first found resolution string.
    Returns 'unknown' if not found.
    """
    import re
    pattern = re.compile(r'res=([\dx]+)')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    return match.group(1)  # e.g., '8x8', '16x16', etc.
    except Exception as e:
        print(f"Warning: Could not extract resolution from {filepath}: {e}")
    return 'unknown'

def filter_measurements_by_angle_changes(angle_changes, measurements, window_start=2.0, window_end=8.0):
    """
    angle_changes: list of (datetime, x, y) where angle changes occur.
    measurements: list of (datetime, frame_number, x, y, z) keystone measurements.
    window_start: seconds after angle change to start accepting measurements.
    window_end: seconds after angle change to stop accepting measurements.
    
    Returns list of (datetime, frame_number, actual_x, actual_y, keystone_x, keystone_y, keystone_z)
    for measurements that are within [change_time + window_start, change_time + window_end]
    after the most recent angle change.
    """
    # Create a list of change timestamps
    change_times = [ts for ts, _, _ in angle_changes]
    
    filtered = []
    for m_ts, m_frame, kx, ky, kz in measurements:
        # Find the index of the most recent change time <= m_ts
        idx = None
        for i, c_ts in enumerate(change_times):
            if c_ts <= m_ts:
                idx = i
            else:
                break
        if idx is None:
            # measurement before first change, ignore
            continue
        # Get the corresponding change time and angle
        c_ts, actual_x, actual_y = angle_changes[idx]
        delta = (m_ts - c_ts).total_seconds()
        # Accept only if delta is between window_start and window_end inclusive
        if window_start <= delta <= window_end:
            filtered.append((m_ts, m_frame, actual_x, actual_y, kx, ky, kz))
    return filtered

def compute_error_stats(filtered_data):
    """
    Compute error statistics per actual angle.
    filtered_data: list of (datetime, frame_number, actual_x, actual_y, keystone_x, keystone_y, keystone_z)
    Returns dict mapping (actual_x, actual_y) -> (min_error, max_error, median_error, count)
    """
    error_dict = {}
    for _, _, ax, ay, kx, ky, _ in filtered_data:
        key = (ax, ay)
        error_x = kx - ax
        error_y = ky - ay
        error_dict.setdefault(key, []).append((error_x, error_y))
    
    def calc_median(values):
        """Compute median of a list"""
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
        else:
            return sorted_vals[n//2]
    
    # Compute min, max, median for each angle
    stats_dict = {}
    for key, errors in error_dict.items():
        errors_x = [e[0] for e in errors]
        errors_y = [e[1] for e in errors]
        median_x = calc_median(errors_x)
        median_y = calc_median(errors_y)
        stats_dict[key] = {
            'min_x': min(errors_x),
            'max_x': max(errors_x),
            'median_x': median_x,
            'min_y': min(errors_y),
            'max_y': max(errors_y),
            'median_y': median_y,
            'count': len(errors)
        }
    return stats_dict

def parse_args():
    parser = argparse.ArgumentParser(description='Compute error between actual rotation stage angles and keystone calculated angles.')
    parser.add_argument('-r', '--real', required=True, help='Path to real rotation stage log file (e.g., sofn_log_+-30.txt)')
    parser.add_argument('-k', '--keystone', required=True, help='Path to keystone algorithm log file (e.g., 8x8_keystone.txt)')
    parser.add_argument('-j', '--json', default=None, help='Path to raw JSON file (optional, e.g., tmf8829_UIDxxx.json.gz)')
    parser.add_argument('-s', '--start', type=float, default=3.0, help='Start offset in seconds after angle change (default: 3.0)')
    parser.add_argument('-d', '--duration', type=float, default=3.0, help='Duration in seconds after start offset (default: 3.0, i.e., window is [start, start+duration])')
    return parser.parse_args()

def main():
    args = parse_args()
    
    real_path = args.real
    keystone_path = args.keystone
    json_path = args.json
    window_start = args.start
    window_end = args.start + args.duration
    
    if not os.path.exists(real_path):
        print(f"Error: {real_path} not found.")
        sys.exit(1)
    if not os.path.exists(keystone_path):
        print(f"Error: {keystone_path} not found.")
        sys.exit(1)
    
    # Parse JSON file if provided
    json_data = None
    num_pixels = 0
    if json_path:
        if not os.path.exists(json_path):
            print(f"Error: {json_path} not found.")
            sys.exit(1)
        print("Parsing JSON file...")
        json_data = parse_json_file(json_path)
        # Determine number of pixels from first frame
        for frame_num in json_data:
            num_pixels = len(json_data[frame_num]['distances'])
            break
    
    # Output directory: .output subdirectory under keystone file directory
    output_dir = os.path.dirname(keystone_path)
    if not output_dir:
        output_dir = '.'  # current directory if keystone_path has no directory
    output_dir = os.path.join(output_dir, '.output')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Using output directory: {output_dir}")
    
    print("Parsing real log...")
    angle_changes = parse_sofn_log(real_path)
    print(f"Found {len(angle_changes)} angle changes.")
    
    print("Parsing keystone log...")
    keystone_measurements = parse_keystone_log(keystone_path)
    print(f"Found {len(keystone_measurements)} keystone measurements.")
    
    # Extract resolution from keystone log
    resolution = extract_resolution_from_keystone_log(keystone_path)
    print(f"Detected resolution: {resolution}")
    
    # Extract filenames for plot titles
    real_filename = os.path.basename(real_path)
    keystone_filename = os.path.basename(keystone_path)
    file_info = f"-r: {real_filename}  -k: {keystone_filename}  -s: {window_start}  -d: {args.duration}"

    # Filter measurements: only keep data within the specified time window after each angle change
    print(f"Filtering window: [{window_start}, {window_end}] seconds after angle change")
    filtered = filter_measurements_by_angle_changes(angle_changes, keystone_measurements, window_start, window_end)
    print(f"After filtering (window {window_start}-{window_end}s), {len(filtered)} measurements remain.")
    
    # Write CSV with all filtered keystone calculations
    csv_path = os.path.join(output_dir, f'keystone_error_{resolution}.csv')
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Build header: base columns + optional JSON columns
        header = ['timestamp', 'actual_x', 'actual_y', 'keystone_x', 'keystone_y', 'keystone_z', 'error_x', 'error_y']
        if json_data:
            header.extend(['frame_number', 'warnings'])
            for i in range(num_pixels):
                header.append(f'distance_{i+1}')
            for i in range(num_pixels):
                header.append(f'snr_{i+1}')
        writer.writerow(header)
        
        for m_ts, m_frame, ax, ay, kx, ky, kz in filtered:
            error_x = kx - ax
            error_y = ky - ay
            row = [m_ts.strftime('%Y-%m-%d %H:%M:%S'), ax, ay, kx, ky, kz, error_x, error_y]
            if json_data and m_frame in json_data:
                fd = json_data[m_frame]
                row.append(m_frame)
                row.append(fd['warnings'])
                row.extend(fd['distances'])
                row.extend(fd['snrs'])
            elif json_data:
                # Frame not found in JSON, fill with empty/0 values
                row.append(m_frame)
                row.append(0)
                row.extend([0] * (num_pixels * 2))
            writer.writerow(row)
    print(f"CSV saved to {csv_path}")
    
    # Compute errors per actual angle
    stats_dict = compute_error_stats(filtered)
    
    # Build rows for plotting (statistics per angle)
    rows = []
    for key, stats in stats_dict.items():
        ax, ay = key
        rows.append((ax, ay, stats['median_x'], stats['min_x'], stats['max_x'], 
                            stats['median_y'], stats['min_y'], stats['max_y'], stats['count']))
    
    # Create DataFrames for plotting (assuming y is constant zero, but keep structure)
    # Separate data by actual_y if needed
    y_values = set(ay for (ax, ay) in stats_dict.keys())
    for y_val in y_values:
        # Filter rows for this y
        rows_y = [(ax, ay, median_x, min_x, max_x, median_y, min_y, max_y, count) 
                  for (ax, ay, median_x, min_x, max_x, median_y, min_y, max_y, count) in rows if ay == y_val]
        if not rows_y:
            continue
        
        # Sort by actual_x
        rows_y.sort(key=lambda r: r[0])
        actual_x = [r[0] for r in rows_y]
        error_x_median = [r[2] for r in rows_y]
        error_x_min = [r[3] for r in rows_y]
        error_x_max = [r[4] for r in rows_y]
        error_y_median = [r[5] for r in rows_y]
        error_y_min = [r[6] for r in rows_y]
        error_y_max = [r[7] for r in rows_y]
        counts = [r[8] for r in rows_y]
        
        # Asymmetric error bars: [lower_errors], [upper_errors]
        # lower = median - min, upper = max - median
        x_err_low = [error_x_median[i] - error_x_min[i] for i in range(len(actual_x))]
        x_err_high = [error_x_max[i] - error_x_median[i] for i in range(len(actual_x))]
        y_err_low = [error_y_median[i] - error_y_min[i] for i in range(len(actual_x))]
        y_err_high = [error_y_max[i] - error_y_median[i] for i in range(len(actual_x))]
        
        plt.figure(figsize=(10, 6))
        plt.errorbar(actual_x, error_x_median, 
                     yerr=[x_err_low, x_err_high], 
                     marker='o', linestyle='-', capsize=4, color='blue')
        plt.xlabel('Actual X angle (deg)')
        plt.ylabel('X error (deg)')
        plt.title(f'{file_info}\nKeystone X Error vs Actual X Angle (Y={y_val} deg)\nError bars: min ~ max, dot: median')
        plt.grid(True)
        plot_path_x = os.path.join(output_dir, f'keystone_error_x_y{y_val}_{resolution}.png')
        plt.savefig(plot_path_x, dpi=300)
        print(f"X error plot saved to {plot_path_x}")
        plt.close()
        
        # Plot Y error with min/max error bars
        plt.figure(figsize=(10, 6))
        plt.errorbar(actual_x, error_y_median, 
                     yerr=[y_err_low, y_err_high], 
                     marker='o', linestyle='-', capsize=4, color='orange')
        plt.xlabel('Actual X angle (deg)')
        plt.ylabel('Y error (deg)')
        plt.title(f'{file_info}\nKeystone Y Error vs Actual X Angle (Y={y_val} deg)\nError bars: min ~ max, dot: median')
        plt.grid(True)
        plot_path_y = os.path.join(output_dir, f'keystone_error_y_y{y_val}_{resolution}.png')
        plt.savefig(plot_path_y, dpi=300)
        print(f"Y error plot saved to {plot_path_y}")
        plt.close()
        
        # Combined plot (both X and Y errors)
        plt.figure(figsize=(12, 6))
        plt.errorbar(actual_x, error_x_median, 
                     yerr=[x_err_low, x_err_high], 
                     marker='o', linestyle='-', capsize=4, label='X error (min~max)')
        plt.errorbar(actual_x, error_y_median, 
                     yerr=[y_err_low, y_err_high], 
                     marker='s', linestyle='--', capsize=4, label='Y error (min~max)')
        plt.xlabel('Actual X angle (deg)')
        plt.ylabel('Error (deg)')
        plt.title(f'{file_info}\nKeystone X and Y Errors vs Actual X Angle (Y={y_val} deg)\nError bars: min ~ max, dot: median')
        plt.legend()
        plt.grid(True)
        plot_path_combined = os.path.join(output_dir, f'keystone_error_combined_y{y_val}_{resolution}.png')
        plt.savefig(plot_path_combined, dpi=300)
        print(f"Combined error plot saved to {plot_path_combined}")
        plt.close()
    
    
if __name__ == '__main__':
    main()