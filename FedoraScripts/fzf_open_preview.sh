#!/bin/bash
# Beskrivning: Använder fzf för att söka efter filer och mappar, visar en
# detaljerad förhandsgranskning med 'ls -l', och öppnar den valda filen/mappen
# med 'xdg-open' vid tryck på ENTER.

# Kontrollera om xdg-open är tillgängligt (för Linux/UNIX-liknande system)
if ! command -v xdg-open &> /dev/null; then
	echo "Fel: Kommandot 'xdg-open' hittades inte. Detta skript kräver 'xdg-open' för att öppna filer."
	exit 1
fi

# Kontrollera om fzf är tillgängligt
if ! command -v fzf &> /dev/null; then
	echo "Fel: Kommandot 'fzf' hittades inte. Installera fzf och försök igen."
	exit 1
fi

fzf_open_preview() {
	echo "Söker efter filer och mappar i nuvarande katalog..."
	
	# Använder find för att hitta alla filer och mappar, exkluderar vanliga
	# utvecklingskataloger för att göra sökningen snabbare.
	find . -type f -o -type d -not -path "./.git/*" -not -path "./node_modules/*" |
	
	# Kör fzf med de nödvändiga inställningarna
	fzf --ansi \
		--multi \
		--cycle \
		--layout=reverse \
		--info=inline \
		--border \
		--height=80% \
		--header="Sök, ENTER för att öppna, ESC för att avbryta. Förhandsgranskning: ls -l" \
		\
		# Konfigurerar förhandsgranskningen (Preview)
		# 'ls -ld' visar detaljerad information även för mappar.
		--preview 'ls -ld --color=always "{}"' \
		--preview-window=right:50% \
		\
		# Konfigurerar åtgärden när ENTER trycks (Action)
		# execute(xdg-open {}) kör kommandot.
		# > /dev/tty 2>&1 säkerställer att utdata från xdg-open inte stör fzf.
		# +abort stänger fzf efter att filen har öppnats.
		--bind "enter:execute(xdg-open {} > /dev/tty 2>&1)+abort"
}

# Kör funktionen
fzf_open_preview
