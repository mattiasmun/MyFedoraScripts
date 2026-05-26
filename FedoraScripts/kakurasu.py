#!/usr/bin/env python3
# ============================================================
#  KAKURASU SOLVER V4 - PYTHON EDITION
# ============================================================
#
#  Funktioner:
#
#  ✔ MRV heuristic (mest begränsad rad först)
#  ✔ Bitmaskbaserad sökning
#  ✔ Förberäknade mask-summor och kolumner
#  ✔ Kandidatdomäner per rad
#  ✔ Aggressiv kolumnpruning
#  ✔ Min/max interval propagation
#  ✔ Constraint-baserad pruning
#  ✔ Cacheade kolumnmöjligheter
#  ✔ Immutable lookup-tabeller (tuples)
#  ✔ Stöd för jokrar (None)
#  ✔ Live-status och statistik
#  ✔ LibreOffice Calc-integration
#
#  Optimeringar:
#
#  • Bitmasker istället för bool-matriser
#  • Förberäknade lookup-tabeller
#  • Cachevänliga immutable datastrukturer
#  • Minimal Python-overhead i sökträdet
#  • Tidig pruning av omöjliga kolumnsummor
#
# ============================================================

from time import perf_counter


SIZE = 9
BIT_SIZE = 1 << SIZE

# ============================================================
# HJÄLPDATA
# ============================================================

ROW_VALUES = tuple([r + 1 for r in range(SIZE)])
BIT_VALUES = tuple([1 << i for i in range(SIZE)])

MASK_SUM = [0] * BIT_SIZE
MASK_COLS = [[] for _ in range(BIT_SIZE)]

for mask in range(BIT_SIZE):

    cols = []
    s = 0

    for bit in range(SIZE):

        if mask & BIT_VALUES[bit]:
            cols.append(bit + 1)
            s += bit + 1

    MASK_COLS[mask] = tuple(cols)
    MASK_SUM[mask] = s

MASK_SUM = tuple(MASK_SUM)
MASK_COLS = tuple(MASK_COLS)

# ============================================================
# SOLVER
# ============================================================

