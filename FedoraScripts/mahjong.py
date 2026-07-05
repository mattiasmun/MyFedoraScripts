#!/usr/bin/env python3
from collections import deque, defaultdict
import random
import time

EMPTY = 0
DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]

class Board:
    def __init__(self, matrix):
        self.raw_rows = len(matrix)
        self.raw_cols = len(matrix[0])
        
        self.grid = [[EMPTY] * (self.raw_cols + 2)]
        for row in matrix:
            self.grid.append([EMPTY] + row + [EMPTY])
        self.grid.append([EMPTY] * (self.raw_cols + 2))
        
        self.height = len(self.grid)
        self.width = len(self.grid[0])
        
        self.alive_tiles = defaultdict(set)
        for r in range(1, self.raw_rows + 1):
            for c in range(1, self.raw_cols + 1):
                val = self.grid[r][c]
                if val != EMPTY:
                    self.alive_tiles[val].add((r, c))
                    
        self.remaining_pairs = sum(len(pos) for pos in self.alive_tiles.values()) // 2
        
        rng = random.Random(0)
        self.zobrist_table = {}
        for val, positions in self.alive_tiles.items():
            for pos in positions:
                self.zobrist_table[(pos, val)] = rng.getrandbits(64)
                
        self.current_hash = 0
        for val, positions in self.alive_tiles.items():
            for pos in positions:
                self.current_hash ^= self.zobrist_table[(pos, val)]

    def is_empty(self):
        return self.remaining_pairs == 0

    def remove(self, p1, p2, val):
        self.grid[p1[0]][p1[1]] = EMPTY
        self.grid[p2[0]][p2[1]] = EMPTY
        self.alive_tiles[val].remove(p1)
        self.alive_tiles[val].remove(p2)
        self.current_hash ^= self.zobrist_table[(p1, val)]
        self.current_hash ^= self.zobrist_table[(p2, val)]
        self.remaining_pairs -= 1

    def restore(self, p1, p2, val):
        self.grid[p1[0]][p1[1]] = val
        self.grid[p2[0]][p2[1]] = val
        self.alive_tiles[val].add(p1)
        self.alive_tiles[val].add(p2)
        self.current_hash ^= self.zobrist_table[(p1, val)]
        self.current_hash ^= self.zobrist_table[(p2, val)]
        self.remaining_pairs += 1

    def find_path(self, p1, p2):
        """
        C. Rita själva vägen.
        Modifierad BFS som returnerar den exakta vägen (lista med koordinater) 
        om p1 och p2 kan kopplas, annars None.
        """
        r1, c1 = p1
        r2, c2 = p2
        
        # Kön lagrar (r, c, path_so_far)
        queue = deque([(r1, c1, [(r1, c1)])])
        visited = [[[3] * 4 for _ in range(self.width)] for _ in range(self.height)]
        
        for d, (dr, dc) in enumerate(DIRS):
            nr, nc = r1 + dr, c1 + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if self.grid[nr][nc] == EMPTY:
                    queue.append((nr, nc, [(r1, c1), (nr, nc)]))
                    visited[nr][nc][d] = 0
                elif (nr, nc) == p2:
                    return [(r1, c1), (nr, nc)]

        while queue:
            r, c, path = queue.popleft()
            turns = min(visited[r][c])
            
            if turns >= 2:
                for curr_dir in range(4):
                    if visited[r][c][curr_dir] == 2:
                        dr, dc = DIRS[curr_dir]
                        nr, nc = r + dr, c + dc
                        current_path = list(path)
                        while 0 <= nr < self.height and 0 <= nc < self.width:
                            current_path.append((nr, nc))
                            if (nr, nc) == p2:
                                return current_path
                            if self.grid[nr][nc] != EMPTY:
                                break
                            nr += dr
                            nc += dc
                continue

            for next_dir, (dr, dc) in enumerate(DIRS):
                for curr_dir in range(4):
                    base_turns = visited[r][c][curr_dir]
                    if base_turns > 2:
                        continue
                        
                    is_turn = (next_dir != curr_dir)
                    next_turns = base_turns + (1 if is_turn else 0)
                    if next_turns > 2:
                        continue
                        
                    nr, nc = r + dr, c + dc
                    current_path = list(path)
                    while 0 <= nr < self.height and 0 <= nc < self.width:
                        current_path.append((nr, nc))
                        if (nr, nc) == p2:
                            return current_path
                        if self.grid[nr][nc] != EMPTY:
                            break
                            
                        if next_turns < visited[nr][nc][next_dir]:
                            visited[nr][nc][next_dir] = next_turns
                            queue.append((nr, nc, current_path))
                            
                        nr += dr
                        nc += dc
        return None

    def get_legal_moves(self, stats=None):
        moves = defaultdict(list)
        for val, active_tiles in self.alive_tiles.items():
            n = len(active_tiles)
            if n < 2:
                continue
            tiles_list = list(active_tiles)
            for i in range(n):
                for j in range(i + 1, n):
                    p1 = tiles_list[i]
                    p2 = tiles_list[j]
                    
                    if stats:
                        stats["connectable_calls"] += 1
                        
                    # Använder find_path istället för connectable för att kunna spara vägen vid behov
                    if self.find_path(p1, p2) is not None:
                        moves[val].append((p1, p2))
        return moves

    def print_ascii(self):
        """ B. ASCII-animation-hjälpare. Skriver ut det inre brädet. """
        for r in range(1, self.height - 1):
            row_str = []
            for c in range(1, self.width - 1):
                val = self.grid[r][c]
                row_str.append(f"{val:2}" if val != EMPTY else " .")
            print(" ".join(row_str))
        print("-" * (self.raw_cols * 3))


