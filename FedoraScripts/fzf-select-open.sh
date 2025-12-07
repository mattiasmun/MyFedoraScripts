#!/bin/bash
# Filnamn: fzf-select-open.sh
# Beskrivning: Använder fzf för att välja en eller flera filer. Sparar resultatet i en variabel,
# visar detaljerad information med 'ls -ld' för alla valda filer, och frågar sedan
# användaren om filerna ska öppnas med 'xdg-open'.

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

fzf_select_open_multi() {
	echo "Söker efter filer och mappar i nuvarande katalog…"

	# Kör fzf med --multi och sparar alla valda resultat i SELECTED_FILES.
	# Filnamnen är separerade av radbrytningar.
	SELECTED_FILES=$(
		find . -type f -o -type d -not -path "./.git/*" -not -path "./node_modules/*" |
		fzf --multi \
			--cycle \
			--layout=reverse \
			--border \
			--height=80% \
			--header="Välj en eller flera filer (TAB/Shift+TAB för att markera). ENTER för att välja, ESC för att avbryta."
	)

	# 1. Kontrollera om användaren avbröt (SELECTED_FILES är tom)
	if [ -z "$SELECTED_FILES" ]; then
		echo "Val av filer avbröts. Avslutar skriptet."
		return 0
	fi

	# Räkna antalet valda filer (wc -l räknar raderna, vilket motsvarar antalet filer)
	FILE_COUNT=$(echo "$SELECTED_FILES" | wc -l)

	echo ""
	echo "⎯⎯ Detaljerad information för $FILE_COUNT filer (ls -ld) ⎯⎯"

	# 2. Loopa igenom alla valda filer och kör ls -ld på varje.
	# IFS= read -r FILE säkerställer att vi hanterar filnamn med blanksteg korrekt.
	echo "$SELECTED_FILES" | while IFS= read -r FILE; do
		if [ -n "$FILE" ]; then
			if ! ls -ld --color=always "$FILE"; then
				echo "Varning: Kunde inte hitta eller lista detaljer för '$FILE'."
			fi
		fi
	done

	echo "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"

	# 3. Fråga användaren om de vill öppna filerna
	read -r -p "Vill du öppna DESSA $FILE_COUNT filer med xdg-open? (j/n): " response

	# Acceptera j, J, ja, JA, etc.
	if [[ "$response" =~ ^([jJ][aA]|[jJ])$ ]]; then
		echo "Öppnar de valda filerna…"

		# Loopa igenom filerna igen och öppna dem
		echo "$SELECTED_FILES" | while IFS= read -r FILE_TO_OPEN; do
			if [ -n "$FILE_TO_OPEN" ]; then
				# Kör xdg-open i bakgrunden för varje fil (&) för att undvika att vänta
				# på att varje applikation stängs.
				xdg-open "$FILE_TO_OPEN" &> /dev/null &
			fi
		done

		echo "Klart. Fönstren/applikationerna kommer nu att visas."
	else
		echo "Öppning av filer avbröts. Avslutar skriptet."
	fi
}

# Kör funktionen
fzf_select_open_multi

