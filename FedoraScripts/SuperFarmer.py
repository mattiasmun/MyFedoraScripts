# ————————————————————————————
# GEMINI MASTER FARMER v3.0
# ————————————————————————————

# ———————————————————————————————————
# MASTER CONTROL LOOP - STARTA DENNA!
# ———————————————————————————————————

def main_farm_manager():
    while True:
        # 1. EVOLUTION: Försök låsa upp nya förmågor
        auto_unlock_progression()

        # Flytta till (0, 0) för att scanna typ av fält
        move_to(0, 0)
        entity = get_entity_type()
        gold = num_items(Items.Gold)

        # Prioritetsordning: Pumpa > Kaktus > Resten
        if gold > 1000000:
            run_pumpkin_cycle()
        elif gold > 500000 or entity == Entities.Cactus:
            run_cactus_cycle()
        else:
            # Annars kör vi din guld-vinnande solros/morots-loop
            snake_harvest()

# ————————————————————————————————
# PUMPA-MODUL (MEGA-KLUSTER LOGIK)
# ————————————————————————————————

def run_pumpkin_cycle():
    size = get_world_size()
    if size not in moves: return

    # Hjälpfunktion för att säkra frön
    def ensure_pumpkin_seeds():
        if num_items(Items.Pumpkin_Seed) < 10:
            trade(Items.Pumpkin_Seed, 100)
    # Steg 1: Plantera pumpor effektivt
    for direction in moves[size]:
        smart_move(direction)
        if get_entity_type() != Entities.Pumpkin:
            if can_harvest(): harvest()
            prepare_ground(Grounds.Soil)
            ensure_pumpkin_seeds()
            plant(Entities.Pumpkin)
            water = should_water(Entities.Pumpkin)
            if water: water_tile(water)

    # Steg 2: Vänta och optimera kluster
    max_passes = 20
    passes = 0
    while passes < max_passes:
        all_mega = True
        passes += 1
        for direction in moves[size]:
            smart_move(direction)
            if get_entity_type() == Entities.Dead_Pumpkin: # Död pumpa, plantera en ny pumpa
                ensure_pumpkin_seeds()
                plant(Entities.Pumpkin)
                water = should_water(Entities.Pumpkin)
                if water: water_tile(water)
                all_mega = False
        if all_mega:
            break

    # Steg 3: Skörda klustret
    harvest()

# ————————————————————————————
# KAKTUS-MODUL (SORTERING n^2)
# ————————————————————————————

def run_cactus_cycle():
    size = get_world_size()
    if size not in moves: return
    # Steg 1: Plantera
    for direction in moves[size]:
        smart_move(direction)
        if get_entity_type() != Entities.Cactus:
            if can_harvest(): harvest()
            prepare_ground(Grounds.Soil)
            plant(Entities.Cactus)

    # 2. Sortera
    for _ in range(3):
        diagonal_cactus_pass()
    optimize_cactus_field()

    # 3. Vänta (Smart väntan på sista rutan)
    move_to(size - 1, size - 1)
    while not can_harvest(): pass

    optimize_cactus_field()

    # 4. Skörda kedjereaktion
    move_to(0, 0)
    if harvest(): # Startar kedjereaktionen
        quick_print("Kaktus-vinst inkasserad!")

# ————————————————————————————————
# SNAKE HARVEST (STANDARD EKONOMI)
# ————————————————————————————————

def snake_harvest():
    size = get_world_size()
    if size not in moves: return
    x, y = 0, 0
    sun_points = []
    max_petals = -1

    for direction in moves[size]:
        smart_move(direction)
        entity = get_entity_type()
        x, y = get_pos_x(), get_pos_y()
        if entity == Entities.Sunflower:
            p = measure()
            if p > max_petals:
                max_petals = p
                sun_points = [(x, y)]
            elif p == max_petals and p != -1:
                sun_points.append((x, y))
        manage_tile(entity, x, y)

    if len(sun_points) > 0:
        cx, cy = get_pos_x(), get_pos_y()
        sun_points = sort_by_distance(sun_points, cx, cy)
        for point in sun_points:
            move_to(point[0], point[1])
            if can_harvest(): harvest()

