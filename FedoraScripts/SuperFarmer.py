# ==========================================
# GEMINI MASTER FARMER v3.0
# ==========================================

# ==========================================
# MASTER CONTROL LOOP - STARTA DENNA!
# ==========================================

def main_farm_manager():
    while True:
        # Flytta till (0,0) för att scanna typ av fält
        move_to(0, 0)
        entity = get_entity_type()
        gold = num_items(Items.Gold)

        # Prioritetsordning: Kaktus > Pumpa > Resten
        if gold > 1000000: # När du är riktigt rik
            run_pumpkin_cycle()
        elif gold > 500000 or entity == Entities.Cactus:
            run_cactus_cycle()
        else:
            # Annars kör vi din guld-vinnande solros/morots-loop
            snake_harvest()

def run_pumpkin_cycle():
    size = get_world_size()

    # Hjälpfunktion för att säkra frön
    def ensure_pumpkin_seeds():
        if num_items(Items.Pumpkin_Seed) < 10:
            trade(Items.Pumpkin_Seed, 100)

    # Steg 1: Plantera pumpor på hela fältet
    for x in range(size):
        for y in range(size):
            move_to(x, y)
            if get_entity_type() != Entities.Pumpkin:
                if can_harvest():
                    harvest()
                prepare_ground(Grounds.Soil)

                ensure_pumpkin_seeds() # Kolla frön innan plantering
                plant(Entities.Pumpkin)

                to_water = should_water(Entities.Pumpkin)
                if to_water:
                    water_tile(to_water)

    # Steg 2: Vänta och optimera kluster
    # Vi loopar över fältet och skördar bara de pumpor som är "små"
    # (de som inte blev mega-pumpor) för att ge dem en ny chans.
    while True:
        all_mega = True
        for x in range(size):
            for y in range(size):
                move_to(x, y)
                # Om pumpan är fullvuxen men fortfarande liten:
                if can_harvest():
                    if measure() == -1: # Del av mega-kluster
                        continue
                    else:
                        # Skörda den lilla och plantera om
                        harvest()

                        ensure_pumpkin_seeds() # Kolla frön igen
                        plant(Entities.Pumpkin)

                        to_water = should_water(Entities.Pumpkin)
                        if to_water:
                            water_tile(to_water)
                        all_mega = False

        # Om vi har täckt hela fältet och allt är Mega eller vi är nöjda:
        if all_mega:
            break

    # Steg 3: MEGA-SKÖRD
    move_to(0, 0)
    harvest()

def run_cactus_cycle():
    size = get_world_size()

    # Steg 1: Se till att hela fältet är fyllt med kaktusar
    for x in range(size):
        for y in range(size):
            move_to(x, y)
            if get_entity_type() != Entities.Cactus:
                if can_harvest():
                    harvest()
                prepare_ground(Grounds.Soil)
                plant(Entities.Cactus)

    # 2. Sortera MEDAN de växer (Smart! Sparar tid)
    # Man kan faktiskt sortera kaktusar även om de inte är fullvuxna
    for _ in range(3):
        diagonal_cactus_pass()
    optimize_cactus_field()

    # 3. Vänta på att de växer klart
    move_to(size - 1, size - 1)
    while not can_harvest():
        move_to(size - 1, size - 1)

    # 4. Dubbelkoll: Sortera en sista gång snabbt utifall att
    optimize_cactus_field()

    # Steg 5: MEGA-SKÖRD (n^2 belöning)
    move_to(0, 0)
    if harvest(): # Startar kedjereaktionen
        quick_print("Kaktus-vinst inkasserad!")

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
    move_to(get_world_size()-1, get_world_size()-1)
    val_max = measure()
    return val_min <= val_max