class Solver:
    def __init__(self, board):
        self.board = board
        self.solution_path = []
        self.transposition_table = set()
        self.legal_moves_cache = {}
        
        # D. Statistikinsamling
        self.stats = {
            "dfs_nodes": 0,
            "backtracks": 0,
            "connectable_calls": 0,
            "cache_hits": 0,
            "max_depth": 0,
            "start_time": 0.0
        }

    def order_moves(self, legal_moves_dict):
        flat_moves = []
        for val, pairs in legal_moves_dict.items():
            type_flexibility = len(pairs)
            for p1, p2 in pairs:
                dist_p1 = min(p1[0], self.board.height - 1 - p1[0], p1[1], self.board.width - 1 - p1[1])
                dist_p2 = min(p2[0], self.board.height - 1 - p2[0], p2[1], self.board.width - 1 - p2[1])
                edge_priority = min(dist_p1, dist_p2)
                flat_moves.append((type_flexibility, edge_priority, p1, p2, val))
                
        flat_moves.sort(key=lambda x: (x[0], x[1]))
        return [(m[2], m[3], m[4]) for m in flat_moves]

    def solve(self, current_depth=0):
        if current_depth == 0:
            self.stats["start_time"] = time.time()
            
        self.stats["dfs_nodes"] += 1
        if current_depth > self.stats["max_depth"]:
            self.stats["max_depth"] = current_depth

        if self.board.is_empty():
            return True

        board_hash = self.board.current_hash
        if board_hash in self.transposition_table:
            return False
            
        if board_hash in self.legal_moves_cache:
            self.stats["cache_hits"] += 1
            legal_moves_dict = self.legal_moves_cache[board_hash]
        else:
            legal_moves_dict = self.board.get_legal_moves(self.stats)
            self.legal_moves_cache[board_hash] = legal_moves_dict
        
        if not legal_moves_dict:
            self.stats["backtracks"] += 1
            self.transposition_table.add(board_hash)
            return False

        ordered_moves = self.order_moves(legal_moves_dict)

        for p1, p2, val in ordered_moves:
            if self.board.grid[p1[0]][p1[1]] == EMPTY or self.board.grid[p2[0]][p2[1]] == EMPTY:
                continue

            self.board.remove(p1, p2, val)
            self.solution_path.append((p1, p2, val))

            if self.solve(current_depth + 1):
                return True

            self.board.restore(p1, p2, val)
            self.solution_path.pop()

        self.stats["backtracks"] += 1
        self.transposition_table.add(board_hash)
        return False

    def print_diagnostics(self):
        """ Skriver ut den insamlade statistiken i ett snyggt format. """
        elapsed = time.time() - self.stats["start_time"]
        print("\n=== SÖKSTATISTIK ===")
        print(f"DFS-noder:         {self.stats['dfs_nodes']:,}")
        print(f"Backtracks:        {self.stats['backtracks']:,}")
        print(f"find_path() anrop: {self.stats['connectable_calls']:,}")
        print(f"Cache-träffar:     {self.stats['cache_hits']:,}")
        print(f"Max djup:          {self.stats['max_depth']}")
        print(f"Exekveringstid:    {elapsed:.3f} s")
        print("====================\n")

