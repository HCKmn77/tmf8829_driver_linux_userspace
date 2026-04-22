#!/usr/bin/env python3
"""
Find the best focal length in the range [520, 600] for a given resolution and mode.

Usage:
  python calc_best_focal_length.py -i INPUT_DIR [-r RESOLUTION] [-m MODE] [-p]

Input:
  - INPUT_DIR: directory containing keystone_error_{resolution}.csv files

Parameters:
  -r, --resolution  Resolution index (default: 2)
                    0 = 8x8, 1 = 16x16, 2 = 32x32, 3 = 32x48
  -m, --mode        Optimization mode (default: 0)
                    0 = minimize max absolute X angle error across all angles
                    1 = minimize mean absolute X angle error across all angles
  -p, --plot_all_focal_length
                    Plot error vs focal length for range [520, 600] step 1
                    and save the figure to the input directory.
                    X-axis: focal length, Y-axis: error (degrees).
                    Shows both max and mean error curves with best point marked.

Output:
  Best focal length and corresponding error metrics for the specified resolution.
  Or a plot saved to error_vs_focal_length_{resolution}_{mode}.png
"""

import os
import sys
import argparse
import csv
import re
import math

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Import shared logic from offline_calc_keystone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import offline_calc_keystone


RESOLUTION_MAP = {
    0: '8x8',
    1: '16x16',
    2: '32x32',
    3: '32x48',
}

RESOLUTION_GRID = {
    '8x8': (8, 8),
    '16x16': (16, 16),
    '32x32': (32, 32),
    '32x48': (32, 48),
}


def load_csv_once(csv_path, rows, cols):
    """Load all rows from CSV once, return list of (actual_x, distances, snrs)."""
    rows_data = []
    num_pixels = rows * cols
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                actual_x = float(row.get('actual_x', 0))
            except (ValueError, TypeError):
                continue
            distances = []
            for i in range(1, num_pixels + 1):
                try:
                    d = float(row.get('distance_%d' % i, 0))
                except (ValueError, TypeError):
                    d = 0.0
                distances.append(d)
            snrs = []
            for i in range(1, num_pixels + 1):
                try:
                    s = float(row.get('snr_%d' % i, -1))
                except (ValueError, TypeError):
                    s = -1.0
                snrs.append(s)
            rows_data.append((actual_x, distances, snrs))
    return rows_data


def calc_error_x_list(rows_data, rows, cols, focal_length, use_fov_correction, fov_value, all_zones, snr_threshold):
    """Compute error_x for all rows at a given focal length using cached data."""
    error_x_list = []
    for actual_x, distances, snrs in rows_data:
        # Rebuild a minimal row dict for process_csv_row compatibility
        num_pixels = rows * cols
        row = {'actual_x': actual_x}
        for i in range(1, num_pixels + 1):
            row['distance_%d' % i] = distances[i - 1]
            row['snr_%d' % i] = snrs[i - 1]
        kx, ky, kz = offline_calc_keystone.process_csv_row(
            row, rows, cols,
            use_fov_correction=use_fov_correction,
            fov_value=fov_value,
            all_zones=all_zones,
            snr_threshold=snr_threshold,
            focal_length=focal_length
        )
        error_x_list.append(kx - actual_x)
    return error_x_list


def eval_point(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, fl):
    """Evaluate a single focal length and return (score, max_abs, mean_abs)."""
    error_x_list = calc_error_x_list(rows_data, rows, cols, fl, use_fov_correction, fov_value, all_zones, snr_threshold)
    if not error_x_list:
        return float('inf'), float('inf'), float('inf')
    abs_errors = [abs(e) for e in error_x_list]
    max_abs = max(abs_errors)
    mean_abs = sum(abs_errors) / len(abs_errors)
    score = max_abs if mode == 0 else mean_abs
    return score, max_abs, mean_abs


