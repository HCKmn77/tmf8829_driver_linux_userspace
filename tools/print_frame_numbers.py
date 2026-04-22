#!/usr/bin/env python3
"""
Print frame_number from TMF8829 JSON.gz log file
"""

import json
import gzip
import argparse
import sys
import os

def get_latest_json_file(directory):
    """Find the latest JSON or JSON.gz file in a directory"""
    
    if not os.path.isdir(directory):
        return None
    
    json_files = []
    for item in os.listdir(directory):
        if item.endswith('.json') or item.endswith('.json.gz'):
            file_path = os.path.join(directory, item)
            mtime = os.path.getmtime(file_path)
            json_files.append((file_path, mtime))
    
    if not json_files:
        return None
    
    # Sort by modification time (newest first) and return the first one
    json_files.sort(key=lambda x: x[1], reverse=True)
    return json_files[0][0]

def print_frame_numbers(json_file):
    """Read and print frame_number from JSON.gz file"""
    
    # Check if input is a directory or file
    if os.path.isdir(json_file):
        latest_file = get_latest_json_file(json_file)
        if latest_file is None:
            print(f"Error: No JSON or JSON.gz files found in directory '{json_file}'")
            sys.exit(1)
        print(f"Using latest file in directory: {os.path.basename(latest_file)}")
        json_file = latest_file
    elif not os.path.isfile(json_file):
        print(f"Error: '{json_file}' is not a valid file or directory")
        sys.exit(1)
    
    # Check if file exists
    try:
        if json_file.endswith('.gz'):
            with gzip.open(json_file, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Extract result set
    result_set = data.get('Result_Set', [])
    
    if not result_set:
        print("No frames found in the file")
        return
    
    # Print frame numbers
    print(f"File: {json_file}")
    print(f"Total frames: {len(result_set)}")
    print("-" * 40)
    print("frame_number:")
    for frame in result_set:
        info = frame.get('info', {})
        frame_number = info.get('frame_number', 'N/A')
        print(f"  {frame_number}")

def main():
    parser = argparse.ArgumentParser(
        description='Print frame_number from TMF8829 JSON.gz log file'
    )
    parser.add_argument(
        'input_path',
        help='Path to JSON/JSON.gz file, or directory (will use latest file)'
    )
    parser.add_argument(
        '-i',
        '--input',
        action='store_true',
        help='Input is a directory (will automatically use the latest JSON/JSON.gz file)'
    )
    
    args = parser.parse_args()
    
    # -i flag is just for documentation, input_path handling is the same
    print_frame_numbers(args.input_path)

if __name__ == '__main__':
    main()
