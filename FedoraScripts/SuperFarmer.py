# ==========================================
# GEMINI MASTER FARMER v3.0
# ==========================================

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
    should_plant = False

    if entity == None:
        should_plant = True
    elif entity != Entities.Sunflower and can_harvest():
        should_plant = harvest()
        entity = None if should_plant else entity

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
        water_count = num_items(Items.Water)
        if (water_count < 10) and (num_items(Items.Empty_Tank) < 10):
            trade(Items.Empty_Tank, 100) # Eller Items.Empty_Tank

        # Kolla om vi har vatten (antingen gamla eller nyköpta)
        # Använd to_water stycken Items.Water
        if num_items(Items.Water) > 0:
            # Vi begränsar to_water till vad vi faktiskt har i lager för att undvika False
            actual_use = min(to_water, num_items(Items.Water))
            use_item(Items.Water, actual_use)
            # Loopar ifall use_item bara tar 1 tank åt gången
            #for i in range(to_water):
            #    actual_use = min(to_water, num_items(Items.Water))
            #    use_item(Items.Water, actual_use)

def get_best_crop():
    # Ekonomi-check
    if num_items(Items.Gold) > 50000:
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
            if can_harvest(): harvest()
        else: attempts = 0
    # Flytta i Y-led
    attempts = 0
    while get_pos_y() != target_y and attempts < 100:
        cur_y = get_pos_y()
        move(North if cur_y < target_y else South)
        if get_pos_y() == cur_y:
            attempts += 1
            if can_harvest(): harvest()
        else: attempts = 0

def move_northeast():
    size = get_world_size()
    tx, ty = (get_pos_x() + 1) % size, (get_pos_y() + 1) % size
    m_e, m_n, attempts = False, False, 0
    while (not m_e or not m_n) and attempts < 100:
        if not m_n:
            m_n = True if move(North) else get_pos_y() == ty
            attempts = 0 if m_n else attempts + 1
            if not m_n and can_harvest(): harvest()
        if not m_e:
            m_e = True if move(East) else get_pos_x() == tx
            attempts = 0 if m_e else attempts + 1
            if not m_e and can_harvest(): harvest()
    return attempts < 100

def move_northwest():
    size = get_world_size()
    tx, ty = (get_pos_x() - 1) % size, (get_pos_y() + 1) % size
    m_w, m_n, attempts = False, False, 0
    while (not m_w or not m_n) and attempts < 100:
        if not m_n:
            m_n = True if move(North) else get_pos_y() == ty
            attempts = 0 if m_n else attempts + 1
            if not m_n and can_harvest(): harvest()
        if not m_w:
            m_w = True if move(West) else get_pos_x() == tx
            attempts = 0 if m_w else attempts + 1
            if not m_w and can_harvest(): harvest()
    return attempts < 100

def move_southeast():
    size = get_world_size()
    tx, ty = (get_pos_x() + 1) % size, (get_pos_y() - 1) % size
    m_e, m_s, attempts = False, False, 0
    while (not m_e or not m_s) and attempts < 100:
        if not m_s:
            m_s = True if move(South) else get_pos_y() == ty
            attempts = 0 if m_s else attempts + 1
            if not m_s and can_harvest(): harvest()
        if not m_e:
            m_e = True if move(East) else get_pos_x() == tx
            attempts = 0 if m_e else attempts + 1
            if not m_e and can_harvest(): harvest()
    return attempts < 100

def move_southwest():
    size = get_world_size()
    tx, ty = (get_pos_x() - 1) % size, (get_pos_y() - 1) % size
    m_w, m_s, attempts = False, False, 0
    while (not m_w or not m_s) and attempts < 100:
        if not m_s:
            m_s = True if move(South) else get_pos_y() == ty
            attempts = 0 if m_s else attempts + 1
            if not m_s and can_harvest(): harvest()
        if not m_w:
            m_w = True if move(West) else get_pos_x() == tx
            attempts = 0 if m_w else attempts + 1
            if not m_w and can_harvest(): harvest()
    return attempts < 100

# ==========================================
# HJÄLPFUNKTIONER
# ==========================================

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
    snake_harvest()

"""
def snake_harvest2(size = 3, x_pos = 0, y_pos = 0):
    y = 0
    for x in my_range(size, x_pos):
        for y in my_range(size, y_pos):
            print("moved to (" + str(x) + "," + str(y) + ")")
            #manage_tile()
        y_pos = y
"""