def hill_climb(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode,
               start, step, lo, hi):
    """Hill-climbing search from start toward the minimum within [lo, hi].

    Algorithm:
      1. Evaluate start point.
      2. Check both neighbors (left/right) to determine direction.
      3. Move step-by-step in that direction until score increases.
      4. Return the best point found.

    Returns:
        best_fl, best_score, [(fl, score, max_abs, mean_abs), ...]
    """
    print("-" * 50)
    print("%-10s %-15s %-15s" % ("focal_l", "max|error_x|", "mean|error_x|"))
    print("-" * 50)

    results = []
    best_fl, best_score = start, float('inf')

    # Evaluate start point
    score, max_abs, mean_abs = eval_point(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, start)
    results.append((start, score, max_abs, mean_abs))
    best_fl, best_score = start, score
    print("%-10.1f %-15.6f %-15.6f" % (start, max_abs, mean_abs))

    # Determine direction by checking both neighbors
    left = start - step
    right = start + step
    sc_left = eval_point(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, left)[0] if left >= lo else float('inf')
    sc_right = eval_point(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, right)[0] if right <= hi else float('inf')

    if sc_left >= score and sc_right >= score:
        # Start is already the best (or both sides are worse/equal)
        return best_fl, best_score, results

    # Choose direction: go toward the better neighbor
    direction = 1 if sc_right < sc_left else -1

    cur = start + direction * step
    while lo <= cur <= hi:
        score, max_abs, mean_abs = eval_point(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, cur)
        print("%-10.1f %-15.6f %-15.6f" % (cur, max_abs, mean_abs))
        results.append((cur, score, max_abs, mean_abs))

        if score < best_score:
            best_fl, best_score = cur, score
        else:
            # Score increased, crossed the minimum -> stop
            break

        cur += direction * step

    return best_fl, best_score, results


def find_best_focal_length(input_dir, resolution_idx, mode, use_fov_correction=True, fov_value=0, all_zones=True, snr_threshold=20):
    """Search focal length range [520, 600] using hill-climbing (coarse + fine)."""
    res_str = RESOLUTION_MAP.get(resolution_idx)
    if res_str is None:
        print("Error: invalid resolution index %d. Valid: 0-8x8, 1-16x16, 2-32x32, 3-32x48." % resolution_idx)
        sys.exit(1)

    csv_name = 'keystone_error_%s.csv' % res_str
    csv_path = os.path.join(input_dir, csv_name)

    if not os.path.isfile(csv_path):
        print("Error: CSV file not found: %s" % csv_path)
        sys.exit(1)

    rows, cols = RESOLUTION_GRID[res_str]
    mode_desc = "max abs X error" if mode == 0 else "mean abs X error"

    print("Loading data from: %s" % csv_path)
    print("Resolution: %s (%dx%d)" % (res_str, rows, cols))
    print("FOV correction: %s (value=0x%02X)" % ("Enabled" if use_fov_correction else "Disabled", fov_value))
    print("All zones: %s (SNR>=%.1f)" % ("True" if all_zones else "False", snr_threshold))
    print("Optimization mode: %d (%s)" % (mode, mode_desc))
    print()

    # Load CSV once and cache all rows
    print("Loading CSV rows into memory...")
    rows_data = load_csv_once(csv_path, rows, cols)
    print("Loaded %d rows." % len(rows_data))
    print()

    # --- Pass 1: Coarse hill-climbing from 560, step=10 ---
    print("=" * 50)
    print("[Pass 1] Hill-climbing (step=10), start=560, range=[520, 600]")
    coarse_fl, coarse_score, _ = hill_climb(
        rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode,
        start=560.0, step=10.0, lo=520.0, hi=600.0
    )
    print("-" * 50)
    print("Coarse best: focal_l=%.1f, %s=%.6f" % (coarse_fl, mode_desc, coarse_score))
    print()

    # --- Pass 2: Fine hill-climbing from coarse best, step=1 ---
    print("=" * 50)
    print("[Pass 2] Hill-climbing (step=1), start=%.1f" % coarse_fl)
    best_fl, best_score, results_table = hill_climb(
        rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode,
        start=coarse_fl, step=1.0, lo=520.0, hi=600.0
    )

    print("-" * 50)
    print()
    print("Best focal length: %.1f" % best_fl)
    print("Best %s: %.6f" % (mode_desc, best_score))

    return best_fl, results_table


