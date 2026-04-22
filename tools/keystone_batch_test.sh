#!/bin/bash

# Keystone Batch Test Script
# This script generates all keystone error analysis data for devices 0415 and 0417

set -e

echo "========================================="
echo "Keystone Batch Test"
echo "========================================="

# ==========================================
# 0415 (SN: UID1747655863)
# ==========================================
echo ""
echo "Processing 0415 (SN: UID1747655863)..."

# Plot Each Resolution Keystone Error (Online Log)
echo "  Computing keystone error for each resolution..."
python ./tools/compute_keystone_error.py -r ./data/keystone/0415/keystone_8x8_sofn.txt   -k ./data/keystone/0415/keystone_8x8_log.txt   -j ./data/keystone/0415/tmf8829_UID1747655863-2026-04-15-10-46-27.json.gz
python ./tools/compute_keystone_error.py -r ./data/keystone/0415/keystone_16x16_sofn.txt -k ./data/keystone/0415/keystone_16x16_log.txt -j ./data/keystone/0415/tmf8829_UID1747655863-2026-04-15-11-02-47.json.gz
python ./tools/compute_keystone_error.py -r ./data/keystone/0415/keystone_32x32_sofn.txt -k ./data/keystone/0415/keystone_32x32_log.txt -j ./data/keystone/0415/tmf8829_UID1747655863-2026-04-15-11-16-26.json.gz
python ./tools/compute_keystone_error.py -r ./data/keystone/0415/keystone_48x32_sofn.txt -k ./data/keystone/0415/keystone_48x32_log.txt -j ./data/keystone/0415/tmf8829_UID1747655863-2026-04-15-11-29-34.json.gz

# Plot All Resolution Keystone Error (Online Log)
echo "  Plotting combined x error..."
python ./tools/plot_x_error_combined.py -i ./data/keystone/0415/.output

# Offline Calculate Keystone Error - Without FOV Correction (Selected Zone)
echo "  Offline: No correction (selected zone)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0415/.output/

# Offline Calculate Keystone Error - Without FOV Correction (All Zones, SNR>=20)
echo "  Offline: No correction (all zones, SNR>=20)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0415/.output/ -a

# Offline Calculate Keystone Error - With FOV Correction (All Zones, SNR>=20)
echo "  Offline: FOV correction (all zones, SNR>=20)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0415/.output/ -a -f -v 0x02

# Offline Calculate Keystone Error - With FOV Correction + FL576 (All Zones, SNR>=20)
echo "  Offline: FOV correction + FL576 (all zones, SNR>=20)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0415/.output/ -a -f -v 0x02 -l 576

# ==========================================
# 0417 (SN: UID1821715)
# ==========================================
echo ""
echo "Processing 0417 (SN: UID1821715)..."

# Plot Each Resolution Keystone Error (Online Log)
echo "  Computing keystone error for each resolution..."
python ./tools/compute_keystone_error.py -r ./data/keystone/0417/keystone_8x8_sofn.txt   -k ./data/keystone/0417/keystone_8x8_log.txt   -j ./data/keystone/0417/tmf8829_UID1821715-2026-04-17-10-26-58.json.gz
python ./tools/compute_keystone_error.py -r ./data/keystone/0417/keystone_16x16_sofn.txt -k ./data/keystone/0417/keystone_16x16_log.txt -j ./data/keystone/0417/tmf8829_UID1821715-2026-04-17-10-40-19.json.gz
python ./tools/compute_keystone_error.py -r ./data/keystone/0417/keystone_32x32_sofn.txt -k ./data/keystone/0417/keystone_32x32_log.txt -j ./data/keystone/0417/tmf8829_UID1821715-2026-04-17-10-53-01.json.gz
python ./tools/compute_keystone_error.py -r ./data/keystone/0417/keystone_48x32_sofn.txt -k ./data/keystone/0417/keystone_48x32_log.txt -j ./data/keystone/0417/tmf8829_UID1821715-2026-04-17-11-05-36.json.gz

# Plot All Resolution Keystone Error (Online Log)
echo "  Plotting combined x error..."
python ./tools/plot_x_error_combined.py -i ./data/keystone/0417/.output

# Offline Calculate Keystone Error - Without FOV Correction (Selected Zone)
echo "  Offline: No correction (selected zone)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0417/.output/

# Offline Calculate Keystone Error - Without FOV Correction (All Zones, SNR>=20)
echo "  Offline: No correction (all zones, SNR>=20)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0417/.output/ -a

# Offline Calculate Keystone Error - With FOV Correction (All Zones, SNR>=20)
echo "  Offline: FOV correction (all zones, SNR>=20)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0417/.output/ -a -f -v 0x0c

# Offline Calculate Keystone Error - With FOV Correction + FL568 (All Zones, SNR>=20)
echo "  Offline: FOV correction + FL568 (all zones, SNR>=20)..."
python ./tools/offline_calc_keystone.py -i ./data/keystone/0417/.output/ -a -f -v 0x0c -l 568

echo ""
echo "========================================="
echo "Keystone Batch Test Complete!"
echo "========================================="
