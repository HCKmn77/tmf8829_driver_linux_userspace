# TMF8829 MCU Project - Tools

This directory contains utility tools for the TMF8829 MCU project.

## Available Tools

### 1. compute_keystone_error.py

Calculates error between actual rotation stage angles and keystone algorithm calculated angles.

**Usage:**
```bash
python3 compute_keystone_error.py -r REAL_LOG -k KEYSTONE_LOG
```

**Input Files:**
- `REAL_LOG`: Rotation stage log file with actual (x, y) angles and timestamps
  Format: "2026-04-01 14:54:06 set_x_to_-30.00_y_to_0.00 delay:10s"
- `KEYSTONE_LOG`: Keystone algorithm log with calculated (x, y, z) angles and timestamps
  Format: "[2026-04-01 14:54:10] Keystone angles: X=-27.52 deg, Y=0.09 deg, Z=62.48 deg"

**Output:**
- `keystone_error_{resolution}.csv`: CSV file with all filtered measurements
  Columns: timestamp, actual_x, actual_y, keystone_x, keystone_y, keystone_z, error_x, error_y
- `keystone_error_x_y{y}_{resolution}.png`: X error plot vs actual X angle (with error bars)
- `keystone_error_y_y{y}_{resolution}.png`: Y error plot vs actual X angle (with error bars)
- `keystone_error_combined_y{y}_{resolution}.png`: Combined X and Y errors plot

**Options:**
```bash
python3 compute_keystone_error.py \
  -r 8x8_sofn_log_+-30.txt \
  -k 8x8_keystone.txt \
  -s 3.0 \
  -d 3.0
```
- `-s, --start`: Start offset in seconds after angle change (default: 3.0)
- `-d, --duration`: Duration in seconds after start offset (default: 3.0)

**Filtering:** Only measurements between 3 and 6 seconds after each angle change are kept by default.

**Resolution Detection:** The script automatically extracts resolution (e.g., '8x8', '16x16') from keystone log files.

---

### 2. json_to_html.py

Converts TMF8829 JSON log files to interactive HTML visualizations.

**Usage:**
```bash
python3 json_to_html.py <input.json.gz> <output.html>
```

**Features:**
- Interactive frame navigation
- Distance heatmaps for all resolutions
- Histogram data visualization (if available)
- Confidence and noise data display

**Example:**
```bash
python3 json_to_html.py data/tmf8829_uid-2026-03-31-14-30-00.json.gz output/visualization.html
```

---

### 3. print_frame_numbers.py

Extracts and prints frame numbers from JSON log files.

**Usage:**
```bash
python3 print_frame_numbers.py <input.json.gz>
```

**Output:**
Prints a list of all frame numbers in the JSON file, useful for:
- Verifying frame continuity
- Detecting lost frames
- Debugging frame parsing issues

**Example:**
```bash
python3 print_frame_numbers.py data/tmf8829_uid-2026-03-31-14-30-00.json.gz
```

---

### 4. run_all_modes.sh

Runs the TMF8829 application in all 14 resolution modes sequentially.

**Usage:**
```bash
./run_all_modes.sh [-j] [-t <duration>] [-h]
```

**Options:**
- `-j`: Save JSON files and rename them with mode information
- `-t <duration>`: Duration for each mode in seconds (default: 5)
- `-h`: Save histogram data

**What it does:**
1. Runs all 14 modes (0-13) sequentially with specified duration
2. Creates timestamped output directory: `run_all_modes_YYYYMMDD_HHMMSS/`
3. Saves log files for each mode
4. If `-j` is used, renames JSON files to include mode information
5. If `-h` is used, enables histogram data for all modes

**Example:**
```bash
./run_all_modes.sh -j -t 10 -h
```

---

### 5. test_all_combinations.sh

Tests all Makefile compilation macro combinations.

**Usage:**
```bash
./test_all_combinations.sh
```

**What it tests:**
- All 8 combinations of:
  - `ENABLE_JSON_LOGGING` (0/1)
  - `ENABLE_HISTOGRAM` (0/1)
  - `ENABLE_KEYSTONE` (0/1)

**What it does:**
1. Backs up the original Makefile
2. Tests each combination by modifying the Makefile
3. Attempts to compile the project
4. Reports success/failure for each test
5. Restores the original Makefile
6. Provides color-coded summary output

**Example Output:**
```
Test 1/8: JSON=1 HIST=1 KEYSTONE=1 ... PASS
Test 2/8: JSON=1 HIST=1 KEYSTONE=0 ... PASS
...
Summary: 8/8 tests passed
```

---

### 6. test_fps_all_modes.sh

Tests the frame rate (FPS) for all resolution modes.

**Usage:**
```bash
./test_fps_all_modes.sh
```

**What it does:**
1. Runs each mode for a short duration (typically 10 seconds)
2. Parses output to extract FPS information
3. Creates a summary table of FPS by resolution and mode
4. Helps identify performance bottlenecks

**Example Output:**
```
Mode  Resolution  Dual Mode  Avg FPS
0     8x8         No         15.2
3     8x8         Yes        7.8
5     16x16       No         8.4
...
```

---


## File Structure

```
tools/
├── README.md                     # This file
├── compute_keystone_error.py    # Keystone error calculation tool
├── json_to_html.py              # JSON to HTML visualization converter
├── print_frame_numbers.py       # Frame number extraction tool
├── run_all_modes.sh             # Run all resolution modes script
├── test_all_combinations.sh     # Makefile macro combination tester
└── test_fps_all_modes.sh        # Frame rate testing script
```

---

*Last Updated: 2026-04-03*