def snake_harvest():
    size = get_world_size()
    x_pos, y_pos = get_pos_x(), get_pos_y()

    max_petals = -1
    sun_points = []

    # 1. SCANNING & UNDERHÅLL
    for x in my_range(size, x_pos):
        y = 0
        for y in my_range(size, y_pos):
            move_to(x, y)
            entity = get_entity_type()

            # Mät solrosor för senare skörd
            if entity == Entities.Sunflower:
                p = measure()
                if p > max_petals:
                    max_petals = p
                    sun_points = [(x, y)]
                elif p == max_petals and p != -1:
                    sun_points.append((x, y))

            # Skörda, plantera och vattna rutan
            manage_tile(entity, x, y)
        y_pos = y

    # 2. SELEKTIV SOLROSSKÖRD
    if len(sun_points) > 0:
        cx, cy = get_pos_x(), get_pos_y()
        sun_points = sort_by_distance(sun_points, cx, cy)

        for point in sun_points:
            move_to(point[0], point[1])
            if can_harvest():
                harvest()

# ==========================================
# LOGIK OCH EKONOMI
# ==========================================

def manage_tile(entity, x, y):
    # Om det är en kaktus, skörda den INTE automatiskt
    if entity == Entities.Cactus:
        return # Avbryt, låt specialfunktionen sköta skörden senare
    should_plant = False

    if entity == None:
        should_plant = True
    elif entity != Entities.Sunflower and can_harvest():
        should_plant = harvest()
        if should_plant:
            entity = None

    if should_plant:
        target_crop = get_best_crop()
        if target_crop == Entities.Sunflower:
            entity = Entities.Sunflower if plant(Entities.Sunflower) else entity
        elif target_crop == Entities.Carrots:
            prepare_ground(Grounds.Soil)
            entity = Entities.Carrots if plant(Entities.Carrots) else entity
        elif target_crop == Entities.Bush:
            if (x + y) & 1 == 0:
                entity = Entities.Tree if plant(Entities.Tree) else entity
            else:
                entity = Entities.Bush if plant(Entities.Bush) else entity
        elif target_crop == Entities.Grass:
            prepare_ground(Grounds.Turf)
            entity = Entities.Grass

    # Vatten-hantering (Nu med get_water() och 0.75 tröskel)
    to_water = should_water(entity)
    if to_water:
        water_tile(to_water)

def get_best_crop():
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
    req = total_tiles * 4
    hay, wood = num_items(Items.Hay), num_items(Items.Wood)

    if hay >= req and wood >= req:
        return Entities.Carrots
    return Entities.Grass if hay < wood else Entities.Bush

# ==========================================
# SÄKRA RÖRELSEFUNKTIONER (Anti-Freeze)
# ==========================================

def move_to(target_x, target_y):
    # Flytta i X-led
    attempts = 0
    while get_pos_x() != target_x and attempts < 100:
        cur_x = get_pos_x()
        move(East if cur_x < target_x else West)
        if get_pos_x() == cur_x:
            attempts += 1
            safe_harvest_check()
        else: attempts = 0
    # Flytta i Y-led
    attempts = 0
    while get_pos_y() != target_y and attempts < 100:
        cur_y = get_pos_y()
        move(North if cur_y < target_y else South)
        if get_pos_y() == cur_y:
            attempts += 1
            safe_harvest_check()
        else: attempts = 0

def move_northeast():
    size = get_world_size()
    tx, ty = (get_pos_x() + 1) % size, (get_pos_y() + 1) % size
    m_e, m_n, attempts = False, False, 0
    while (not m_e or not m_n) and attempts < 100:
        if not m_n:
            m_n = True if move(North) else get_pos_y() == ty
            attempts = 0 if m_n else attempts + 1
            if not m_n: safe_harvest_check()
        if not m_e:
            m_e = True if move(East) else get_pos_x() == tx
            attempts = 0 if m_e else attempts + 1
            if not m_e: safe_harvest_check()
    return attempts < 100

def move_northwest():
    size = get_world_size()
    tx, ty = (get_pos_x() - 1) % size, (get_pos_y() + 1) % size
    m_w, m_n, attempts = False, False, 0
    while (not m_w or not m_n) and attempts < 100:
        if not m_n:
            m_n = True if move(North) else get_pos_y() == ty
            attempts = 0 if m_n else attempts + 1
            if not m_n: safe_harvest_check()
        if not m_w:
            m_w = True if move(West) else get_pos_x() == tx
            attempts = 0 if m_w else attempts + 1
            if not m_w: safe_harvest_check()
    return attempts < 100