def plot_all_focal_lengths(rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, resolution_idx, output_dir):
    """Plot error vs focal length for range [520, 600] step 1 and save the figure."""
    if plt is None:
        print("Error: matplotlib is required for plotting. Install with: pip install matplotlib")
        return

    res_str = RESOLUTION_MAP.get(resolution_idx)
    mode_desc = "max" if mode == 0 else "mean"
    mode_full = "Max" if mode == 0 else "Mean"

    focal_lengths = list(range(520, 601))  # 520 to 600 inclusive
    max_errors = []
    mean_errors = []

    print("Calculating errors for all focal lengths (520-600)...")
    print("%-10s %-15s %-15s" % ("focal_l", "max|error_x|", "mean|error_x|"))
    print("-" * 42)
    for fl in focal_lengths:
        score, max_abs, mean_abs = eval_point(
            rows_data, rows, cols, use_fov_correction, fov_value, all_zones, snr_threshold, mode, fl
        )
        max_errors.append(max_abs)
        mean_errors.append(mean_abs)
        print("%-10.1f %-15.6f %-15.6f" % (fl, max_abs, mean_abs))

    # Plot
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(focal_lengths, max_errors, 'b-', linewidth=1.5, label='Max abs error')
    ax.plot(focal_lengths, mean_errors, 'r-', linewidth=1.5, label='Mean abs error')

    # Mark best point
    best_idx = max_errors.index(min(max_errors)) if mode == 0 else mean_errors.index(min(mean_errors))
    best_fl = focal_lengths[best_idx]
    best_val = max_errors[best_idx] if mode == 0 else mean_errors[best_idx]
    ax.scatter([best_fl], [best_val], color='green', s=100, zorder=5, label='Best (%.1f: %.4f)' % (best_fl, best_val))

    ax.set_xlabel('Focal Length', fontsize=14)
    ax.set_ylabel('Error (degrees)', fontsize=14)
    ax.set_title('%s Abs X Error vs Focal Length\nResolution: %s (%dx%d), Mode: %s' % (
        mode_full, res_str, rows, cols, mode_desc), fontsize=14)
    ax.legend(loc='best', fontsize=12)
    ax.grid(True, alpha=0.3)

    # Save figure
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, 'error_vs_focal_length_%s_%s.png' % (res_str, mode_desc))
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print()
    print("Plot saved to: %s" % out_path)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Find the best focal length for keystone error minimization.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        """,
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input directory containing keystone_error_{resolution}.csv files'
    )
    parser.add_argument(
        '-r', '--resolution',
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help='Resolution index: 0=8x8, 1=16x16, 2=32x32 (default), 3=32x48'
    )
    parser.add_argument(
        '-m', '--mode',
        type=int,
        default=0,
        choices=[0, 1],
        help='Optimization mode: 0=minimize max abs X error (default), 1=minimize mean abs X error'
    )
    parser.add_argument(
        '-v', '--fov_value',
        type=lambda x: int(x, 0),
        default=0,
        help='FOV correction byte value in hex or decimal (e.g. 0x02, 2). '
             'bits[1:0]=X correction, bits[3:2]=Y correction. Default: 0.'
    )
    parser.add_argument(
        '-p', '--plot_all_focal_length',
        action='store_true',
        help='Plot error vs focal length for range [520, 600] step 1 and save the figure'
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = args.input

    if not os.path.isdir(input_dir):
        print("Error: %s is not a valid directory." % input_dir)
        sys.exit(1)

    print("=" * 50)
    print("Best Focal Length Finder")
    print("=" * 50)
    print("Input directory : %s" % input_dir)
    print("Resolution       : %d (%s)" % (args.resolution, RESOLUTION_MAP[args.resolution]))
    print("Mode             : %d (%s)" % (
        args.mode,
        "minimize max abs X error" if args.mode == 0 else "minimize mean abs X error"
    ))
    print("FOV value        : 0x%02X" % args.fov_value)
    print("Plot mode        : %s" % ("Enabled" if args.plot_all_focal_length else "Disabled"))
    print()

    if args.plot_all_focal_length:
        # Load data once
        res_str = RESOLUTION_MAP.get(args.resolution)
        csv_name = 'keystone_error_%s.csv' % res_str
        csv_path = os.path.join(input_dir, csv_name)
        if not os.path.isfile(csv_path):
            print("Error: CSV file not found: %s" % csv_path)
            sys.exit(1)
        rows, cols = RESOLUTION_GRID[res_str]
        rows_data = load_csv_once(csv_path, rows, cols)
        print("Loaded %d rows." % len(rows_data))
        print()

        # Plot all focal lengths
        plot_all_focal_lengths(
            rows_data, rows, cols, True, args.fov_value, True, 20,
            args.mode, args.resolution, input_dir
        )
    else:
        find_best_focal_length(input_dir, args.resolution, args.mode, use_fov_correction=True, fov_value=args.fov_value, all_zones=True, snr_threshold=20)


if __name__ == '__main__':
    main()
