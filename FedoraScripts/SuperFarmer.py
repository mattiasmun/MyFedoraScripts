def snake_harvest():
    size = get_world_size()
    x_pos, y_pos = get_pos_x(), get_pos_y()

    # Variabler för att minnas den bästa solrosen
    max_petals = -1
    best_x, best_y = 0, 0

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

            # 2. Arbets-fas: Skörda, plantera och vattna
            manage_tile(entity, x, y)
        y_pos = y

    # 3. Skörde-fas: Om vi hittade en solros, åk och hämta den bästa efter rundan!
    if max_petals != -1:
        move_to(best_x, best_y)
        if can_harvest():
            harvest()

def my_range(size, coordinate):
    # Väljer start och stopp baserat på var vi står
    start, stop, step = (0, size, 1) if coordinate < (size / 2) else (size - 1, -1, -1)
    return range(start, stop, step)

def manage_tile(entity, x, y):
    should_plant = False
    
    # Solrosor skördas separat i snake_harvest
    if entity == Entities.Sunflower:
        should_plant = False
    
    # Tom ruta behöver planteras
    elif entity == None:
        should_plant = True
    
    # Allt annat skördas om det är klart
    elif can_harvest():
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
        if water_items < 10:
            trade(Items.Water_Tank, 100)

        if water_items >= to_water:
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
        if sunflower_seed_items < 5:
            trade(Items.Sunflower_Seed, 50)
        if sunflower_seed_items > 0:
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
    water_level = get_water_level()
    if water_level >= 0.5:
        return False

    entity = get_entity_type()
    exclusive_crops = [Entities.Carrot, Entities.Sunflower, Entities.Pumpkin]

    if entity in exclusive_crops:
        return 2 if water_level < 0.25 else 1

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
