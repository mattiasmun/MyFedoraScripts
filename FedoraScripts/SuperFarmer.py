def snake_harvest():
    size = get_world_size()
    x_pos, y_pos = get_pos_x(), get_pos_y()

    # Variabler för att minnas den bästa solrosen
    max_petals = -1
    best_x, best_y = 0, 0
    sun_points = []
    y = 0
    for x in my_range(size, x_pos):
        for y in my_range(size, y_pos):
            move_to(x, y)
            entity = get_entity_type()

            # 1. Scanning-fas: Mät solrosor
            if entity == Entities.Sunflower:
                p = measure()
                if p > max_petals:
                    max_petals = p
                    best_x, best_y = x, y
                    sun_points = [(x, y)]
                elif p == max_petals and p != -1:
                    sun_points.append((x, y))

            # 2. Arbets-fas: Skörda, plantera och vattna
            manage_tile(entity, x, y)
        y_pos = y

    # 3. Skörde-fas: Sortera och hämta de bästa solrosorna
    if len(sun_points) > 0:
        cx, cy = get_pos_x(), get_pos_y()

        # Ersättare för lambda-sort:
        sun_points = sort_by_distance(sun_points, cx, cy)

        for point in sun_points:
            x, y = point
            move_to(x, y)
            if can_harvest():
                harvest()

def sort_by_distance(points, cx, cy):
    n = len(points)
    # En enkel Bubble Sort
    for i in range(n):
        for j in range(0, n - i - 1):
            # Hämta punkt A och punkt B
            p1 = points[j]
            p2 = points[j + 1]

            # Räkna ut avståndet för båda (Manhattan-distans)
            dist1 = abs(p1[0] - cx) + abs(p1[1] - cy)
            dist2 = abs(p2[0] - cx) + abs(p2[1] - cy)

            # Om punkt 1 är längre bort än punkt 2, byt plats på dem
            if dist1 > dist2:
                points[j], points[j + 1] = points[j + 1], points[j]
    return points

def my_range(size, coordinate):
    # Väljer start och stopp baserat på var vi står
    start, stop, step = (0, size, 1) if coordinate < (size / 2) else (size - 1, -1, -1)
    return range(start, stop, step)

def manage_tile(entity, x, y):
    should_plant = False

    if entity == None:
        should_plant = True
    elif entity != Entities.Sunflower and can_harvest():
        harvest()
        should_plant = True

    if should_plant:
        target_crop = get_best_crop()

        if target_crop == Entities.Sunflower:
            plant(Entities.Sunflower)
        elif target_crop == Entities.Carrot:
            prepare_ground(Grounds.Soil)
            plant(Entities.Carrots)
        elif target_crop == Entities.Bush:
            # Schackrutemönster med bitwise-logik
            if (x + y) & 1 == 0:
                plant(Entities.Tree)
            else:
                plant(Entities.Bush)
        elif target_crop == Entities.Grass:
            prepare_ground(Grounds.Turf)

    # Vatten-hantering
    to_water = should_water()
    if to_water:
        water_items = num_items(Items.Water_Tank)
        buy_success = False

        if water_items < 10:
            buy_success = trade(Items.Water_Tank, 100)

        # Kolla om vi har vatten (antingen gamla eller nyköpta)
        if water_items >= to_water or buy_success:
            # Vi gör en säkerhetscheck så vi inte använder to_water om vi bara fick 1
            use_item(Items.Water_Tank, to_water)
            # Loopar ifall use_item bara tar 1 tank åt gången
            #for i in range(to_water):
            #    use_item(Items.Water_Tank)

def get_best_crop():
    total_tiles = get_world_size() ** 2
    safe_margin = total_tiles * 2
    cost_per_carrot = 2
    required_res = safe_margin * cost_per_carrot

    # Ekonomi-check: Har vi råd med solrosor?
    gold_items = num_items(Items.Gold)
    if gold_items > 50000:
        sunflower_seed_items = num_items(Items.Sunflower_Seed)
        buy_success = False
        if sunflower_seed_items < 5:
            buy_success = trade(Items.Sunflower_Seed, 50)
        if sunflower_seed_items > 0 or buy_success:
            return Entities.Sunflower

    # Resurs-balansering
    hay_items, wood_items = num_items(Items.Hay), num_items(Items.Wood)
    if hay_items >= required_res and wood_items >= required_res:
        return Entities.Carrot

    if hay_items < wood_items:
        return Entities.Grass
    else:
        return Entities.Bush

def prepare_ground(target_type):
    if get_ground_type() != target_type:
        till()

def move_to(target_x, target_y):
    # Flytta i X-led
    x_pos = get_pos_x()
    while x_pos != target_x:
        if x_pos < target_x:
            if not move(East): continue
        else:
            if not move(West): continue
        x_pos = get_pos_x()

    # Flytta i Y-led
    y_pos = get_pos_y()
    while y_pos != target_y:
        if y_pos < target_y:
            if not move(North): continue
        else:
            if not move(South): continue
        y_pos = get_pos_y()

def should_water():
    # Uppdaterat funktionsnamn
    water_level = get_water()

    # Om det redan är över 75% fukt, gör ingenting
    if water_level >= 0.75:
        return False

    entity = get_entity_type()
    exclusive_crops = [Entities.Carrot, Entities.Sunflower, Entities.Pumpkin]

    if entity in exclusive_crops:
        # Om det är riktigt torrt, returnera 2 tankar, annars 1
        return 2 if water_level < 0.3 else 1

    return False

# STARTA PROGRAMMET
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
