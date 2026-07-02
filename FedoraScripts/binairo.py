#!/usr/bin/env python3
import sys
from z3 import *

class Z3Solver:
    def __init__(self, board_strings):
        self.board = board_strings
        self.R = len(board_strings)
        self.C = len(board_strings[0])
        
        # 1. Använd Bool istället för Int
        self.grid = [[Bool(f"r{r}c{c}") for c in range(self.C)] for r in range(self.R)]
        self.solver = Solver()
        
        self._build_constraints()
        self._add_clues()

    def _build_constraints(self):
        # 2. Tre i rad (Optimerat med Sum av Bool-konvertering)
        for r in range(self.R):
            for c in range(self.C - 2):
                triple = [If(self.grid[r][c+i], 1, 0) for i in range(3)]
                self.solver.add(Sum(triple) != 0)
                self.solver.add(Sum(triple) != 3)

        for r in range(self.R - 2):
            for c in range(self.C):
                triple = [If(self.grid[r+i][c], 1, 0) for i in range(3)]
                self.solver.add(Sum(triple) != 0)
                self.solver.add(Sum(triple) != 3)

        # 3. Balans per rad och kolumn
        for r in range(self.R):
            self.solver.add(Sum([If(self.grid[r][c], 1, 0) for c in range(self.C)]) == self.C // 2)
        for c in range(self.C):
            self.solver.add(Sum([If(self.grid[r][c], 1, 0) for r in range(self.R)]) == self.R // 2)

        # 4. Unika rader och kolumner (Effektivare Or-syntax)
        for i in range(self.R):
            for j in range(i + 1, self.R):
                self.solver.add(Or([self.grid[i][c] != self.grid[j][c] for c in range(self.C)]))
        for i in range(self.C):
            for j in range(i + 1, self.C):
                self.solver.add(Or([self.grid[r][i] != self.grid[r][j] for r in range(self.R)]))

    def _add_clues(self):
        # 5. Parser för givna siffror
        for r in range(self.R):
            for c in range(self.C):
                ch = self.board[r][c]
                if ch == "1":
                    self.solver.add(self.grid[r][c] == True)
                elif ch == "0":
                    self.solver.add(self.grid[r][c] == False)

    def solve(self):
        # 6. Kontroll av unik lösning
        if self.solver.check() != sat:
            print("Ingen lösning existerar.")
            return None

        model = self.solver.model()
        first_solution = [[1 if is_true(model[self.grid[r][c]]) else 0 for c in range(self.C)] for r in range(self.R)]

        # Lägg till villkor för att blockera den första lösningen
        blocking_clause = Or([self.grid[r][c] != is_true(model[self.grid[r][c]]) for r in range(self.R) for c in range(self.C)])
        self.solver.add(blocking_clause)

        if self.solver.check() == sat:
            print("Varning: Pusslet har flera lösningar! (Inte unikt)")
        else:
            print("Pusslet har en unik lösning.")

        return first_solution

# --- 7. Verifierare (Ren Python, ingen Z3) ---
def verify_solution(board):
    R = len(board)
    C = len(board[0])
    
    # Konvertera till int-matris
    grid = [[int(char) for char in row.strip()] for row in board]
    
    # Kolla rader (balans och tre i rad)
    for r in range(R):
        if sum(grid[r]) != C / 2: return False, f"Obalans i rad {r+1}"
        for c in range(C - 2):
            if grid[r][c] == grid[r][c+1] == grid[r][c+2]: return False, f"Tre i rad i rad {r+1}"
            
    # Kolla kolumner (balans och tre i rad)
    for c in range(C):
        col_sum = sum(grid[r][c] for r in range(R))
        if col_sum != R / 2: return False, f"Obalans i kolumn {c+1}"
        for r in range(R - 2):
            if grid[r][c] == grid[r+1][c] == grid[r+2][c]: return False, f"Tre i rad i kolumn {c+1}"
            
    # Kolla unika rader/kolumner
    if len(set(tuple(row) for row in grid)) != R: return False, "Dubbletter av rader finns"
    if len(set(tuple(grid[r][c] for r in range(R)) for c in range(C))) != C: return False, "Dubbletter av kolumner finns"
    
    return True, "Lösningen är helt korrekt!"

# --- CLI-hantering ---
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Användning: python binairo.py --solve/--verify filnamn.txt")
        sys.exit(1)

    mode = sys.argv[1]
    filename = sys.argv[2]

    with open(filename, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if mode == "--verify":
        success, msg = verify_solution(lines)
        print(f"Verifiering: {msg}")
        sys.exit(0 if success else 1)

    elif mode == "--solve":
        solver = Z3Solver(lines)
        sol = solver.solve()
        if sol:
            print("\nLösning:")
            for row in sol:
                print(" ".join(map(str, row)))