def verify_and_animate_solution(original_matrix, solution_path, delay=0.2):
    """
    Spelar upp och verifierar lösningssekvensen steg för steg.
    Visar exakt vilken väg lasern tog mellan brickorna.
    """
    print("Inleder verifiering och animering...\n")
    sim_board = Board(original_matrix)
    
    for idx, (p1, p2, val) in enumerate(solution_path):
        # 1. Hämta den exakta vägen innan vi tar bort brickorna
        path = sim_board.find_path(p1, p2)
        
        if path is None:
            print(f"❌ KORREKTHETSBUGG: Drag {idx+1} Matcha par {val} på {p1} och {p2} är INTE tillåtet!")
            return False
            
        # Konvertera koordinater till det inre brädets index för användarvänlig utskrift
        user_p1 = (p1[0]-1, p1[1]-1)
        user_p2 = (p2[0]-1, p2[1]-1)
        
        print(f"Drag {idx+1:02d}: Matcha par {val} mellan {user_p1} och {user_p2}")
        print(f"-> Laserlinje: {' -> '.join(str((r-1, c-1)) for r, c in path)}")
        
        # Verkställ draget
        sim_board.remove(p1, p2, val)
        
        # Visa brädet efter draget
        sim_board.print_ascii()
        time.sleep(delay)
        
    if sim_board.is_empty():
        print("✅ VERIFIERING LYCKADES: Alla drag var giltiga och brädet är helt tomt!")
        return True
    else:
        print("❌ VERIFIERING MISSLYCKADES: Lösningslistan tog slut men brädet innehåller fortfarande brickor.")
        return False

if __name__ == "__main__":
    board_matrix = [
        [1,2,3,4,5,6,7,5],
        [8,9,10,6,11,12,6,9],
        [2,8,13,10,11,14,15,16],
        [17,12,6,11,7,15,18,19],
        [20,21,10,15,22,10,10,6],
        [23,22,19,4,20,17,10,18],
        [13,1,6,15,11,8,8,14],
        [24,22,22,21,23,3,16,24],
    ]

    game_board = Board(board_matrix)
    solver = Solver(game_board)

    print("Löser pusslet...")
    if solver.solve():
        print("\nPusslet är löst! Här är dragen i ordning:")
        for idx, (p1, p2, val) in enumerate(solver.solution_path, 1):
            # Justera koordinaterna med -1 för att matcha användarens 0-indexerade bräde
            print(f"Drag {idx:02d}: Matcha par {val} på ({p1[0]-1}, {p1[1]-1}) och ({p2[0]-1}, {p2[1]-1})")
        solver.print_diagnostics()
        #verify_and_animate_solution(board_matrix, solver.solution_path)
    else:
        print("\nPusslet gick inte att lösa.")