# ————————————————————————————
# HJÄLPFUNKTIONER OCH RÖRELSE
# ————————————————————————————

def manage_tile(entity, x, y):
    if entity == Entities.Cactus: return
    should_plant = False
    if entity == None:
        should_plant = True
    elif entity != Entities.Sunflower and can_harvest():
        should_plant = harvest()

    if should_plant:
        target = get_best_crop(x, y)
        if target == Entities.Sunflower: plant(Entities.Sunflower)
        elif target == Entities.Carrots:
            prepare_ground(Grounds.Soil)
            plant(Entities.Carrots)
        elif target == Entities.Grass: prepare_ground(Grounds.Turf)
        elif target == Entities.Tree: plant(Entities.Tree)
        else: plant(Entities.Bush)

    water = should_water(get_entity_type())
    if water: water_tile(water)

def move_to(target_x, target_y):
    attempts = 0
    while (get_pos_x() != target_x or get_pos_y() != target_y) and attempts < 100:
        move_val = 0
        cur_x, cur_y = get_pos_x(), get_pos_y()

        # Bestäm horisontell bit (East=1, West=4)
        if cur_x < target_x:
            move_val += 1
        elif cur_x > target_x:
            move_val += 4

        # Bestäm vertikal bit (North=2, South=8)
        if cur_y < target_y:
            move_val += 2
        elif cur_y > target_y:
            move_val += 8

        # Utför förflyttningen (smart_move hanterar om det är rakt eller diagonalt)
        if move_val > 0:
            smart_move(move_val)

        # Kontrollera om vi faktiskt rörde oss (för att undvika oändliga loopar)
        if get_pos_x() == cur_x and get_pos_y() == cur_y:
            attempts += 1
        else:
            attempts = 0

def water_tile(amount):
    water_count = num_items(Items.Water)
    if (water_count < 10) and (num_items(Items.Empty_Tank) < 10):
        trade(Items.Empty_Tank, 100)
    if num_items(Items.Water) > 0:
        actual_use = min(amount, num_items(Items.Water))
        use_item(Items.Water, actual_use)

