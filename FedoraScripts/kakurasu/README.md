# Kakurasu Solver

En snabb Kakurasu-lösare skriven i Vala med stöd för integration i LibreOffice Calc.

Programmet löser 9×9 Kakurasu-pussel och kan användas både från kommandoraden och direkt från LibreOffice via ett Python-makro.

## Funktioner

* Snabb backtracking-baserad lösare
* MRV (Minimum Remaining Values)
* Förberäknade domäner
* Aggressiv kolumnpruning
* Statistik över:

  * Rekursioner
  * Backtracks
  * Körtid
* JSON-baserat gränssnitt
* LibreOffice Calc-integration

---

## Beroenden

### Byggberoenden

* Meson
* Ninja
* Vala
* json-glib

På Fedora:

```bash
sudo dnf install meson ninja-build vala json-glib-devel
```

På Debian/Ubuntu:

```bash
sudo apt install meson ninja-build valac libjson-glib-dev
```

---

## Bygg och installation

Konfigurera projektet:

Meson-alternativ

Projektet definierar följande Meson-alternativ i meson_options.txt:

option(
  'libreoffice_python_dir',
  type : 'string',
  value : '',
  description : 'LibreOffice Python macro directory'
)

Alternativet används för att ange var LibreOffice-makrot ska installeras.

Exempel:

meson setup build \
  --prefix=$HOME/.local \
  -Dlibreoffice_python_dir=$HOME/.config/libreoffice/4/user/Scripts/python

Vid installation kopieras då kakurasu_macro.py automatiskt till LibreOffices användarkatalog för Python-makron.

Om alternativet utelämnas byggs solvern normalt, men inget LibreOffice-makro installeras.

```bash
meson setup build \
  --prefix=$HOME/.local \
  -Dlibreoffice_python_dir=$HOME/.config/libreoffice/4/user/Scripts/python
```

Kompilera:

```bash
meson compile -C build
```

Installera:

```bash
meson install -C build
```

Detta installerar:

```text
~/.local/bin/kakurasu
```

samt LibreOffice-makrot:

```text
~/.config/libreoffice/4/user/Scripts/python/kakurasu_macro.py
```

---

## Användning från kommandoraden

Programmet läser JSON från standard input.

Exempel:

```bash
echo '{
  "rows":[17,18,16,12,24,23,8,15,22],
  "cols":[16,26,20,11,26,24,17,8,7]
}' | kakurasu
```

Svar:

```json
{
  "ok": true,
  "grid": [...],
  "recursions": 123,
  "backtracks": 45,
  "time": 0.0012
}
```

Om ingen lösning finns:

```json
{
  "ok": false,
  "grid": [],
  "recursions": 100,
  "backtracks": 100,
  "time": 0.0005
}
```

---

## LibreOffice Calc

Efter installationen finns makrot:

```text
solve_current_sheet
```

Makrot läser ett 9×9 Kakurasu-pussel från det aktiva kalkylbladet.

### Format

Kolumnsummor placeras på första raden.

Radsummor placeras i första kolumnen.

Exempel:

```text
     16 26 20 11 26 24 17 8 7
17
18
16
12
24
23
 8
15
22
```

Tomma värden eller `?` behandlas som okända mål.

### Resultat

Efter lösning skrivs:

* `O` för ifyllda rutor
* `X` för tomma rutor

Dessutom visas:

* Status
* Rekursioner
* Backtracks
* Tid

---

## Projektstruktur

```text
.
├── meson.build
├── meson_options.txt
├── solver/
│   └── kakurasu.vala
└── libreoffice/
    └── kakurasu_macro.py
```

---

## Licens

Fri att använda, modifiera och distribuera.