def move_southeast():
    size = get_world_size()
    tx, ty = (get_pos_x() + 1) % size, (get_pos_y() - 1) % size
    m_e, m_s, attempts = False, False, 0
    while (not m_e or not m_s) and attempts < 100:
        if not m_s:
            m_s = True if move(South) else get_pos_y() == ty
            attempts = 0 if m_s else attempts + 1
            if not m_s: safe_harvest_check()
        if not m_e:
            m_e = True if move(East) else get_pos_x() == tx
            attempts = 0 if m_e else attempts + 1
            if not m_e: safe_harvest_check()
    return attempts < 100

def move_southwest():
    size = get_world_size()
    tx, ty = (get_pos_x() - 1) % size, (get_pos_y() - 1) % size
    m_w, m_s, attempts = False, False, 0
    while (not m_w or not m_s) and attempts < 100:
        if not m_s:
            m_s = True if move(South) else get_pos_y() == ty
            attempts = 0 if m_s else attempts + 1
            if not m_s: safe_harvest_check()
        if not m_w:
            m_w = True if move(West) else get_pos_x() == tx
            attempts = 0 if m_w else attempts + 1
            if not m_w: safe_harvest_check()
    return attempts < 100

# ==========================================
# HJÄLPFUNKTIONER
# ==========================================

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
                if x % 2 == 0:
                    move(North) if y < size - 1 else move(East)
                else:
                    move(South) if y > 0 else move(East)

        # Om vi inte gjorde några byten på hela fältet är det perfekt sorterat!
        if not swapped:
            break

def safe_harvest_check():
    # Om det är en kaktus, skörda ALDRIG för att lösa ett hinder
    # Vi vill hellre vänta eller försöka igen än att förstöra n^2
    if get_entity_type() == Entities.Cactus:
        return False

    # För alla andra grödor (gräs, morötter, solrosor) är det okej
    if can_harvest():
        return harvest()
    return False

def water_tile(amount):
    water_count = num_items(Items.Water)
    if (water_count < 10) and (num_items(Items.Empty_Tank) < 10):
        trade(Items.Empty_Tank, 100) # Eller Items.Empty_Tank

    # Kolla om vi har vatten (antingen gamla eller nyköpta)
    # Använd amount stycken Items.Water
    if num_items(Items.Water) > 0:
        # Vi begränsar amount till vad vi faktiskt har i lager för att undvika False
        actual_use = min(amount, num_items(Items.Water))
        use_item(Items.Water, actual_use)
        # Loopar ifall use_item bara tar 1 tank åt gången
        #for i in range(amount):
        #    actual_use = min(amount, num_items(Items.Water))
        #    use_item(Items.Water, actual_use)

def should_water(entity):
    # Uppdaterat funktionsnamn
    water_level = get_water()
    # Om det redan är över 75% fukt, gör ingenting
    if water_level >= 0.75:
        return False
    exclusive_crops = [Entities.Carrots, Entities.Sunflower, Entities.Pumpkin]
    if entity in exclusive_crops:
        # returnera 1 till 3 tankar beroende på fuktighet
        return 3 - (water_level // 0.25)
    return False

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

def my_range(size, coordinate):
    start, stop, step = (0, size, 1) if coordinate < (size / 2) else (size - 1, -1, -1)
    return range(start, stop, step)

def prepare_ground(target):
    if get_ground_type() != target:
        till()

# ==========================================
# START
# ==========================================
while True:
    main_farm_manager()

"""
def snake_harvest2(size = 3, x_pos = 0, y_pos = 0):
    y = 0
    for x in my_range(size, x_pos):
        for y in my_range(size, y_pos):
            print("moved to (" + str(x) + "," + str(y) + ")")
            #manage_tile()
        y_pos = y
"""
