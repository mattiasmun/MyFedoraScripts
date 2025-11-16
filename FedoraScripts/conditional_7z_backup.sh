#!/bin/bash
#
# Conditional 7z Archive Backup Script
#
# This script creates a new 7-zip archive of a specified directory only if
# any file within that directory is newer than the existing archive file.
# The archive file will be placed in the same directory as the source folder.
# For example, if the source is '/home/user/data_project', the archive will be 
# '/home/user/data_project.7z'.
#
# Usage: ./conditional_7z_backup.sh <source_directory_path>

# --- Configuration ---
SOURCE_DIR="$1"

# 1. Get the simple folder name (e.g., 'my_project')
# The ${SOURCE_DIR%/} removes a trailing slash if present.
ARCHIVE_NAME=$(basename "${SOURCE_DIR%/}")

# 2. Get the containing directory (e.g., '/home/user/')
ARCHIVE_DIR=$(dirname "$SOURCE_DIR")

# 3. Combine to form the full path to the archive file
ARCHIVE_FILE="${ARCHIVE_DIR}/${ARCHIVE_NAME}.7z"

# --- Functions ---

# Function to check for required tools
check_prerequisites() {
    if ! command -v 7z &> /dev/null; then
        echo "❌ ERROR: The '7z' command (7-Zip) is required but not found." >&2
        echo "Please install it using 'sudo dnf install p7zip p7zip-plugins' (Fedora) or equivalent." >&2
        exit 1
    fi
}

# Function to validate the source directory
validate_source_dir() {
    if [ -z "$SOURCE_DIR" ]; then
        echo "❌ ERROR: Missing source directory argument." >&2
        echo "Usage: $0 <source_directory_path>" >&2
        exit 1
    fi

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "❌ ERROR: Source directory '$SOURCE_DIR' does not exist." >&2
        exit 1
    fi
    
    # Check if the destination directory for the archive is writable
    if [ ! -w "$ARCHIVE_DIR" ]; then
        echo "❌ ERROR: Destination directory '$ARCHIVE_DIR' is not writable. Cannot create '$ARCHIVE_FILE'." >&2
        exit 1
    fi
}

# Function to create the 7z archive
create_archive() {
    local type_of_run="$1"

    echo "Starting $type_of_run archive creation for directory: '$SOURCE_DIR'"
    echo "Archive destination: '$ARCHIVE_FILE'"
    
    # The 'a' command adds files to the archive. If the archive exists, it updates it.
    # -t7z: Specify 7z format
    # -mx=9: Maximum compression
    # -y: Assume Yes to all queries (overwrite existing archive)
    if 7z a -t7z -mx=9 -y "$ARCHIVE_FILE" "$SOURCE_DIR" &> /dev/null
    then
        echo "✅ SUCCESS: Archive '$ARCHIVE_FILE' created/updated successfully."
        exit 0
    else
        echo "❌ ERROR: 7z failed to create the archive. Check permissions or disk space." >&2
        exit 1
    fi
}

# --- Main Logic ---
check_prerequisites
validate_source_dir

# --- 1. Check Initial Archive Existence (Base Case) ---
if [ ! -f "$ARCHIVE_FILE" ]; then
    echo "Archive '$ARCHIVE_FILE' not found. This is the initial run."
    create_archive "initial"
fi

# --- 2. Check for Newer Files ---
echo "Checking for new or modified files in '$SOURCE_DIR' compared to '$ARCHIVE_FILE'..."

# Use 'find' with -newer flag for maximum efficiency.
# -type f: Only check regular files (ignore directories, links, etc.)
# -print -quit: Prints the first matching file found and stops immediately.
NEWER_FILE=$(find "$SOURCE_DIR" -type f -newer "$ARCHIVE_FILE" -print -quit 2>/dev/null)

if [ -n "$NEWER_FILE" ]; then
    echo "Found newer file: '$NEWER_FILE'"
    create_archive "new"
else
    echo "☑️ NO CHANGES: All files are older than or equal to the archive timestamp. No action taken."
    exit 0
fi

# End of script
