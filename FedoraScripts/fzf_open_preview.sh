#!/bin/bash
# Beskrivning: Använder fzf för att välja en fil. Sparar resultatet i en variabel,
# visar detaljerad information med 'ls -ld', och frågar sedan användaren om filen
# ska öppnas med 'xdg-open'.

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
	
	# Kör fzf och sparar det valda resultatet (en enskild rad) i variabeln SELECTED_FILE.
	SELECTED_FILE=$(
		find . -type f -o -type d -not -path "./.git/*" -not -path "./node_modules/*" |
		fzf --layout=reverse \
			--border \
			--height=80% \
			--header="Välj en fil. ENTER för att välja, ESC för att avbryta."
	)

	# 1. Kontrollera om användaren avbröt (SELECTED_FILE är tom)
	if [ -z "$SELECTED_FILE" ]; then
		echo "Val av fil avbröts. Avslutar skriptet."
		return 0
	fi

	echo ""
	echo "--- Detaljerad information (ls -ld) ---"
	
	# 2. Kör ls -ld på den valda filen. Vi använder -ld för att säkerställa att
	# även kataloger visas i detalj och inte dess innehåll.
	if ! ls -ld --color=always "$SELECTED_FILE"; then
		echo "Fel: Kunde inte hitta eller lista detaljer för '$SELECTED_FILE'."
		return 1
	fi
	
	echo "-------------------------------------"
	
	# 3. Fråga användaren om de vill öppna filen
	read -r -p "Vill du öppna '$SELECTED_FILE' med xdg-open? (j/n): " response

	if [[ "$response" =~ ^([jJ][aA]|[jJ])$ ]]; then
		echo "Öppnar $SELECTED_FILE..."
		# Använder '&> /dev/null &' för att köra i bakgrunden och tysta utdata.
		xdg-open "$SELECTED_FILE" &> /dev/null &
		echo "Klart. Fönstret kommer nu att visas."
	else
		echo "Öppning av fil avbröts. Avslutar skriptet."
	fi
}

# Kör funktionen
fzf_open_preview