class KakurasuSolver:

    def __init__(self, row_targets, col_targets):

        self.row_targets = tuple(row_targets)
        self.col_targets = tuple(col_targets)

        self.grid = [[0] * SIZE for _ in range(SIZE)]

        self.row_sums = [0] * SIZE
        self.col_sums = [0] * SIZE

        self.recursions = 0
        self.backtracks = 0

        self.start_time = perf_counter()
        self.last_status = perf_counter()

        # ====================================================
        # Kandidater per rad
        # ====================================================

        self.domains = []

        for r in range(SIZE):

            target = row_targets[r]

            if target is None:

                candidates = list(range(BIT_SIZE))

            else:

                candidates = [
                    m for m in range(BIT_SIZE)
                    if MASK_SUM[m] == target
                ]

            self.domains.append(tuple(candidates))

        self.row_solved = [False] * SIZE

        self.row_col_possible = [
            [False] * SIZE
            for _ in range(SIZE)
        ]

        self.row_col_mandatory = [
            [False] * SIZE
            for _ in range(SIZE)
        ]

        for row in range(SIZE):

            for col in range(SIZE):

                self.row_col_possible[row][col] = any(
                    mask & BIT_VALUES[col]
                    for mask in self.domains[row]
                )

                self.row_col_mandatory[row][col] = all(
                    mask & BIT_VALUES[col]
                    for mask in self.domains[row]
                )

    # ========================================================
    # STATUS
    # ========================================================

    def status(self, row):

        now = perf_counter()

        if now - self.last_status > 0.5:

            print(
                f"\r"
                f"Rad: {ROW_VALUES[row]} | "
                f"Rekursioner: {self.recursions:,} | "
                f"Backtracks: {self.backtracks:,} | "
                f"Tid: {now - self.start_time:.1f}s",
                end=""
            )

            self.last_status = now

    # ========================================================
    # MRV
    # ========================================================

    def choose_row(self):

        best_row = None
        best_size = 999999

        for r in range(SIZE):

            if not self.row_solved[r]:

                size = len(self.domains[r])

                if size < best_size:

                    best_size = size
                    best_row = r

        return best_row

    # ========================================================
    # APPLY ROW
    # ========================================================

    def apply_row(self, row, mask):

        for col in MASK_COLS[mask]:

            self.grid[row][col - 1] = 1

            self.row_sums[row] += col
            self.col_sums[col - 1] += ROW_VALUES[row]

    # ========================================================
    # REMOVE ROW
    # ========================================================

    def remove_row(self, row, mask):

        for col in MASK_COLS[mask]:

            self.grid[row][col - 1] = 0

            self.row_sums[row] -= col
            self.col_sums[col - 1] -= ROW_VALUES[row]

    # ========================================================
    # PRUNING
    # ========================================================

    def columns_possible(self):

        for col in range(SIZE):

            target = self.col_targets[col]

            if target is None:
                continue

            current = self.col_sums[col]

            # ============================================
            # För stor direkt
            # ============================================

            if current > target:
                return False

            if current == target:

                for row in range(SIZE):

                    if self.row_solved[row]:
                        continue

                    if self.row_col_mandatory[row][col]:
                        return False

                continue

            # ============================================
            # Min/max möjliga framtida summa
            # ============================================

            min_possible = current
            max_possible = current

            for row in range(SIZE):

                if self.row_solved[row]:
                    continue

                possible = self.row_col_possible[row][col]
                mandatory = self.row_col_mandatory[row][col]

                # ========================================
                # Någon kandidat kan fylla kolumnen
                # ========================================

                value = ROW_VALUES[row]

                if possible:
                    max_possible += value

                # ========================================
                # Alla kandidater måste fylla kolumnen
                # ========================================

                if mandatory:
                    min_possible += value

            # ============================================
            # Interval pruning
            # ============================================

            if target < min_possible:
                return False

            if target > max_possible:
                return False

        return True

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    def final_validation(self):

        for r in range(SIZE):

            target = self.row_targets[r]

            if target is not None:

                if self.row_sums[r] != target:
                    return False

        for c in range(SIZE):

            target = self.col_targets[c]

            if target is not None:

                if self.col_sums[c] != target:
                    return False

        return True

    # ========================================================
    # SOLVE
    # ========================================================

    def solve(self):

        self.recursions += 1

        row = self.choose_row()

        self.status(row if row is not None else 0)

        # ====================================================
        # Klar?
        # ====================================================

        if row is None:
            return self.final_validation()

        domain = self.domains[row][:]

        for mask in domain:

            self.apply_row(row, mask)

            self.row_solved[row] = True

            if self.columns_possible():

                if self.solve():
                    return True

            self.row_solved[row] = False

            self.remove_row(row, mask)

            self.backtracks += 1

        return False

    # ========================================================
    # PRINT
    # ========================================================

    def print_solution(self):

        print("\n")

        for r in range(SIZE):

            line = []

            for c in range(SIZE):

                if self.grid[r][c]:
                    line.append("■")
                else:
                    line.append("·")

            print(" ".join(line))

        print("\n")

        print(f"Rekursioner: {self.recursions:,}")
        print(f"Backtracks: {self.backtracks:,}")
        print(f"Tid: {perf_counter() - self.start_time:.4f}s")


# ============================================================
# EXEMPEL
# ============================================================

if __name__ == "__main__":

    row_targets = [
        10,
        10,
        10,
        10,
        5,
        10,
        10,
        10,
        10
    ]

    col_targets = [
        10,
        10,
        10,
        10,
        5,
        10,
        10,
        10,
        10
    ]

    solver = KakurasuSolver(
        row_targets=row_targets,
        col_targets=col_targets
    )

    if solver.solve():

        solver.print_solution()

    else:

        print("Ingen lösning hittades.")

def solve_current_sheet():

    doc = XSCRIPTCONTEXT.getDocument()

    # Hämtar den controller som faktiskt styr kalkylbladet,
    # oavsett om makroredigeraren är i fokus eller inte
    view_cursor = doc.getCurrentController()
    sheet = view_cursor.getActiveSheet()

    # ============================================
    # Läs radmål
    # ============================================

    row_targets = []

    for r in range(SIZE):

        cell = sheet.getCellByPosition(0, r + 1)
        val = cell.getString().strip()

        if val in ("", "?"):
            row_targets.append(None)
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
            col_targets.append(None)
        else:
            col_targets.append(int(val))

    # ============================================
    # Lös
    # ============================================

    solver = KakurasuSolver(
        row_targets=row_targets,
        col_targets=col_targets
    )

    ok = solver.solve()

    # ============================================
    # Skriv lösning
    # ============================================

    if ok:

        for r in range(SIZE):

            for c in range(SIZE):

                if solver.grid[r][c]:

                    sheet.getCellByPosition(
                        c + 1,
                        r + 1
                    ).String = "O"

                else:

                    sheet.getCellByPosition(
                        c + 1,
                        r + 1
                    ).String = "X"

    else:

        sheet.getCellByPosition(11, 0).String = \
            "Ingen lösning hittades"

g_exportedScripts = (
    solve_current_sheet,
)
