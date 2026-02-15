#!/bin/bash

# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
# SCRIPT: setup-my-env.sh
# PURPOSE: Configures the user's Fedora environment for custom scripts and history.
# ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

# ⎯⎯ Variable Definitions ⎯⎯
SOURCE_DIR="$HOME/Bash/MyFedoraScripts/FedoraScripts"
DESKTOP_FILE="$SOURCE_DIR/archive/runall.desktop"
BASHRC_FILE="$HOME/.bashrc"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications"
BASH_HISTORY_SOURCE="$SOURCE_DIR/archive/.bash_history"
BASH_HISTORY_TARGET1="$HOME/.bash_history"
BASH_HISTORY_TARGET2="$HOME/.bash_history_cleaned"

# ⎯⎯ Step 1: Updating PATH and History Optimization in .bashrc ⎯⎯
echo "⎯⎯ Step 1: Updating PATH and Environment in $BASHRC_FILE ⎯⎯"

# Vi använder en unik markör för att undvika dubbletter
if grep -qF -- "# Historik-optimering (Uppdaterad via setup-script)" "$BASHRC_FILE"; then
	echo "Inställningarna finns redan i '$BASHRC_FILE'. Hoppar över."
else
	cp "$BASHRC_FILE" "${BASHRC_FILE}.bak"
	echo "Backup skapad vid ${BASHRC_FILE}.bak"

	# Lägg till det kompletta blocket med alla dina inställningar
	cat << 'EOF' >> "$BASHRC_FILE"

# Path setup added by setup-my-env.sh
if [[ ":$PATH:" != *":$HOME/Bash/MyFedoraScripts/FedoraScripts:"* ]]; then
	export PATH="$PATH:$HOME/Bash/MyFedoraScripts/FedoraScripts"
fi

# Askpass and Aliases
export SUDO_ASKPASS="/usr/libexec/openssh/gnome-ssh-askpass"
alias pip-upgrade="pip freeze --user | cut -d'=' -f1 | xargs -n1 pip install -U --no-warn-script-location"

# Tools Initialization
eval "$(zoxide init bash)"
eval "$(thefuck --alias)"

# Historik-optimering (Uppdaterad via setup-script)
export HISTSIZE=2000                                          # Antal rader i minnet
export HISTFILESIZE=2000                                      # Antal rader i filen
export HISTCONTROL=ignoredups                                 # Skippa dubbletter
export HISTIGNORE="ls*:exit:history:pwd:clear"                # Ignorera småkommandon
export HISTTIMEFORMAT="%F %T  "                               # Lägg till datum och tid

shopt -s histappend                                           # Lägg till i filen, skriv inte över
shopt -s cmdhist                                              # Spara flerradiga kommandon snyggt

# Synkar historik aggressivt mellan terminaler
export PROMPT_COMMAND="history -a; history -c; history -r; $PROMPT_COMMAND"

# Snabbsök i historiken
alias hgrep="history | grep -i"

export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
export PATH=$JAVA_HOME/bin:$PATH
EOF
	echo "Hela miljö-blocket har lagts till i '$BASHRC_FILE'."
fi

# ⎯⎯ Step 2: Desktop Files (Autostart & Applications) ⎯⎯
echo ""
echo "⎯⎯ Step 2: Copying $DESKTOP_FILE ⎯⎯"

if [ ! -f "$DESKTOP_FILE" ]; then
	echo "Error: Filen '$DESKTOP_FILE' saknas."
else
	mkdir -p "$AUTOSTART_DIR"
	cp -f "$DESKTOP_FILE" "$AUTOSTART_DIR"
	
	mkdir -p "$APPLICATIONS_DIR"
	cp -f "$DESKTOP_FILE" "$APPLICATIONS_DIR"
	echo "Desktop-filer kopierade till autostart och applikationer."
fi

# ⎯⎯ Step 3: Initial Bash History Files ⎯⎯
echo ""
echo "⎯⎯ Step 3: Copying Initial Bash History files ⎯⎯"

if [ -f "$BASH_HISTORY_SOURCE" ]; then
	if [ ! -f "$BASH_HISTORY_TARGET1" ]; then
		cp -f "$BASH_HISTORY_SOURCE" "$BASH_HISTORY_TARGET1"
		echo "Initialiserade $BASH_HISTORY_TARGET1"
	fi

	if [ ! -f "$BASH_HISTORY_TARGET2" ]; then
		cp -f "$BASH_HISTORY_SOURCE" "$BASH_HISTORY_TARGET2"
		echo "Initialiserade $BASH_HISTORY_TARGET2"
	fi
else
	echo "Ingen källfil för historik hittades. Hoppar över."
fi

echo ""
echo "⎯⎯ Skript färdigt. Konfigurationen är klar. ⎯⎯"
source "$BASHRC_FILE"

exit 0