def should_water(entity):
    water_level = get_water()
    # Om det redan är över 75% fukt, gör ingenting
    if water_level >= 0.75: return False
    exclusive_crops = [Entities.Carrots, Entities.Sunflower, Entities.Pumpkin]
    if entity in exclusive_crops:
        # returnera 1 till 3 tankar beroende på fuktighet
        return 3 - (water_level // 0.25)
    return False

def my_range(size, coordinate):
    if coordinate < (size / 2): return range(size)
    return range(size - 1, -1, -1)

def prepare_ground(target):
    if get_ground_type() != target: till()

def get_best_crop(x, y):
    gold = num_items(Items.Gold)
    # Lyx-grödor
    if gold > 1000000:
        if num_items(Items.Pumpkin_Seed) > 0 or trade(Items.Pumpkin_Seed, 100):
            return Entities.Pumpkin
    if gold > 50000:
        if num_items(Items.Sunflower_Seed) > 0 or trade(Items.Sunflower_Seed, 50):
            return Entities.Sunflower
    # Resurs-balansering
    total_tiles = get_world_size() ** 2
    req = total_tiles * 40
    hay, wood = num_items(Items.Hay), num_items(Items.Wood)
    carr = num_items(Items.Carrot)
    if min(hay, wood) >= req and carr < wood: return Entities.Carrots
    if (x + y) & 1 == 0:
        if wood < hay: return Entities.Tree
    return Entities.Grass

def auto_unlock_progression():
    # Prioriterad ordning för maximal tillväxt
    upgrades = [
        # 1. Grundläggande logik (Krävs för att koden ska köra)
        Unlocks.Variables, Unlocks.Operators, Unlocks.Loops,
        Unlocks.Functions, Unlocks.Lists, Unlocks.Senses,

        # 2. Bas-ekonomi & Överlevnad
        Unlocks.Plant, Unlocks.Grass, Unlocks.Trees,
        Unlocks.Carrots, Unlocks.Watering, Unlocks.Fertilizer,

        # 3. Expansion & Snabbhet (Viktigast för v3.0)
        Unlocks.Expand, Unlocks.Speed, Unlocks.Multi_Trade,

        # 4. High-End Grödor
        Unlocks.Sunflowers, Unlocks.Cactus, Unlocks.Pumpkin,

        # 5. Avancerat (När du har allt annat)
        Unlocks.Mazes, Unlocks.Polyculture, Unlocks.Dinosaurs
    ]

    for item in upgrades:
        if unlock(item):
            # Vi gör en quick_print för att veta vad som hände i loggen
            quick_print("Utveckling: " + str(item))
            break # Tar 200 ops, så vi kör bara en per cykel

def optimize_cactus_field():
    size = get_world_size()
    # Kör flera pass för att garantera ordning (Bubble sort i 2D)
    for i in range(size * size):
        swapped = False
        move_to(0, 0)

        # Vi använder en sicksack-rörelse för att täcka hela fältet
        for x in range(size):
            for y in range(size):
                # Kontrollera Öst
                if x < size - 1:
                    if measure() > measure(East):
                        swap(East)
                        swapped = True
                # Kontrollera Norr
                if y < size - 1:
                    if measure() > measure(North):
                        swap(North)
                        swapped = True

                # Flytta till nästa ruta i sicksack
                if x & 1 == 0:
                    if y < size - 1: move(North)
                    else: move(East)
                else:
                    if y > 0: move(South)
                    else: move(East)

        # Om vi inte gjorde några byten på hela fältet är det perfekt sorterat!
        if not swapped:
            break

def diagonal_cactus_pass():
    size = get_world_size()
    # Börja i nedre vänstra hörnet
    for start_node in range(size):
        move_to(start_node, 0)
        # Klättra diagonalt så långt det går
        while get_pos_x() < size - 1 and get_pos_y() < size - 1:
            # Triangel-sortering
            if measure() > measure(North): swap(North)
            if measure() > measure(East): swap(East)

            # Grann-check (Valfritt men effektivt)
            move(North)
            if measure() > measure(East): swap(East)
            move(South)

            # Din säkra diagonal-metod
            if not move_northeast():
                break

def diagonal_cactus_check():
    # En snabb check för att se om fältet är någorlunda sorterat
    # Jämför hörnet (0,0) med (size-1, size-1)
    move_to(0, 0)
    val_min = measure()
    move_to(get_world_size() - 1, get_world_size() - 1)
    val_max = measure()
    return val_min <= val_max

def sort_by_distance(points, cx, cy):
    n = len(points)
    for i in range(n):
        for j in range(0, n - i - 1):
            p1, p2 = points[j], points[j + 1]
            d1 = abs(p1[0] - cx) + abs(p1[1] - cy)
            d2 = abs(p2[0] - cx) + abs(p2[1] - cy)
            if d1 > d2:
                points[j], points[j + 1] = points[j + 1], points[j]
    return points

def smart_move(direction):
    a, b = True, True
    if direction & 2:
        a = move(North)
    elif direction & 8:
        a = move(South)
    if direction & 1:
        b = move(East)
    elif direction & 4:
        b = move(West)
    return a and b

def move_northeast():
    return smart_move(3)

def move_northwest():
    return smart_move(6)

def move_southeast():
    return smart_move(9)

def move_southwest():
    return smart_move(12)

moves = {}
for s in range(3, 13):
    if s & 1 == 0:
        moves[s] = generate_even_hamiltonian_path(s)
    else:
        moves[s] = generate_odd_hamiltonian_path(s)

def generate_even_hamiltonian_path(size):
    path = [2] * (size - 1)
    # Vi går igenom fältet kolumn för kolumn
    for x in range(size - 2):
        path += [1] # Ta ett steg East (1)
        # Om vi är på en jämn kolumn (0, 2, 4…), gå North (2)
        # Om vi är på en udda kolumn (1, 3, 5…), gå South (8)
        if x & 1 == 0:
            for _ in range(size - 2):
                path += [8] # North
        else:
            for _ in range(size - 2):
                path += [2] # South
    # Efter sista kolumnen är vi längst upp till höger.
    # För att göra den till en "Circuit" (tillbaka till (0, 0)) lägger vi till hemresan.
    path += [1]
    path += [8] * (size - 1) # South ner till (size-1, 0)
    path += [4] * (size - 1) # West hela vägen tillbaka till (0, 0)
    return path

def generate_odd_hamiltonian_path(size):
    if size == 3:
        return [3, 4, 2, 1, 1, 8, 8, 4, 4]
    path = []
    # 1. Inledande sicksack (skalar med size)
    # För 5: 1 rep, För 7: 2 reps, För 9: 3 reps
    for _ in range((size - 3) // 2):
        path += [2, 1, 2, 4]
    # 2. Övergång till mittsektionen
    path += [2, 2, 1, 8, 3]
    # 3. Expansionen i mitten (Horisontell vidd)
    # För 5: 1 st, För 7: 3 st, För 9: 5 st, För 11: 7 st
    num_ones = size - 3
    path += [1] * num_ones
    # 4. Den långa vertikala transporten
    # För 5: 4 st, För 7: 6 st, För 9: 8 st, För 11: 10 st
    num_eights = size - 1
    path += [8] * num_eights
    # 5. Trappstegs-returen (Den stora loop-sektionen)
    # För size 9 repeteras detta 3 gånger
    num_steps = (size - 3) // 2
    for _ in range(num_steps):
        path += [4]
        path += [2] * (size - 2)
        path += [4]
        path += [8] * (size - 2)
    # 6. Avslutande steg för att sluta cirkeln
    path += [4, 4]
    return path

def verify_path(size, path):
    # Startposition (0,0)
    x, y = 0, 0
    visited = set([(x, y)])

    # Dina specifika riktningar
    directions = {
        1: (1, 0),   # East (Höger)
        2: (0, 1),   # North (Upp)
        4: (-1, 0),  # West (Vänster)
        8: (0, -1),  # South (Ner)
        3: (1, 1)    # North-East (Diagonalt upp-höger)
    }

    for i, move in enumerate(path):
        if move not in directions:
            return False, f"Steg {i}: Okänd move {move}"

        dx, dy = directions[move]
        x += dx
        y += dy

        # Kontrollera att vi är inom brädet (0 till size-1)
        if not (0 <= x < size and 0 <= y < size):
            return False, f"Steg {i} ({move}): Utanför vid ({x}, {y})"

        # Registrera besöket
        visited.add((x, y))

    # Slutkontroll
    at_start = (x, y) == (0, 0)
    all_visited = len(visited) == size * size

    if not all_visited:
        return False, f"Missade {size*size - len(visited)} rutor. Landade på ({x}, {y})"
    if not at_start:
        return False, f"Besökte alla rutor men landade på ({x}, {y}) istället för (0,0)"

    return True, f"Succé! Alla {len(visited)} rutor besökta. Landade på (0,0)."

# Testkörning för storlekarna 3, 4, 5, 6, 7, 8, 9, 10, 11
def test_path(start, stop):
    print("——— TESTRESULTAT ———")
    for s in range(start, stop):
        if s in moves:
            success, msg = verify_path(s, moves[s])
            status = "❌"
            if success: status = "✅"
            print(f"Storlek {s:2}: {status} {msg}")

# START
while True:
    main_farm_manager()
