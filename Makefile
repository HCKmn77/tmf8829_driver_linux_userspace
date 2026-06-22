# ************************************************************************************
# Copyright (c) [2025] ams-OSRAM AG
#
# SPDX-License-Identifier: GPL-2.0 OR MIT
#
# For full license texts, see LICENSES-GPL-2.0.txt or LICENSES-MIT.TXT.
# ************************************************************************************

# Makefile for TMF8829 MCU project

BUILD_DIR = build
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

CC = gcc
TARGET = $(BUILD_DIR)/tmf8829
.DEFAULT_GOAL := all

# Enable JSON logging (comment out to disable)
ENABLE_JSON_LOGGING = 1

# Enable histogram parsing and storage (comment out to disable, saves ~600KB RAM)
ENABLE_HISTOGRAM = 1

# Enable keystone angle calculation (comment out to disable)
ENABLE_KEYSTONE = 1

# Source files
SRCS = main.c tmf8829.c tmf8829_driver.c tmf8829_frameparser.c tmf8829_shim.c

# Object files
OBJS = $(patsubst %.c,$(BUILD_DIR)/%.o,$(SRCS))

# Compiler flags
CFLAGS = -Wall -Wextra -O2

# Add JSON logging support
ifdef ENABLE_JSON_LOGGING
CFLAGS += -DENABLE_JSON_LOGGING
SRCS += tmf8829_json.c
endif

# Add histogram support
ifdef ENABLE_HISTOGRAM
CFLAGS += -DENABLE_HISTOGRAM
endif

# Add keystone support
ifdef ENABLE_KEYSTONE
CFLAGS += -DENABLE_KEYSTONE
SRCS += tmf8829_keystone.c
endif

# Linker flags
LDFLAGS = -lm -lpthread

# Add zlib for JSON logging
ifdef ENABLE_JSON_LOGGING
LDFLAGS += -lz
endif

# Default target
all: $(TARGET)

# Link target
$(TARGET): $(OBJS)
	$(CC) $(OBJS) -o $(TARGET) $(LDFLAGS)

# Compile source files
$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@ -MD -MP

# Include auto-generated dependencies
-include $(OBJS:.o=.d)

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR)
#	rm -f $(OBJS) $(TARGET) $(OBJS:.o=.d)

# Clean and rebuild
rebuild: clean all

# Install (optional, adjust as needed)
install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

# Uninstall
uninstall:
	rm -f /usr/local/bin/$(TARGET)

.PHONY: all clean rebuild install uninstall
