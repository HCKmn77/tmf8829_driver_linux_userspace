#!/usr/bin/env python3
"""
Plot combined X error comparison across all resolutions.

Usage:
  python plot_x_error_combined.py -i INPUT_DIR

Input:
  - INPUT_DIR: directory containing keystone_error_{resolution}.csv files

Output:
  - x_error_combined.png: line plot of X error vs actual X angle for all resolutions,
    with each resolution as a separate line (with min~max error bars)
"""

import os
import sys
import argparse
import csv
import re
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(
        description='Plot combined X error comparison across all resolutions.'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Path to directory containing keystone_error_{resolution}.csv files'
    )
    return parser.parse_args()


def compute_error_stats(csv_path):
    """
    Parse a keystone error CSV and compute median X error statistics per actual_x angle.

    Returns:
        resolution: str, extracted from filename
        data: dict with keys 'actual_x', 'median_x', 'min_x', 'max_x', 'count'
    """
    # Extract resolution from filename (e.g., 'keystone_error_8x8.csv' -> '8x8')
    basename = os.path.basename(csv_path)
    match = re.match(r'keystone_error_(.+)\.csv$', basename)
    if not match:
        print(f"Warning: Could not extract resolution from {basename}, skipping.")
        return None, None
    resolution = match.group(1)

    # Group errors by (actual_x, actual_y)
    error_dict = {}
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ax = float(row['actual_x'])
                ay = float(row['actual_y'])
                ex = float(row['error_x'])
            except (KeyError, ValueError):
                continue
            key = (ax, ay)
            error_dict.setdefault(key, []).append(ex)

    # Compute median, min, max per unique actual_x (assume y is constant)
    stats_by_x = {}
    for (ax, ay), errors in error_dict.items():
        sorted_err = sorted(errors)
        n = len(sorted_err)
        median = (sorted_err[n // 2 - 1] + sorted_err[n // 2]) / 2 if n % 2 == 0 else sorted_err[n // 2]
        stats_by_x[ax] = {
            'median': median,
            'min': min(errors),
            'max': max(errors),
            'count': n
        }

    # Sort by actual_x
    sorted_x = sorted(stats_by_x.keys())
    return resolution, {
        'actual_x': sorted_x,
        'median_x': [stats_by_x[x]['median'] for x in sorted_x],
        'min_x': [stats_by_x[x]['min'] for x in sorted_x],
        'max_x': [stats_by_x[x]['max'] for x in sorted_x],
        'count': [stats_by_x[x]['count'] for x in sorted_x]
    }


def main():
    args = parse_args()
    input_dir = args.input

    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory.")
        sys.exit(1)

    # Find all keystone_error_*.csv files
    csv_files = [
        os.path.join(input_dir, f) for f in os.listdir(input_dir)
        if re.match(r'keystone_error_.+\.csv$', f)
    ]

    if not csv_files:
        print(f"No keystone_error_*.csv files found in {input_dir}")
        sys.exit(1)

    print(f"Found {len(csv_files)} CSV files in {input_dir}")

    # Parse each CSV and collect stats
    all_data = {}  # resolution -> stats dict
    for csv_path in sorted(csv_files):
        resolution, stats = compute_error_stats(csv_path)
        if resolution and stats:
            all_data[resolution] = stats
            print(f"  Loaded {resolution}: {len(stats['actual_x'])} angle points")

    if not all_data:
        print("No valid data found in any CSV file.")
        sys.exit(1)

    # Define color cycle for different resolutions
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

    # Plot: X error vs Actual X angle, one line per resolution
    plt.figure(figsize=(12, 7))

    for idx, (resolution, data) in enumerate(sorted(all_data.items())):
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        actual_x = data['actual_x']
        median_x = data['median_x']
        min_x = data['min_x']
        max_x = data['max_x']

        # Asymmetric error bars
        err_low = [median_x[i] - min_x[i] for i in range(len(actual_x))]
        err_high = [max_x[i] - median_x[i] for i in range(len(actual_x))]

        plt.errorbar(actual_x, median_x,
                     yerr=[err_low, err_high],
                     marker=marker, linestyle='-', capsize=3,
                     color=color, label=resolution,
                     markersize=5, linewidth=1.5, elinewidth=1)

    plt.xlabel('Actual X angle (deg)', fontsize=12)
    plt.ylabel('X error (deg)', fontsize=12)
    plt.title('Keystone X Error vs Actual X Angle (All Resolutions)\n'
              'Error bars: min ~ max, dot: median', fontsize=13)
    plt.legend(title='Resolution', loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    output_path = os.path.join(input_dir, 'x_error_combined.png')
    plt.savefig(output_path, dpi=300)
    print(f"Combined X error plot saved to {output_path}")
    plt.close()


if __name__ == '__main__':
    main()
