#!/bin/bash

# ==============================================================================
# SCRIPT: setup-my-env.sh
# PURPOSE: Configures the user's Fedora environment for custom scripts.
#
# TASKS:
# 1. PATH Setup: Adds a custom script directory to $PATH in .bashrc,
#	ensuring the directory is only added once.
# 2. Desktop Files: Creates autostart and application registration links.
# 3. History Files: Initializes .bash_history files from a source archive.
# ==============================================================================

# --- Variable Definitions ---
# Define all necessary paths using clear, descriptive names.
# Note: Using explicit paths ($HOME) ensures robustness across environments.
SOURCE_DIR="$HOME/Bash/MyFedoraScripts/FedoraScripts"
DESKTOP_FILE="$SOURCE_DIR/archive/runall.desktop"
BASHRC_FILE="$HOME/.bashrc"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications"
BASH_HISTORY_SOURCE="$SOURCE_DIR/archive/.bash_history"
BASH_HISTORY_TARGET1="$HOME/.bash_history"
BASH_HISTORY_TARGET2="$HOME/.bash_history2" # Note: This target might be used for specific history configurations.

# --- Step 1: Updating PATH and History Sync in .bashrc ---
echo "--- Step 1: Updating PATH and History Sync in $BASHRC_FILE ---"

# Check if the configuration block has already been added.
# We use a unique marker (a specific comment) to prevent duplication in .bashrc.
if grep -qF -- "# Path setup added by setup-my-env.sh" "$BASHRC_FILE"; then
	echo "The conditional PATH and history sync block already exists in '$BASHRC_FILE'. Skipping changes."
else
	# Create a backup of the original file for safety before making permanent changes.
	cp "$BASHRC_FILE" "${BASHRC_FILE}.bak"
	echo "Backup created at ${BASHRC_FILE}.bak"

	# Append the new configuration block to .bashrc using a Here Document.
	# The 'EOF' is quoted ('EOF') to prevent shell variables (like $PATH or $HOME)
	# from being expanded now; they must be expanded by the shell upon login.
	cat << 'EOF' >> "$BASHRC_FILE"

# Path setup added by setup-my-env.sh
# This conditional check uses a regex match on the current $PATH variable.
# It ensures the custom directory is added to PATH only once, preventing long, repeated paths.
if [[ ":$PATH:" != *":$HOME/Bash/MyFedoraScripts/FedoraScripts:"* ]]; then
	export PATH="$PATH:$HOME/Bash/MyFedoraScripts/FedoraScripts"
fi

# History Synchronization Configuration (Ensures history is shared between terminals)
# PROMPT_COMMAND executes commands just before the prompt is displayed.
# history -n: Reads history entries from disk that haven't been read yet.
# history -a: Appends the current session's history entries to the disk file.
# This setup ensures all terminals share the command history in real-time.
export PROMPT_COMMAND="history -n; history -a; $PROMPT_COMMAND"
EOF
	
	echo "Successfully added the PATH conditional block and history sync to '$BASHRC_FILE'."
fi

# ------------------------------------------------------------------------------

# --- Step 2: Copy .desktop file for Autostart and Application Registration ---
echo ""
echo "--- Step 2: Copying $DESKTOP_FILE ---"

# Verify that the necessary source file exists before proceeding.
if [ ! -f "$DESKTOP_FILE" ]; then
	echo "Error: The desktop file '$DESKTOP_FILE' does not exist. Check source path."
	exit 1
fi

# 2a. Configure for Autostart
# 'mkdir -p' creates the directory structure if it doesn't exist, suppressing errors.
echo "Creating autostart directory: $AUTOSTART_DIR"
mkdir -p "$AUTOSTART_DIR"

# Copy the file to ensure the custom script runs upon graphical login.
echo "Copying $DESKTOP_FILE to $AUTOSTART_DIR"
cp -f "$DESKTOP_FILE" "$AUTOSTART_DIR"
if [ $? -eq 0 ]; then
	echo "Successfully copied to autostart directory."
else
	echo "Error: Failed to copy to autostart directory. Check permissions."
fi

# 2b. Configure for Application Registration (e.g., GNOME/KDE App Launcher)
echo "Creating applications directory: $APPLICATIONS_DIR"
mkdir -p "$APPLICATIONS_DIR"

# Copying the file here makes the script visible and launchable via the desktop environment's launcher/search bar.
echo "Copying $DESKTOP_FILE to $APPLICATIONS_DIR"
cp -f "$DESKTOP_FILE" "$APPLICATIONS_DIR"
if [ $? -eq 0 ]; then
	echo "Successfully copied to applications directory."
else
	echo "Error: Failed to copy to applications directory. Check permissions."
fi

# ------------------------------------------------------------------------------

# --- Step 3: Copying Initial Bash History Files ---
echo ""
echo "--- Step 3: Copying Initial Bash History files ---"

# Check the integrity of the source history file first.
if [ ! -f "$BASH_HISTORY_SOURCE" ]; then
	echo "Warning: The source history file '$BASH_HISTORY_SOURCE' does not exist. Skipping this setup step."
else
	# 3a. Initialize Primary Bash History (~/.bash_history)
	# Only copy if the target file does NOT exist, to avoid overwriting existing user history.
	if [ ! -f "$BASH_HISTORY_TARGET1" ]; then
		echo "Copying $BASH_HISTORY_SOURCE to initialize $BASH_HISTORY_TARGET1"
		cp -f "$BASH_HISTORY_SOURCE" "$BASH_HISTORY_TARGET1"
	else
		echo "$BASH_HISTORY_TARGET1 already exists. Skipping copy (preserving user history)."
	fi

	# 3b. Initialize Secondary Bash History (~/.bash_history2)
	# This step suggests a secondary history file is used, potentially for specific shell profiles or custom scripts.
	if [ ! -f "$BASH_HISTORY_TARGET2" ]; then
		echo "Copying $BASH_HISTORY_SOURCE to initialize $BASH_HISTORY_TARGET2"
		cp -f "$BASH_HISTORY_SOURCE" "$BASH_HISTORY_TARGET2"
	else
		echo "$BASH_HISTORY_TARGET2 already exists. Skipping copy."
	fi
fi

# ------------------------------------------------------------------------------

echo ""
echo "--- Script finished. Configuration complete. ---"
# Apply changes immediately to the current shell environment
echo "Sourcing $BASHRC_FILE to apply PATH and history synchronization changes immediately."
source "$BASHRC_FILE"

exit 0
