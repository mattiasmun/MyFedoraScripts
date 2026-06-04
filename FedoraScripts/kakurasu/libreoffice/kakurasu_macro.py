#!/usr/bin/env python3
#
# Kakurasu Solver
# Copyright (C) 2026 Mattias Münster
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details:
# https://www.gnu.org/licenses/
#

import json
import subprocess

SIZE = 9


def solve_current_sheet():

    doc = XSCRIPTCONTEXT.getDocument()

    controller = doc.getCurrentController()
    sheet = controller.getActiveSheet()

    # ============================================
    # Läs radmål
    # ============================================

    row_targets = []

    for r in range(SIZE):

        cell = sheet.getCellByPosition(0, r + 1)
        val = cell.getString().strip()

        if val in ("", "?"):
            row_targets.append(-1)
        else:
            row_targets.append(int(val))

    # ============================================
    # Läs kolumnmål
    # ============================================

    col_targets = []

    for c in range(SIZE):

        cell = sheet.getCellByPosition(c + 1, 0)
        val = cell.getString().strip()

        if val in ("", "?"):
            col_targets.append(-1)
        else:
            col_targets.append(int(val))

    # ============================================
    # Anropa Vala-solvern
    # ============================================

    request = {
        "rows": row_targets,
        "cols": col_targets
    }

    result = subprocess.run(
        ["/home/mmunster/.local/bin/kakurasu"],
        input=json.dumps(request),
        text=True,
        capture_output=True
    )

    if result.returncode != 0:

        sheet.getCellByPosition(11, 0).String = (
            "Solverfel"
        )

        sheet.getCellByPosition(11, 1).String = (
            result.stderr
        )

        return

    # ============================================
    # Tolka JSON-svar
    # ============================================

    try:

        response = json.loads(
            result.stdout
        )
        recursions = response.get("recursions", 0)
        backtracks = response.get("backtracks", 0)
        elapsed = response.get("time", 0.0)

    except Exception as e:

        sheet.getCellByPosition(11, 0).String = (
            f"JSON-fel: {e}"
        )

        return

    # ============================================
    # Ingen lösning
    # ============================================

    if not response.get("ok", False):

        sheet.getCellByPosition(11, 0).String = "Status"
        sheet.getCellByPosition(12, 0).String = "Ingen lösning"

        sheet.getCellByPosition(11, 1).String = "Rekursioner"
        sheet.getCellByPosition(12, 1).Value = recursions

        sheet.getCellByPosition(11, 2).String = "Backtracks"
        sheet.getCellByPosition(12, 2).Value = backtracks

        sheet.getCellByPosition(11, 3).String = "Tid (s)"
        sheet.getCellByPosition(12, 3).Value = elapsed

        return

    # ============================================
    # Skriv lösning
    # ============================================

    grid = response["grid"]

    for r in range(SIZE):

        for c in range(SIZE):

            sheet.getCellByPosition(
                c + 1,
                r + 1
            ).String = (
                "O"
                if grid[r][c]
                else "X"
            )

    sheet.getCellByPosition(11, 0).String = "Status"
    sheet.getCellByPosition(12, 0).String = "Löst"

    sheet.getCellByPosition(11, 1).String = "Rekursioner"
    sheet.getCellByPosition(12, 1).Value = recursions

    sheet.getCellByPosition(11, 2).String = "Backtracks"
    sheet.getCellByPosition(12, 2).Value = backtracks

    sheet.getCellByPosition(11, 3).String = "Tid (s)"
    sheet.getCellByPosition(12, 3).Value = elapsed


g_exportedScripts = (
    solve_current_sheet,
)
