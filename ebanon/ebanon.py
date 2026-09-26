"""
Ébanon // Motor de Supervivencia — Port a Python (Pygame)
==========================================================
Parche: anti-tunneling zombis + PIXEL_SCALE dinámico.
"""

import pygame
import sys
import math
import random
import json
import os

# ----------------------------------------------------------------------------
# 1. CONFIG / VENTANA / PALETA
# ----------------------------------------------------------------------------
pygame.init()
pygame.mixer.init()
pygame.display.set_caption("Ébanon // Motor de Supervivencia")

info = pygame.display.Info()
SCREEN_W, SCREEN_H = info.current_w, info.current_h
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
clock = pygame.time.Clock()

# ── Escala dinámica ──────────────────────────────────────────────────────
BASE_TILE = 16
MIN_SCALE = 2
MAX_SCALE = 4
# Queremos que quepan ~30 tiles en el eje más corto
target_tiles = 30
scale = max(MIN_SCALE, min(MAX_SCALE, min(SCREEN_W, SCREEN_H) // (BASE_TILE * target_tiles)))
PIXEL_SCALE = scale
TILE = BASE_TILE
# ── Escalado UI ──────────────────────────────────────────────────────────
UI_S = max(1, PIXEL_SCALE // 2)   # ← AÑADE ESTA LÍNEA

TEXT_SCALE = max(1, min(3, PIXEL_SCALE))   # limita entre 1 y 3

# Fuentes escaladas
FONT_SMALL = pygame.font.SysFont("consolas", 8 * TEXT_SCALE)
FONT_MED   = pygame.font.SysFont("consolas", 12 * TEXT_SCALE, bold=True)
FONT_TITLE = pygame.font.SysFont("consolas", 18 * TEXT_SCALE, bold=True)

STAMINA_RECOVER_MIN = 55
WORLD_W, WORLD_H = 90, 90
WORLD_SEED_X = random.uniform(0, 100000)
WORLD_SEED_Y = random.uniform(0, 100000)
DAY_LENGTH = 240
AMMO_RESPAWN_TIME = 45
AMMO_PER_PICKUP = 6
INTERACT_RANGE = 24 * scale
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ebano_save.json")

RESPAWN_WOOD = 90
RESPAWN_ROCK = 240
RESPAWN_SCRAP = 240
RESPAWN_FOOD = 150
RESPAWN_AMMO = 250

INITIAL_WOOD = 10
INITIAL_ROCK = 4
INITIAL_SCRAP = 3
INITIAL_FOOD = 6
INITIAL_AMMO = 3

PALETTE = {
    "grass1": (58, 74, 36), "grass2": (50, 64, 32),
    "dirt1": (74, 58, 38), "dirt2": (64, 49, 31),
    "road1": (44, 44, 40), "road2": (36, 36, 32),
    "water1": (38, 69, 82), "water2": (29, 56, 68),
    "ruin1": (51, 52, 46), "ruin2": (38, 39, 31),
    "tree_trunk": (58, 42, 28), "tree_leaf": (45, 74, 31), "tree_leaf_dark": (32, 53, 15),
    "rock": (85, 85, 79), "rock_dark": (61, 61, 56),
    "scrap_pile": (122, 106, 58), "scrap_pile_dark": (92, 79, 40),
    "player_body": (201, 161, 90), "player_body_dark": (138, 106, 56), "player_head": (217, 193, 154),
    "zombie_body": (92, 106, 58), "zombie_body_dark": (58, 67, 36), "zombie_head": (122, 138, 82),
    "wall": (107, 90, 61), "wall_dark": (74, 61, 41),
    "fire1": (232, 134, 42), "fire2": (201, 67, 42),
    "chest": (138, 106, 56), "chest_dark": (92, 69, 34),
    "gun_metal": (139, 141, 134), "gun_dark": (79, 80, 73), "gun_grip": (92, 69, 34),
    "bullet": (244, 224, 74),
    "crate": (122, 90, 52), "crate_dark": (74, 56, 32), "crate_mark": (201, 67, 42),
    "herb_leaf": (90, 154, 74), "herb_flower": (232, 224, 200),
    "door_plank": (107, 74, 47), "door_dark": (74, 50, 32), "door_open_frame": (138, 106, 69),
}

BUILD_COSTS = {
    "wall": {"wood": 3, "scrap": 0, "stone": 0},
    "fire": {"wood": 1, "scrap": 0, "stone": 0},
    "chest": {"wood": 6, "scrap": 2, "stone": 0},
    "wallStone": {"wood": 0, "scrap": 0, "stone": 2},
    "door": {"wood": 3, "scrap": 1, "stone": 0},
}
BUILD_NAMES = {
    "wall": "Muro construido.", "fire": "Fogata encendida.", "chest": "Almacén instalado.",
    "wallStone": "Muro de piedra construido.", "door": "Puerta instalada.",
}
BUILD_LABELS = {
    "wall": "1) Muro  (Madera 3)",
    "fire": "2) Fogata  (Madera 1)",
    "chest": "3) Almacén  (Madera 6, Chatarra 2)",
    "wallStone": "4) Muro de piedra  (Piedra 2)",
    "door": "5) Puerta  (Madera 3, Chatarra 1)",
}
BUILD_KEYS = {
    pygame.K_1: "wall", pygame.K_2: "fire", pygame.K_3: "chest",
    pygame.K_4: "wallStone", pygame.K_5: "door",
}

# Sonidos con fallback silencioso
def _load_sound(path, vol):
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(vol)
        return s
    except Exception:
        silent = pygame.mixer.Sound(buffer=bytearray(44))  # 1 frame silencio
        silent.set_volume(0)
        return silent

step_sound_walk = _load_sound("footsteps_walk.ogg", 0.4)
step_sound_run  = _load_sound("footsteps_run.ogg",  0.4)
gunshot_sound   = _load_sound("gunshot.ogg", 0.6)
hit_sound       = _load_sound("blood_hit.ogg", 0.6)

STATE_START = "start"
STATE_PLAYING = "playing"
STATE_GAMEOVER = "gameover"

# ----------------------------------------------------------------------------
# 2. RUIDO / GENERACIÓN DE MUNDO
# ----------------------------------------------------------------------------
def hash_noise(x, y):
    n = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return n - math.floor(n)

def smooth_noise(x, y):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    v00 = hash_noise(xi, yi)
    v10 = hash_noise(xi + 1, yi)
    v01 = hash_noise(xi, yi + 1)
    v11 = hash_noise(xi + 1, yi + 1)
    i1 = v00 + (v10 - v00) * xf
    i2 = v01 + (v11 - v01) * xf
    return i1 + (i2 - i1) * yf

def gen_world():
    w = []
    for y in range(WORLD_H):
        row = []
        for x in range(WORLD_W):
            n  = smooth_noise(x * 0.12 + WORLD_SEED_X, y * 0.12 + WORLD_SEED_Y)
            n2 = smooth_noise(x * 0.05 + 50 + WORLD_SEED_X, y * 0.05 + 50 + WORLD_SEED_Y)
            if n < 0.18:
                t = 3
            elif n2 > 0.72:
                t = 4
            elif n > 0.62:
                t = 1
            else:
                t = 0
            if y % 14 == 0 or x % 18 == 0:
                t = 2
            row.append(t)
        w.append(row)
    return w

WORLD = gen_world()

def tile_at(tx, ty):
    if tx < 0 or ty < 0 or tx >= WORLD_W or ty >= WORLD_H:
        return 3
    return WORLD[ty][tx]

def tile_solid(tx, ty):
    return tile_at(tx, ty) == 4   # ajusta según el valor que uses para roca/ruina

def tile_water(tx, ty):
    return tile_at(tx, ty) == 3   # agua

# def tile_solid(tx, ty):
#    return tile_at(tx, ty) == 3

def dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)

# ----------------------------------------------------------------------------
# 3. ENTIDADES
# ----------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.x = WORLD_W * TILE / 2
        self.y = WORLD_H * TILE / 2
        self.hp = self.max_hp = 100
        self.stamina = self.max_stamina = 100
        self.hunger = self.max_hunger = 100
        self.speed = 52
        self.sprint_mult = 1.6
        self.attack_cooldown = 0.0
        self.inv_wood = 4
        self.inv_scrap = 2
        self.inv_food = 0
        self.inv_stone = 0
        self.bandages = 0
        self.has_gun = False
        self.ammo = 0
        self.has_axe = False
        self.has_pickaxe = False
        self.has_bat = False
        self.equipped = "fist"
        self.aim_x, self.aim_y = 1.0, 0.0
        self.facing = 1
        self.action_anim = None
        self.anim_t = 0.0
        self.hunger_warned = False
        self.hunger_low_warned = False
        self.exhausted = False
        self.vx = self.vy = 0.0

class Zombie:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.hp = self.max_hp = 75
        self.speed = speed
        self.wander_t = 0.0
        self.wander_dir = (0.0, 0.0)
        self.alert_t = 0.0
        self.aggro = False
        self.alert_cd = 0.0
        self.hit_flash = 0.0
        self.biting = False
        self.facing = 1
        self.anim_t = 0.0
        self.vx = self.vy = 0.0
        self.dead = False

# ----------------------------------------------------------------------------
# 4. ESTADO GLOBAL
# ----------------------------------------------------------------------------
player = Player()
zombies = []
structures = []
bullets = []

wood_pickups = []
rock_pickups = []
scrap_pickups = []
food_pickups = []
ammo_pickups = []
gun_pickup = None

day_count = 1
world_time = 0.48
hunger_timer = 0.0
zombie_spawn_timer = 0.0
camera_x = camera_y = 0.0
log_lines = []

build_menu_open = False
inventory_open = False
active_chest = None

game_state = STATE_START
survived_days = 0
autosave_acc = 0.0

STORE_BAG_MAP = {"wood": "inv_wood", "scrap": "inv_scrap", "stone": "inv_stone",
                  "food": "inv_food", "bandages": "bandages"}

WEAPON_LABELS = {"fist": "PUÑOS", "axe": "HACHA", "pickaxe": "PICO", "bat": "BATE", "gun": "PISTOLA"}
MELEE_DAMAGE = {"fist": 18, "axe": 25, "bat": 40}

def log(msg):
    log_lines.append(msg)
    if len(log_lines) > 5:
        log_lines.pop(0)

# ----------------------------------------------------------------------------
# 5. SPAWNEO
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# 5. SPAWNEO
# ----------------------------------------------------------------------------
def spawn_resources():
    wood_pickups.clear()
    for _ in range(INITIAL_WOOD):
        valid = False
        for tries in range(50):
            tx = random.randint(0, WORLD_W - 1)
            ty = random.randint(0, WORLD_H - 1)
            if not tile_solid(tx, ty) and not tile_water(tx, ty):
                valid = True
                break
        if valid:
            wood_pickups.append({"x": tx * TILE + 8, "y": ty * TILE + 8,
                                 "active": True, "timer": 0.0, "type": "tree"})

    rock_pickups.clear()
    for _ in range(INITIAL_ROCK):
        valid = False
        for tries in range(50):
            rx = random.randint(0, WORLD_W - 1)
            ry = random.randint(0, WORLD_H - 1)
            if not tile_solid(rx, ry) and not tile_water(rx, ry):
                valid = True
                break
        if valid:
            rock_pickups.append({"x": rx * TILE + 8, "y": ry * TILE + 8,
                                 "active": True, "timer": 0.0, "type": "rock"})

    scrap_pickups.clear()
    for _ in range(INITIAL_SCRAP):
        valid = False
        for tries in range(50):
            sx = random.randint(0, WORLD_W - 1)
            sy = random.randint(0, WORLD_H - 1)
            if not tile_solid(sx, sy) and not tile_water(sx, sy):
                valid = True
                break
        if valid:
            scrap_pickups.append({"x": sx * TILE + 8, "y": sy * TILE + 8,
                                  "active": True, "timer": 0.0, "type": "scrap"})

    food_pickups.clear()
    for _ in range(INITIAL_FOOD):
        valid = False
        for tries in range(50):
            fx = random.randint(0, WORLD_W - 1)
            fy = random.randint(0, WORLD_H - 1)
            if not tile_solid(fx, fy) and not tile_water(fx, fy):
                valid = True
                break
        if valid:
            food_pickups.append({"x": fx * TILE + 8, "y": fy * TILE + 8,
                                 "active": True, "timer": 0.0,
                                 "type": "berry" if random.random() < 0.7 else "herb"})


def spawn_gun_and_ammo():
    global gun_pickup
    valid = False
    for tries in range(50):
        tx = random.randint(0, WORLD_W - 1)
        ty = random.randint(0, WORLD_H - 1)
        if not tile_solid(tx, ty) and not tile_water(tx, ty):
            valid = True
            break
    if valid:
        gun_pickup = {"x": tx * TILE + 8, "y": ty * TILE + 8, "taken": False}

    ammo_pickups.clear()
    for _ in range(INITIAL_AMMO):
        valid = False
        for tries2 in range(50):
            ax = random.randint(0, WORLD_W - 1)
            ay = random.randint(0, WORLD_H - 1)
            if not tile_solid(ax, ay) and not tile_water(ax, ay):
                valid = True
                break
        if valid:
            ammo_pickups.append({"x": ax * TILE + 8, "y": ay * TILE + 8,
                                 "active": True, "timer": 0.0})


def spawn_zombie(near_night):
    valid = False
    for tries in range(50):
        tx = random.randint(0, WORLD_W - 1)
        ty = random.randint(0, WORLD_H - 1)
        if not tile_solid(tx, ty) and dist(tx * TILE, ty * TILE, player.x, player.y) >= 6 * TILE:
            valid = True
            break
    if valid:
        zombies.append(Zombie(tx * TILE + 8, ty * TILE + 8,
                              55 if near_night else 30))

# ----------------------------------------------------------------------------
# 6. CICLO DÍA / NOCHE
# ----------------------------------------------------------------------------
def is_night():
    return world_time < 0.22 or world_time > 0.78

def update_day_night(dt):
    global world_time, day_count
    world_time += dt / DAY_LENGTH
    if world_time >= 1:
        world_time -= 1
        day_count += 1
        log(f"Amanece. Día {day_count}.")

def night_darkness():
    t = world_time
    if t < 0.22:
        return 1 - (t / 0.22)
    if t < 0.30:
        return (t - 0.22) / 0.08
    if t < 0.70:
        return 0
    if t < 0.78:
        return (t - 0.70) / 0.08
    return 1

# ----------------------------------------------------------------------------
# 7. COLISIÓN
# ----------------------------------------------------------------------------
def wall_at(tx, ty):
    for st in structures:
        if st["type"] in ("wall", "wallStone"):
            if int(st["x"] // TILE) == tx and int(st["y"] // TILE) == ty:
                return True
    return False

def door_at(tx, ty):
    for st in structures:
        if st["type"] == "door" and int(st["x"] // TILE) == tx and int(st["y"] // TILE) == ty:
            return st
    return None

def blocked(tx, ty, is_zombie):
    # Bloquea solo roca/ruina y muros
    if tile_solid(tx, ty) or wall_at(tx, ty):
        return True
    # Agua no bloquea, se maneja con reducción de velocidad
    if tile_water(tx, ty):
        return False
    d = door_at(tx, ty)
    if d:
        return True if is_zombie else (not d["open"])
    return False


def cardinal_from_aim():
    ax, ay = player.aim_x, player.aim_y
    if abs(ax) >= abs(ay):
        return (1 if ax >= 0 else -1), 0
    return 0, (1 if ay >= 0 else -1)

# ----------------------------------------------------------------------------
# 8. CONSTRUCCIÓN
# ----------------------------------------------------------------------------
def can_afford(t):
    c = BUILD_COSTS[t]
    return player.inv_wood >= c["wood"] and player.inv_scrap >= c["scrap"] and player.inv_stone >= c["stone"]

def build_structure(t):
    global build_menu_open
    if not can_afford(t):
        log("No tienes suficientes materiales.")
        return
    c = BUILD_COSTS[t]
    dirx, diry = cardinal_from_aim()
    tx = round((player.x + dirx * TILE) / TILE) * TILE + TILE / 2
    ty = round((player.y + diry * TILE) / TILE) * TILE + TILE / 2
    for s in structures:
        if int(s["x"] // TILE) == int(tx // TILE) and int(s["y"] // TILE) == int(ty // TILE):
            log("Ya hay algo construido ahí.")
            return
    player.inv_wood -= c["wood"]
    player.inv_scrap -= c["scrap"]
    player.inv_stone -= c["stone"]
    st = {"x": tx, "y": ty, "type": t}
    if t == "chest":
        st["store"] = {"wood": 0, "scrap": 0, "stone": 0, "food": 0, "bandages": 0}
    if t == "door":
        st["open"] = False
    structures.append(st)
    log(BUILD_NAMES[t])
    build_menu_open = False

# ----------------------------------------------------------------------------
# 9. COMBATE
# ----------------------------------------------------------------------------
def melee_attack():
    if player.attack_cooldown > 0:
        return
    player.attack_cooldown = 0.35
    rng = 20
    dirx, diry = cardinal_from_aim()
    ax, ay = player.x + dirx * 10, player.y + diry * 10
    dmg = MELEE_DAMAGE.get(player.equipped, MELEE_DAMAGE["fist"])
    for z in zombies:
        if z.dead:
            continue
        if dist(ax, ay, z.x, z.y) < rng:
            z.hp -= dmg
            z.hit_flash = 0.15
            if z.hp <= 0:
                z.dead = True
                log("Zombi eliminado.")
            if player.equipped in ("axe", "bat"):
                pygame.mixer.Channel(3).play(hit_sound)
    player.action_anim = {"type": "melee", "t": 0.18, "total": 0.18, "dx": dirx, "dy": diry}

def fire_gun():
    if player.attack_cooldown > 0:
        return
    if player.ammo <= 0:
        log("Sin balas.")
        return
    player.attack_cooldown = 0.22
    player.ammo -= 1
    pygame.mixer.Channel(2).play(gunshot_sound)
    bullets.append({
        "x": player.x, "y": player.y,
        "vx": player.aim_x * 180, "vy": player.aim_y * 180,
        "life": 0.25, "dmg": 13
    })
    dirx, diry = cardinal_from_aim()
    player.action_anim = {"type": "gun", "t": 0.12, "total": 0.12, "dx": dirx, "dy": diry}

def attempt_attack():
    if player.equipped == "gun":
        fire_gun()
    else:
        melee_attack()

# ----------------------------------------------------------------------------
# 9b. EQUIPAMIENTO
# ----------------------------------------------------------------------------
def available_weapons():
    w = ["fist"]
    if player.has_axe: w.append("axe")
    if player.has_pickaxe: w.append("pickaxe")
    if player.has_bat: w.append("bat")
    if player.has_gun: w.append("gun")
    return w

def cycle_weapon():
    avail = available_weapons()
    if player.equipped not in avail:
        player.equipped = "fist"
        return
    i = avail.index(player.equipped)
    player.equipped = avail[(i + 1) % len(avail)]
    log(f"Equipaste: {WEAPON_LABELS[player.equipped]}")

def toggle_equip(name):
    owned = {"axe": player.has_axe, "pickaxe": player.has_pickaxe, "bat": player.has_bat, "gun": player.has_gun, "fist": True}
    if not owned.get(name):
        return
    if player.equipped == name:
        player.equipped = "fist"
        log("Guardaste el arma (puños).")
    else:
        player.equipped = name
        log(f"Equipaste: {WEAPON_LABELS[name]}")

# ----------------------------------------------------------------------------
# 10. INTERACCIÓN
# ----------------------------------------------------------------------------
def interact():
    if gun_pickup and not gun_pickup["taken"] and dist(player.x, player.y, gun_pickup["x"], gun_pickup["y"]) < INTERACT_RANGE:
        gun_pickup["taken"] = True
        player.has_gun = True
        log("Recogiste una pistola.")
        return

    for a in ammo_pickups:
        if a["active"] and dist(player.x, player.y, a["x"], a["y"]) < INTERACT_RANGE:
            a["active"] = False
            a["timer"] = RESPAWN_AMMO
            player.ammo += AMMO_PER_PICKUP
            log(f"+{AMMO_PER_PICKUP} balas.")
            return

    for st in structures:
        if st["type"] == "chest" and dist(player.x, player.y, st["x"], st["y"]) < INTERACT_RANGE:
            open_storage(st)
            return
        if st["type"] == "door" and dist(player.x, player.y, st["x"], st["y"]) < INTERACT_RANGE:
            st["open"] = not st["open"]
            log("Abriste la puerta." if st["open"] else "Cerraste la puerta.")
            return

    for w in wood_pickups:
        if w["active"] and dist(player.x, player.y, w["x"], w["y"]) < INTERACT_RANGE:
            if player.equipped == "axe":
                w.setdefault("hits", 0)
                w["hits"] += 1
                log(f"Golpeas con el hacha ({w['hits']}/9).")
                if w["hits"] >= 7:
                    w["active"] = False
                    w["timer"] = 0.0
                    player.inv_wood += 3
                    w["hits"] = 0
                    log("¡Talado con hacha! +3 madera.")
            else:
                w.setdefault("hits", 0)
                w["hits"] += 1
                log(f"Golpeas el árbol ({w['hits']}/8).")
                if w["hits"] >= 9:
                    w["active"] = False
                    w["timer"] = RESPAWN_WOOD
                    player.inv_wood += 1
                    w["hits"] = 0
                    log("+1 madera recolectada.")
            return

    for r in rock_pickups:
        if r["active"] and dist(player.x, player.y, r["x"], r["y"]) < INTERACT_RANGE:
            if player.equipped == "pickaxe":
                r.setdefault("hits", 0)
                r["hits"] += 1
                log(f"Golpeas con el pico ({r['hits']}/9).")
                if r["hits"] >= 5:
                    r["active"] = False
                    r["timer"] = 0.0
                    player.inv_stone += 4
                    r["hits"] = 0
                    log("¡Bravo, minero! +3 roca.")
            else:
                log("Necesitas un pico para romper roca.")
            return

    for s in scrap_pickups:
        if s["active"] and dist(player.x, player.y, s["x"], s["y"]) < INTERACT_RANGE:
            s.setdefault("hits", 0)
            s["hits"] += 1
            log(f"Revisas caja de chatarra ({s['hits']}/2).")
            if s["hits"] >= 2:
                s["active"] = False
                s["timer"] = RESPAWN_SCRAP
                player.inv_scrap += 2
                s["hits"] = 0
                log("+2 chatarra recolectada.")
            return

    for f in food_pickups:
        if f["active"] and dist(player.x, player.y, f["x"], f["y"]) < INTERACT_RANGE:
            f["active"] = False
            f["timer"] = RESPAWN_FOOD
            if f["type"] == "berry":
                player.inv_food += 1
                log("+1 comida recolectada.")
            else:
                player.bandages += 1
                log("+1 venda recolectada.")
            return

# ----------------------------------------------------------------------------
# 11. ALMACÉN
# ----------------------------------------------------------------------------
def open_storage(st):
    global active_chest, inventory_open
    if "store" not in st:
        st["store"] = {"wood": 0, "scrap": 0, "stone": 0, "food": 0, "bandages": 0}
    active_chest = st
    inventory_open = False

def close_storage():
    global active_chest
    active_chest = None

def move_to_chest(key):
    bag_attr = STORE_BAG_MAP[key]
    if getattr(player, bag_attr) > 0:
        setattr(player, bag_attr, getattr(player, bag_attr) - 1)
        active_chest["store"][key] += 1

def move_to_bag(key):
    bag_attr = STORE_BAG_MAP[key]
    if active_chest["store"][key] > 0:
        active_chest["store"][key] -= 1
        setattr(player, bag_attr, getattr(player, bag_attr) + 1)

# ----------------------------------------------------------------------------
# 12. CONSUMIBLES Y CRAFTEO
# ----------------------------------------------------------------------------
def use_food():
    if player.inv_food <= 0 or player.hunger >= player.max_hunger:
        return
    player.inv_food -= 1
    player.hunger = min(player.max_hunger, player.hunger + 25)
    log("Comiste algo.")

def use_bandage():
    if player.bandages <= 0 or player.hp >= player.max_hp:
        return
    player.bandages -= 1
    player.hp = min(player.max_hp, player.hp + 30)
    log("Te vendaste las heridas.")

def craft_axe():
    if player.has_axe or player.inv_wood < 3 or player.inv_scrap < 2:
        return
    player.inv_wood -= 3
    player.inv_scrap -= 2
    player.has_axe = True
    log("Crafteaste un hacha.")

def craft_pickaxe():
    if player.has_pickaxe or player.inv_wood < 4 or player.inv_scrap < 5:
        return
    player.inv_wood -= 4
    player.inv_scrap -= 5
    player.has_pickaxe = True
    log("Crafteaste un pico.")

def craft_bat():
    if player.has_bat or player.inv_wood < 4 or player.inv_scrap < 4:
        return
    player.inv_wood -= 4
    player.inv_scrap -= 4
    player.has_bat = True
    log("Crafteaste un bate con tornillos.")

# ----------------------------------------------------------------------------
# 13. ACTUALIZACIÓN
# ----------------------------------------------------------------------------
def read_keyboard_move(keys):
    x = y = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:  x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]: x += 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:    y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:  y += 1
    return x, y

def update_aim_from_mouse():
    mx_screen, my_screen = pygame.mouse.get_pos()
    dx = mx_screen - SCREEN_W / 2
    dy = my_screen - SCREEN_H / 2
    length = math.hypot(dx, dy)
    if length > 2:
        player.aim_x = dx / length
        player.aim_y = dy / length
        player.facing = 1 if dx >= 0 else -1

def update_player(dt, keys, attack_pressed, interact_pressed):
    global hunger_timer
    mx, my = read_keyboard_move(keys)
    length = math.hypot(mx, my)
    if length > 1:
        mx /= length
        my /= length

    if player.stamina <= 0:
        player.exhausted = True
    elif player.stamina >= STAMINA_RECOVER_MIN:
        player.exhausted = False

    sprinting = keys[pygame.K_LSHIFT] and not player.exhausted and length > 0
    spd = player.speed * (player.sprint_mult if sprinting else 1)

    # 👇 Aquí metes la reducción de velocidad en agua
    if tile_water(int(player.x // TILE), int(player.y // TILE)):
        spd *= 0.4   # jugador se ralentiza en agua

    nx = player.x + mx * spd * dt
    ny = player.y + my * spd * dt
    if not blocked(int(nx // TILE), int(player.y // TILE), False):
        player.x = nx
    if not blocked(int(player.x // TILE), int(ny // TILE), False):
        player.y = ny
    player.x = max(TILE, min(WORLD_W * TILE - TILE, player.x))
    player.y = max(TILE, min(WORLD_H * TILE - TILE, player.y))

    player.vx, player.vy = mx * spd, my * spd
    if length > 0:
        player.anim_t += dt

    # Sonido pasos
    if length > 0:
        if sprinting and not player.exhausted:
            if not pygame.mixer.Channel(1).get_busy() or pygame.mixer.Channel(1).get_sound() != step_sound_run:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(1).play(step_sound_run, loops=-1)
                pygame.mixer.Channel(1).set_volume(0.4)
        elif player.exhausted:
            if not pygame.mixer.Channel(1).get_busy() or pygame.mixer.Channel(1).get_sound() != step_sound_walk:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(1).play(step_sound_walk, loops=-1)
                pygame.mixer.Channel(1).set_volume(0.3)
        else:
            if not pygame.mixer.Channel(1).get_busy() or pygame.mixer.Channel(1).get_sound() != step_sound_walk:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(1).play(step_sound_walk, loops=-1)
                pygame.mixer.Channel(1).set_volume(0.4)
    else:
        pygame.mixer.Channel(1).stop()

    if interact_pressed:
        interact()

    if sprinting and not player.exhausted:
        player.stamina = max(0, player.stamina - dt * 22)
    else:
        player.stamina = min(player.max_stamina, player.stamina + dt * 14)

    if player.attack_cooldown > 0:
        player.attack_cooldown -= dt
    if player.action_anim and player.action_anim["t"] > 0:
        player.action_anim["t"] -= dt
    if attack_pressed:
        attempt_attack()

    hunger_timer += dt
    if hunger_timer > 6:
        hunger_timer = 0
        if player.inv_food > 0 and player.hunger < 60:
            player.inv_food -= 1
            player.hunger = min(player.max_hunger, player.hunger + 18)
        else:
            player.hunger = max(0, player.hunger - 3)

        if player.hunger <= 0:
            player.hp = max(0, player.hp - 2)
            if not player.hunger_warned:
                player.hunger_warned = True
                log("Te mueres de hambre: busca comida ya.")
        else:
            if player.hunger < 30 and not player.hunger_low_warned:
                player.hunger_low_warned = True
                log("Tienes hambre.")
            if player.hunger >= 30:
                player.hunger_low_warned = False
            if player.hunger > 0:
                player.hunger_warned = False
            if player.hunger > 70 and player.hp < player.max_hp:
                player.hp = min(player.max_hp, player.hp + 1)

    if player.hp <= 0:
        game_over()

# ── 6. ANTI-TUNNELING ZOMBIS ─────────────────────────────────────────────
def _zombie_can_move(z, nx, ny):
    """True si el tile destino (nx,ny) no está bloqueado para zombis."""
    tx, ty = int(nx // TILE), int(ny // TILE)
    return not blocked(tx, ty, True)

def update_zombies(dt):
    global zombie_spawn_timer
    night = is_night()
    for z in zombies:
        if z.dead:
            continue

def update_zombies(dt):
    global zombie_spawn_timer
    night = is_night()
    for z in zombies:
        if z.dead:
            continue

        # Penalización si el zombi está en agua
        base_speed = z.speed
        if tile_water(int(z.x // TILE), int(z.y // TILE)):
            base_speed *= 0.3        # se mueve mucho más lento
            z.hp -= dt * 10          # pierde vida por ahogarse
            if z.hp <= 0:
                z.dead = True
                log("Un zombi se ahogó.")
                continue

        if z.alert_cd > 0:
            z.alert_cd -= dt
        if z.alert_t > 0:
            z.alert_t -= dt
        if z.hit_flash > 0:
            z.hit_flash -= dt

        d = dist(player.x, player.y, z.x, z.y)
        aggro_range = 220 if night else 90
        z.aggro = d < aggro_range or z.alert_t > 0

        if z.aggro:
            dx, dy = player.x - z.x, player.y - z.y
            l = math.hypot(dx, dy) or 1
            dx, dy = dx / l, dy / l
            if d < 14:
                player.hp = max(0, player.hp - dt * 16)
                if not z.biting:
                    z.biting = True
                    log("¡Un zombi te está mordiendo!")
                    if z.alert_cd <= 0:
                        for other in zombies:
                            if other.dead or other is z:
                                continue
                            if dist(z.x, z.y, other.x, other.y) < 1200:
                                other.alert_t = 8.0
                        z.alert_cd = 7.0
            else:
                z.biting = False
        else:
            z.wander_t -= dt
            if z.wander_t <= 0:
                z.wander_t = 2 + random.random() * 3
                a = random.random() * math.pi * 2
                z.wander_dir = (math.cos(a), math.sin(a))
            dx, dy = z.wander_dir

        # Movimiento con anti-tunneling: prueba tile destino final
        nx, ny = z.x + dx * base_speed * dt, z.y + dy * base_speed * dt
        if _zombie_can_move(z, nx, ny):
            z.x, z.y = nx, ny
        else:
            # Intenta deslizar por ejes si el destino diagonal está bloqueado
            if _zombie_can_move(z, nx, z.y):
                z.x = nx
            elif _zombie_can_move(z, z.x, ny):
                z.y = ny

        if dx != 0:
            z.facing = 1 if dx > 0 else -1
        z.vx, z.vy = dx, dy
        z.anim_t += dt

    zombies[:] = [z for z in zombies if not z.dead]

    zombie_spawn_timer -= dt
    cap = 14 if night else 6
    if zombie_spawn_timer <= 0 and len(zombies) < cap:
        zombie_spawn_timer = 2.5 if night else 6
        spawn_zombie(night)

def update_bullets(dt):
    for b in bullets:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["life"] -= dt
        # Punto 5: blocked() ya respeta puertas abiertas (is_zombie=False)
        if blocked(int(b["x"] // TILE), int(b["y"] // TILE), False):
            b["life"] = 0
        for z in zombies:
            if z.dead:
                continue
            if dist(b["x"], b["y"], z.x, z.y) < 10:
                z.hp -= b["dmg"]
                z.hit_flash = 0.15
                b["life"] = 0
                if z.hp <= 0:
                    z.dead = True
                    log("Zombi abatido.")
                break
    bullets[:] = [b for b in bullets if b["life"] > 0]

def respawn_pickup(pickup, pickup_type):
    tries = 0
    while True:
        tx = random.randint(0, WORLD_W - 1)
        ty = random.randint(0, WORLD_H - 1)
        tries += 1
        if (not tile_solid(tx, ty) and not tile_water(tx, ty)) or tries > 50:
            break
    pickup["x"] = tx * TILE + 8
    pickup["y"] = ty * TILE + 8
    pickup["active"] = True
    pickup["timer"] = 0.0
    pickup.pop("hits", None)           # limpia contadores de golpes
    if pickup_type == "food":
        pickup["type"] = "berry" if random.random() < 0.7 else "herb"
    else:
        pickup["type"] = pickup_type

def update_all_pickups(dt):
    for a in ammo_pickups:
        if not a["active"]:
            a["timer"] -= dt
            if a["timer"] <= 0:
                respawn_pickup(a, "ammo")
    for w in wood_pickups:
        if not w["active"]:
            w["timer"] -= dt
            if w["timer"] <= 0:
                respawn_pickup(w, "tree")
    for r in rock_pickups:
        if not r["active"]:
            r["timer"] -= dt
            if r["timer"] <= 0:
                respawn_pickup(r, "rock")
    for s in scrap_pickups:
        if not s["active"]:
            s["timer"] -= dt
            if s["timer"] <= 0:
                respawn_pickup(s, "scrap")
    for f in food_pickups:
        if not f["active"]:
            f["timer"] -= dt
            if f["timer"] <= 0:
                respawn_pickup(f, "berry" if random.random() < 0.7 else "herb")

def update_camera():
    global camera_x, camera_y
    camera_x = player.x - (SCREEN_W / PIXEL_SCALE) / 2
    camera_y = player.y - (SCREEN_H / PIXEL_SCALE) / 2

def world_to_screen(wx, wy):
    return (wx - camera_x) * PIXEL_SCALE, (wy - camera_y) * PIXEL_SCALE

# ----------------------------------------------------------------------------
# 14. RENDER
# ----------------------------------------------------------------------------
def px(surface, x, y, w, h, color):
    pygame.draw.rect(surface, color, pygame.Rect(round(x), round(y), max(1, round(w)), max(1, round(h))))

def draw_tile(surface, tx, ty):
    t = tile_at(tx, ty)
    sx, sy = world_to_screen(tx * TILE, ty * TILE)
    checker = (tx + ty) % 2 == 0
    pairs = {0: ("grass1", "grass2"), 1: ("dirt1", "dirt2"), 2: ("road1", "road2"), 3: ("water1", "water2")}
    c1, c2 = pairs.get(t, ("ruin1", "ruin2"))
    color = PALETTE[c1] if checker else PALETTE[c2]
    px(surface, sx, sy, TILE * PIXEL_SCALE, TILE * PIXEL_SCALE, color)

def draw_resource(surface, r):
    if not r["active"]:
        return
    sx, sy = world_to_screen(r["x"] - 8, r["y"] - 8)
    u = PIXEL_SCALE
    t = r["type"]
    if t == "tree":
        px(surface, sx + 5 * u, sy + 9 * u, 3 * u, 6 * u, PALETTE["tree_trunk"])
        px(surface, sx + 1 * u, sy + 1 * u, 11 * u, 8 * u, PALETTE["tree_leaf"])
        px(surface, sx + 2 * u, sy, 9 * u, 2 * u, PALETTE["tree_leaf_dark"])
    elif t == "rock":
        px(surface, sx + 2 * u, sy + 6 * u, 12 * u, 7 * u, PALETTE["rock"])
        px(surface, sx + 2 * u, sy + 11 * u, 12 * u, 2 * u, PALETTE["rock_dark"])
    elif t == "scrap":
        px(surface, sx + 1 * u, sy + 7 * u, 13 * u, 6 * u, PALETTE["scrap_pile"])
        px(surface, sx + 1 * u, sy + 11 * u, 13 * u, 2 * u, PALETTE["scrap_pile_dark"])
    elif t == "herb":
        px(surface, sx + 5 * u, sy + 7 * u, 6 * u, 6 * u, PALETTE["herb_leaf"])
        px(surface, sx + 7 * u, sy + 9 * u, 2 * u, 2 * u, PALETTE["herb_flower"])
    else:
        px(surface, sx + 4 * u, sy + 4 * u, 8 * u, 8 * u, PALETTE["tree_leaf"])
        px(surface, sx + 6 * u, sy + 6 * u, 2 * u, 2 * u, PALETTE["fire2"])
        px(surface, sx + 9 * u, sy + 8 * u, 2 * u, 2 * u, PALETTE["fire2"])

def draw_gun_pickup(surface):
    if not gun_pickup or gun_pickup["taken"]:
        return
    sx, sy = world_to_screen(gun_pickup["x"] - 8, gun_pickup["y"] - 8)
    u = PIXEL_SCALE
    bob = math.sin(pygame.time.get_ticks() / 300) * 1.5
    px(surface, sx + 3 * u, sy + 8 * u + bob, 8 * u, 3 * u, PALETTE["gun_metal"])
    px(surface, sx + 3 * u, sy + 11 * u + bob, 3 * u, 4 * u, PALETTE["gun_grip"])
    px(surface, sx + 9 * u, sy + 7 * u + bob, 3 * u, 2 * u, PALETTE["gun_dark"])

def draw_ammo_pickup(surface, a):
    if not a["active"]:
        return
    sx, sy = world_to_screen(a["x"] - 8, a["y"] - 8)
    u = PIXEL_SCALE
    px(surface, sx + 2 * u, sy + 7 * u, 12 * u, 8 * u, PALETTE["crate"])
    px(surface, sx + 2 * u, sy + 12 * u, 12 * u, 3 * u, PALETTE["crate_dark"])
    px(surface, sx + 6 * u, sy + 9 * u, 4 * u, 4 * u, PALETTE["crate_mark"])

def draw_bullet(surface, b):
    sx, sy = world_to_screen(b["x"] - 2, b["y"] - 2)
    px(surface, sx, sy, 3 * PIXEL_SCALE, 3 * PIXEL_SCALE, PALETTE["bullet"])

def draw_structure(surface, st):
    sx, sy = world_to_screen(st["x"] - 8, st["y"] - 8)
    u = PIXEL_SCALE
    t = st["type"]
    if t == "wall":
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["wall"])
        px(surface, sx, sy + 13 * u, 16 * u, 3 * u, PALETTE["wall_dark"])
        px(surface, sx, sy, 16 * u, 2 * u, PALETTE["wall_dark"])
    elif t == "wallStone":
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["rock"])
        px(surface, sx, sy + 13 * u, 16 * u, 3 * u, PALETTE["rock_dark"])
        px(surface, sx, sy, 16 * u, 2 * u, PALETTE["rock_dark"])
        px(surface, sx + 5 * u, sy + 5 * u, 3 * u, 3 * u, PALETTE["rock_dark"])
        px(surface, sx + 9 * u, sy + 9 * u, 3 * u, 3 * u, PALETTE["rock_dark"])
    elif t == "door":
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["door_open_frame"])
        if not st["open"]:
            px(surface, sx + 2 * u, sy + 1 * u, 12 * u, 14 * u, PALETTE["door_plank"])
            px(surface, sx + 9 * u, sy + 7 * u, 2 * u, 2 * u, PALETTE["door_dark"])
        else:
            px(surface, sx + 1 * u, sy + 1 * u, 3 * u, 14 * u, PALETTE["door_plank"])
    elif t == "fire":
        px(surface, sx + 6 * u, sy + 10 * u, 4 * u, 4 * u, (42, 42, 42))
        flick = math.sin(pygame.time.get_ticks() / 90) * 1.5
        px(surface, sx + 6 * u, sy + 6 * u + flick, 4 * u, 6 * u, PALETTE["fire2"])
        px(surface, sx + 7 * u, sy + 3 * u + flick, 2 * u, 5 * u, PALETTE["fire1"])
    else:
        px(surface, sx + 2 * u, sy + 6 * u, 12 * u, 8 * u, PALETTE["chest"])
        px(surface, sx + 2 * u, sy + 9 * u, 12 * u, 2 * u, PALETTE["chest_dark"])

def draw_character(surface, x, y, facing, vx, vy, anim_t, body_color, body_dark, head_color, hit_flash):
    sx, sy = world_to_screen(x - 8, y - 8)
    u = PIXEL_SCALE
    bob = math.sin(anim_t * 8) if math.hypot(vx, vy) > 1 else 0
    bc = (255, 255, 255) if hit_flash > 0 else body_color
    hc = (255, 255, 255) if hit_flash > 0 else head_color
    px(surface, sx + 4 * u, sy + 7 * u + bob, 8 * u, 7 * u, bc)
    px(surface, sx + 4 * u, sy + 12 * u + bob, 3 * u, 3 * u, body_dark)
    px(surface, sx + 9 * u, sy + 12 * u + bob, 3 * u, 3 * u, body_dark)
    px(surface, sx + 5 * u, sy + 2 * u + bob, 6 * u, 6 * u, hc)
    if facing >= 0:
        px(surface, sx + 10 * u, sy + 8 * u + bob, 2 * u, 2 * u, body_dark)
    else:
        px(surface, sx + 4 * u, sy + 8 * u + bob, 2 * u, 2 * u, body_dark)

def draw_swing(surface, x, y, action_anim):
    if not action_anim or action_anim["t"] <= 0:
        return
    a = action_anim
    sx, sy = world_to_screen(x - 8, y - 8)
    u = PIXEL_SCALE
    alpha = max(0.0, a["t"] / a["total"])
    base = PALETTE["bullet"] if a["type"] == "gun" else (242, 239, 224)
    col = (*base, int(255 * alpha))
    dx, dy = a["dx"], a["dy"]
    surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    if dx > 0:
        pygame.draw.rect(surf, col, (sx + 13 * u, sy + 3 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx + 16 * u, sy + 7 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx + 13 * u, sy + 11 * u, 5 * u, 3 * u))
    elif dx < 0:
        pygame.draw.rect(surf, col, (sx - 2 * u, sy + 3 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx - 5 * u, sy + 7 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx - 2 * u, sy + 11 * u, 5 * u, 3 * u))
    elif dy < 0:
        pygame.draw.rect(surf, col, (sx + 2 * u, sy - 2 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 6 * u, sy - 5 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 10 * u, sy - 2 * u, 3 * u, 5 * u))
    else:
        pygame.draw.rect(surf, col, (sx + 2 * u, sy + 15 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 6 * u, sy + 18 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 10 * u, sy + 15 * u, 3 * u, 5 * u))
    surface.blit(surf, (0, 0))

def draw_build_preview(surface):
    dirx, diry = cardinal_from_aim()
    tx = round((player.x + dirx * TILE) / TILE) * TILE
    ty = round((player.y + diry * TILE) / TILE) * TILE
    sx, sy = world_to_screen(tx, ty)
    pulse = 0.35 + math.sin(pygame.time.get_ticks() / 150) * 0.15
    s = pygame.Surface((TILE * PIXEL_SCALE, TILE * PIXEL_SCALE), pygame.SRCALPHA)
    s.fill((244, 224, 74, int(255 * pulse)))
    surface.blit(s, (sx, sy))
    pygame.draw.rect(surface, (244, 224, 74), (sx, sy, TILE * PIXEL_SCALE, TILE * PIXEL_SCALE), 2)

def draw_night_overlay(surface):
    dark = night_darkness()
    if dark <= 0.01:
        return
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((6, 10, 25, int(dark * 0.65 * 255)))
    for st in structures:
        if st["type"] != "fire":
            continue
        sx, sy = world_to_screen(st["x"], st["y"])
        light = pygame.Surface((180 * PIXEL_SCALE, 180 * PIXEL_SCALE), pygame.SRCALPHA)
        pygame.draw.circle(light, (232, 134, 42, int(110 * dark)), (90 * PIXEL_SCALE, 90 * PIXEL_SCALE), 90 * PIXEL_SCALE)
        overlay.blit(light, (sx - 90 * PIXEL_SCALE, sy - 90 * PIXEL_SCALE), special_flags=pygame.BLEND_RGBA_SUB)
    sx, sy = world_to_screen(player.x, player.y)
    light = pygame.Surface((140 * PIXEL_SCALE, 140 * PIXEL_SCALE), pygame.SRCALPHA)
    pygame.draw.circle(light, (255, 255, 255, int(34 * dark)), (70 * PIXEL_SCALE, 70 * PIXEL_SCALE), 70 * PIXEL_SCALE)
    overlay.blit(light, (sx - 70 * PIXEL_SCALE, sy - 70 * PIXEL_SCALE), special_flags=pygame.BLEND_RGBA_SUB)
    surface.blit(overlay, (0, 0))

def draw_aim_cursor(surface):
    mx, my = pygame.mouse.get_pos()
    col = (244, 224, 74)
    pygame.draw.line(surface, col, (mx - 6, my), (mx + 6, my), max(1, PIXEL_SCALE // 2))
    pygame.draw.line(surface, col, (mx, my - 6), (mx, my + 6), max(1, PIXEL_SCALE // 2))

def render_world(surface):
    surface.fill((0, 0, 0))
    tiles_x = int(SCREEN_W / (TILE * PIXEL_SCALE)) + 3
    tiles_y = int(SCREEN_H / (TILE * PIXEL_SCALE)) + 3
    start_x = int(camera_x // TILE) - 1
    start_y = int(camera_y // TILE) - 1
    for yy in range(tiles_y):
        for xx in range(tiles_x):
            draw_tile(surface, start_x + xx, start_y + yy)

    for w in wood_pickups:
        if w["active"]:
            draw_resource(surface, w)
    for r in rock_pickups:
        if r["active"]:
            draw_resource(surface, r)
    for s in scrap_pickups:
        if s["active"]:
            draw_resource(surface, s)
    for f in food_pickups:
        if f["active"]:
            draw_resource(surface, f)

    if gun_pickup and not gun_pickup["taken"]:
        draw_gun_pickup(surface)
    for a in ammo_pickups:
        if a["active"]:
            draw_ammo_pickup(surface, a)

    for st in structures:
        draw_structure(surface, st)
    if build_menu_open:
        draw_build_preview(surface)

    for b in bullets:
        draw_bullet(surface, b)

    for z in zombies:
        draw_character(surface, z.x, z.y, z.facing, z.vx, z.vy, z.anim_t,
                        PALETTE["zombie_body"], PALETTE["zombie_body_dark"],
                        PALETTE["zombie_head"], z.hit_flash)

    draw_character(surface, player.x, player.y, player.facing,
                    player.vx, player.vy, player.anim_t,
                    PALETTE["player_body"], PALETTE["player_body_dark"],
                    PALETTE["player_head"], 0)
    draw_swing(surface, player.x, player.y, player.action_anim)

    draw_night_overlay(surface)
    draw_aim_cursor(surface)

def draw_text(surface, text, pos, font=FONT_SMALL, color=(217, 214, 194)):
    img = font.render(text, True, color)
    surface.blit(img, pos)
    return img.get_rect(topleft=pos)

def render_hud(surface):
    panel_w = 200 * PIXEL_SCALE // 2
    panel_h = 84 * PIXEL_SCALE // 2
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((11, 13, 10, 190))
    surface.blit(panel, (10 * PIXEL_SCALE // 2, 10 * PIXEL_SCALE // 2))
    bars = [("PV", player.hp, player.max_hp, (184, 67, 59)),
            ("ST", player.stamina, player.max_stamina, (143, 174, 76)),
            ("HB", player.hunger, player.max_hunger, (201, 138, 75))]
    for i, (label, val, mx, color) in enumerate(bars):
        y = int((18 + i * 22) * PIXEL_SCALE // 2)
        draw_text(surface, label, (int(18 * PIXEL_SCALE // 2), y))
        pygame.draw.rect(surface, (0, 0, 0), (int(52 * PIXEL_SCALE // 2), y + 2, int(140 * PIXEL_SCALE // 2), int(10 * PIXEL_SCALE // 2)))
        w = int(int(138 * PIXEL_SCALE // 2) * max(0, val / mx))
        pygame.draw.rect(surface, color, (int(53 * PIXEL_SCALE // 2), y + 3, w, int(8 * PIXEL_SCALE // 2)))

    day_txt = ("NOCHE " if is_night() else "DÍA ") + str(day_count)
    day_color = (92, 122, 134) if is_night() else (217, 183, 74)
    dbadge = FONT_MED.render(day_txt, True, day_color)
    surface.blit(dbadge, (SCREEN_W - dbadge.get_width() - 14, 14))

    weapon_txt = f"Arma: [{WEAPON_LABELS[player.equipped]}]  (TAB cambia)"
    if player.equipped == "gun":
        weapon_txt += f"   Balas: {player.ammo}"
    wtxt = FONT_SMALL.render(weapon_txt, True, (217, 183, 74))
    surface.blit(wtxt, (SCREEN_W - wtxt.get_width() - 14, 44))

    inv_txt = (f"Madera:{player.inv_wood}  Chatarra:{player.inv_scrap}  Piedra:{player.inv_stone}  "
               f"Comida:{player.inv_food}  Vendas:{player.bandages}")
    itxt = FONT_SMALL.render(inv_txt, True, (217, 183, 74))
    surface.blit(itxt, (SCREEN_W - itxt.get_width() - 14, 66))

    hint = FONT_SMALL.render(
        "WASD mover · Mouse apuntar · Espacio/Clic atacar · E recoger · Q mochila · B construir · TAB arma",
        True, (141, 145, 120))
    surface.blit(hint, (14, SCREEN_H - 24))

    for i, line in enumerate(log_lines[-5:]):
        t = FONT_SMALL.render(line, True, (141, 145, 120))
        surface.blit(t, (14, SCREEN_H - 155 + i * 20))

def panel_bg(surface, rect, alpha=235):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill((20, 23, 15, alpha))
    surface.blit(s, rect.topleft)
    pygame.draw.rect(surface, (58, 64, 40), rect, max(1, PIXEL_SCALE // 2))

def render_build_menu(surface):
    buttons = {}
    types = ["wall", "fire", "chest", "wallStone", "door"]
    panel_w = 320 * PIXEL_SCALE // 2
    x0 = SCREEN_W // 2 - panel_w // 2
    y0 = SCREEN_H - int(240 * PIXEL_SCALE // 2)
    panel = pygame.Rect(x0, y0, panel_w, int(200 * PIXEL_SCALE // 2))
    panel_bg(surface, panel)
    draw_text(surface, "CONSTRUIR", (panel.x + int(12 * PIXEL_SCALE // 2), panel.y + int(8 * PIXEL_SCALE // 2)), FONT_MED, (217, 183, 74))
    for i, t in enumerate(types):
        rect = pygame.Rect(x0 + int(10 * PIXEL_SCALE // 2), y0 + int(38 * PIXEL_SCALE // 2) + i * int(32 * PIXEL_SCALE // 2), panel_w - int(20 * PIXEL_SCALE // 2), int(28 * PIXEL_SCALE // 2))
        ok = can_afford(t)
        color = (58, 64, 45) if ok else (40, 30, 30)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (58, 64, 40) if ok else (60, 40, 40), rect, max(1, PIXEL_SCALE // 2))
        txt_color = (217, 214, 194) if ok else (110, 110, 110)
        draw_text(surface, BUILD_LABELS[t], (rect.x + int(8 * PIXEL_SCALE // 2), rect.y + int(6 * PIXEL_SCALE // 2)), FONT_SMALL, txt_color)
        buttons[t] = rect
    return buttons

def handle_build_click(pos, buttons):
    for t, rect in buttons.items():
        if rect.collidepoint(pos):
            build_structure(t)
            return

def _weapon_row(surface, panel, y, name, owned, cost_ok, cost_label):
    rect = pygame.Rect(panel.x + int(16 * PIXEL_SCALE // 2), y, int(308 * PIXEL_SCALE // 2), int(32 * PIXEL_SCALE // 2))
    if not owned:
        pygame.draw.rect(surface, (58, 64, 45) if cost_ok else (40, 30, 30), rect)
        pygame.draw.rect(surface, (58, 64, 40), rect, max(1, PIXEL_SCALE // 2))
        draw_text(surface, cost_label, (rect.x + int(8 * PIXEL_SCALE // 2), rect.y + int(8 * PIXEL_SCALE // 2)))
        return rect, "craft"
    equipped = player.equipped == name
    pygame.draw.rect(surface, (74, 90, 45) if equipped else (58, 64, 45), rect)
    pygame.draw.rect(surface, (217, 183, 74) if equipped else (58, 64, 40), rect, max(1, PIXEL_SCALE // 2))
    label = f"{WEAPON_LABELS[name]}: {'EQUIPADA (clic para guardar)' if equipped else 'en mochila (clic para equipar)'}"
    draw_text(surface, label, (rect.x + int(8 * PIXEL_SCALE // 2), rect.y + int(8 * PIXEL_SCALE // 2)))
    return rect, "equip"

def render_inventory(surface):
    buttons = {}
    panel = pygame.Rect(SCREEN_W // 2 - int(170 * PIXEL_SCALE // 2), SCREEN_H // 2 - int(230 * PIXEL_SCALE // 2), int(340 * PIXEL_SCALE // 2), int(440 * PIXEL_SCALE // 2))
    panel_bg(surface, panel)
    y = panel.y + int(14 * PIXEL_SCALE // 2)
    draw_text(surface, "MOCHILA", (panel.x + int(16 * PIXEL_SCALE // 2), y), FONT_MED, (217, 183, 74))
    y += int(26 * PIXEL_SCALE // 2)
    draw_text(surface, f"Arma equipada: [{WEAPON_LABELS[player.equipped]}]  (TAB cambia)",
              (panel.x + int(16 * PIXEL_SCALE // 2), y), FONT_SMALL, (217, 183, 74))
    y += int(26 * PIXEL_SCALE // 2)

    rows = [f"Madera: {player.inv_wood}", f"Chatarra: {player.inv_scrap}", f"Piedra: {player.inv_stone}",
            f"Comida: {player.inv_food}", f"Vendas: {player.bandages}", f"Balas: {player.ammo}"]
    for r in rows:
        draw_text(surface, r, (panel.x + int(16 * PIXEL_SCALE // 2), y))
        y += int(20 * PIXEL_SCALE // 2)
    y += int(6 * PIXEL_SCALE // 2)

    food_ok = player.inv_food > 0 and player.hunger < player.max_hunger
    band_ok = player.bandages > 0 and player.hp < player.max_hp
    r1 = pygame.Rect(panel.x + int(16 * PIXEL_SCALE // 2), y, int(150 * PIXEL_SCALE // 2), int(30 * PIXEL_SCALE // 2))
    r2 = pygame.Rect(panel.x + int(174 * PIXEL_SCALE // 2), y, int(150 * PIXEL_SCALE // 2), int(30 * PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (58, 64, 45) if food_ok else (40, 30, 30), r1)
    pygame.draw.rect(surface, (58, 64, 40), r1, max(1, PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (74, 30, 30) if band_ok else (40, 30, 30), r2)
    pygame.draw.rect(surface, (184, 67, 59), r2, max(1, PIXEL_SCALE // 2))
    draw_text(surface, "Comer (+hambre)", (r1.x + int(8 * PIXEL_SCALE // 2), r1.y + int(8 * PIXEL_SCALE // 2)))
    draw_text(surface, "Vendar (+30 PV)", (r2.x + int(8 * PIXEL_SCALE // 2), r2.y + int(8 * PIXEL_SCALE // 2)))
    buttons["food"] = r1
    buttons["bandage"] = r2
    y += int(42 * PIXEL_SCALE // 2)

    draw_text(surface, "ARMAS", (panel.x + int(16 * PIXEL_SCALE // 2), y), FONT_MED, (217, 183, 74))
    y += int(30 * PIXEL_SCALE // 2)

    axe_ok = (not player.has_axe) and player.inv_wood >= 3 and player.inv_scrap >= 2
    rect, kind = _weapon_row(surface, panel, y, "axe", player.has_axe, axe_ok,
                              "Hacha (Madera 3, Chatarra 2) — recolecta de un golpe")
    buttons["axe"] = (rect, kind)
    y += int(38 * PIXEL_SCALE // 2)

    pick_ok = (not player.has_pickaxe) and player.inv_wood >= 4 and player.inv_scrap >= 5
    rect, kind = _weapon_row(surface, panel, y, "pickaxe", player.has_pickaxe, pick_ok,
                              "Pico (Madera 4, Chatarra 5) — rompe rocas")
    buttons["pickaxe"] = (rect, kind)
    y += int(38 * PIXEL_SCALE // 2)

    bat_ok = (not player.has_bat) and player.inv_wood >= 4 and player.inv_scrap >= 4
    rect, kind = _weapon_row(surface, panel, y, "bat", player.has_bat, bat_ok,
                              "Bate (Madera 4, Chatarra 4) {— más daño cuerpo a cuerpo}")
    buttons["bat"] = (rect, kind)
    y += int(38 * PIXEL_SCALE // 2)

    if player.has_gun:
        rect, kind = _weapon_row(surface, panel, y, "gun", True, False, "")
        buttons["gun"] = (rect, kind)
        y += int(38 * PIXEL_SCALE // 2)

    y += int(8 * PIXEL_SCALE // 2)
    draw_text(surface, "E recolectar · Q cerrar · B construir · TAB arma", (panel.x + int(16 * PIXEL_SCALE // 2), y), FONT_SMALL, (141, 145, 120))
    return buttons

def handle_inventory_click(pos, buttons):
    if buttons.get("food") and buttons["food"].collidepoint(pos):
        use_food()
        return
    if buttons.get("bandage") and buttons["bandage"].collidepoint(pos):
        use_bandage()
        return
    for name, craft_fn in (("axe", craft_axe), ("pickaxe", craft_pickaxe), ("bat", craft_bat), ("gun", None)):
        entry = buttons.get(name)
        if not entry:
            continue
        rect, kind = entry
        if rect.collidepoint(pos):
            if kind == "craft" and craft_fn:
                craft_fn()
            else:
                toggle_equip(name)
            return

def render_storage(surface):
    buttons = {}
    panel = pygame.Rect(SCREEN_W // 2 - int(190 * PIXEL_SCALE // 2), SCREEN_H // 2 - int(220 * PIXEL_SCALE // 2), int(380 * PIXEL_SCALE // 2), int(420 * PIXEL_SCALE // 2))
    panel_bg(surface, panel)
    y = panel.y + int(14 * PIXEL_SCALE // 2)
    draw_text(surface, "ALMACÉN", (panel.x + int(16 * PIXEL_SCALE // 2), y), FONT_MED, (217, 183, 74))
    y += int(34 * PIXEL_SCALE // 2)

    store = active_chest["store"]
    keys = [("wood", "Madera", "inv_wood"), ("scrap", "Chatarra", "inv_scrap"),
            ("stone", "Piedra", "inv_stone"), ("food", "Comida", "inv_food"),
            ("bandages", "Vendas", "bandages")]
    for key, label, bag_attr in keys:
        bag_val = getattr(player, bag_attr)
        chest_val = store.get(key, 0)
        draw_text(surface, f"{label}:  Mochila {bag_val}   |   Cofre {chest_val}", (panel.x + int(16 * PIXEL_SCALE // 2), y + int(4 * PIXEL_SCALE // 2)))
        r_to = pygame.Rect(panel.x + int(280 * PIXEL_SCALE // 2), y, int(32 * PIXEL_SCALE // 2), int(26 * PIXEL_SCALE // 2))
        r_from = pygame.Rect(panel.x + int(318 * PIXEL_SCALE // 2), y, int(32 * PIXEL_SCALE // 2), int(26 * PIXEL_SCALE // 2))
        pygame.draw.rect(surface, (58, 64, 45), r_to)
        pygame.draw.rect(surface, (58, 64, 45), r_from)
        pygame.draw.rect(surface, (58, 64, 40), r_to, max(1, PIXEL_SCALE // 2))
        pygame.draw.rect(surface, (58, 64, 40), r_from, max(1, PIXEL_SCALE // 2))
        draw_text(surface, "→", (r_to.x + int(10 * PIXEL_SCALE // 2), r_to.y + int(4 * PIXEL_SCALE // 2)))
        draw_text(surface, "←", (r_from.x + int(10 * PIXEL_SCALE // 2), r_from.y + int(4 * PIXEL_SCALE // 2)))
        buttons[f"to_{key}"] = r_to
        buttons[f"from_{key}"] = r_from
        y += int(34 * PIXEL_SCALE // 2)

    y += int(12 * PIXEL_SCALE // 2)
    food_ok = player.inv_food > 0 and player.hunger < player.max_hunger
    band_ok = player.bandages > 0 and player.hp < player.max_hp
    r1 = pygame.Rect(panel.x + int(16 * PIXEL_SCALE // 2), y, int(170 * PIXEL_SCALE // 2), int(30 * PIXEL_SCALE // 2))
    r2 = pygame.Rect(panel.x + int(194 * PIXEL_SCALE // 2), y, int(170 * PIXEL_SCALE // 2), int(30 * PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (58, 64, 45) if food_ok else (40, 30, 30), r1)
    pygame.draw.rect(surface, (74, 30, 30) if band_ok else (40, 30, 30), r2)
    pygame.draw.rect(surface, (58, 64, 40), r1, max(1, PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (184, 67, 59), r2, max(1, PIXEL_SCALE // 2))
    draw_text(surface, "Comer (+hambre)", (r1.x + int(8 * PIXEL_SCALE // 2), r1.y + int(8 * PIXEL_SCALE // 2)))
    draw_text(surface, "Vendar (+30 PV)", (r2.x + int(8 * PIXEL_SCALE // 2), r2.y + int(8 * PIXEL_SCALE // 2)))
    buttons["food"] = r1
    buttons["bandage"] = r2
    y += int(46 * PIXEL_SCALE // 2)

    rc = pygame.Rect(panel.x + int(16 * PIXEL_SCALE // 2), y, int(348 * PIXEL_SCALE // 2), int(34 * PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (58, 64, 45), rc)
    pygame.draw.rect(surface, (58, 64, 40), rc, max(1, PIXEL_SCALE // 2))
    draw_text(surface, "Cerrar", (rc.x + int(150 * PIXEL_SCALE // 2), rc.y + int(8 * PIXEL_SCALE // 2)))
    buttons["close"] = rc
    return buttons

def handle_storage_click(pos, buttons):
    for k, r in buttons.items():
        if not r.collidepoint(pos):
            continue
        if k.startswith("to_"):
            move_to_chest(k[3:])
        elif k.startswith("from_"):
            move_to_bag(k[5:])
        elif k == "food":
            use_food()
        elif k == "bandage":
            use_bandage()
        elif k == "close":
            close_storage()
        return

def render_start_screen(surface):
    surface.fill((11, 13, 10))
    title = FONT_TITLE.render("ÉBANO // PROTOCOLO DE RUINA", True, (143, 174, 76))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, int(130 * PIXEL_SCALE // 2)))
    lines = [
        "Sobrevive de día. Resiste de noche.",
        "Recolecta madera, chatarra y piedra, y construye tu refugio.",
        "WASD moverte · Mouse apuntar · Espacio/Clic atacar",
        "E recolectar · Q mochila y crafteo · B construir · TAB cambiar arma",
    ]
    for i, l in enumerate(lines):
        t = FONT_SMALL.render(l, True, (141, 145, 120))
        surface.blit(t, (SCREEN_W // 2 - t.get_width() // 2, int(210 * PIXEL_SCALE // 2) + i * int(26 * PIXEL_SCALE // 2)))
    btn = pygame.Rect(SCREEN_W // 2 - int(100 * PIXEL_SCALE // 2), int(350 * PIXEL_SCALE // 2), int(200 * PIXEL_SCALE // 2), int(54 * PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (20, 23, 15), btn)
    pygame.draw.rect(surface, (217, 183, 74), btn, max(1, PIXEL_SCALE // 2))
    txt = FONT_MED.render("EMPEZAR", True, (217, 183, 74))
    surface.blit(txt, (btn.x + btn.w // 2 - txt.get_width() // 2, btn.y + btn.h // 2 - txt.get_height() // 2))
    return btn

def render_gameover_screen(surface):
    surface.fill((11, 13, 10))
    title = FONT_TITLE.render("HAS CAÍDO", True, (184, 67, 59))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, int(200 * PIXEL_SCALE // 2)))
    sub = FONT_MED.render(f"Sobreviviste {survived_days} día(s). El mundo sigue ahí fuera.", True, (141, 145, 120))
    surface.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, int(260 * PIXEL_SCALE // 2)))
    btn = pygame.Rect(SCREEN_W // 2 - int(100 * PIXEL_SCALE // 2), int(350 * PIXEL_SCALE // 2), int(200 * PIXEL_SCALE // 2), int(54 * PIXEL_SCALE // 2))
    pygame.draw.rect(surface, (20, 23, 15), btn)
    pygame.draw.rect(surface, (217, 183, 74), btn, max(1, PIXEL_SCALE // 2))
    txt = FONT_MED.render("REINTENTAR", True, (217, 183, 74))
    surface.blit(txt, (btn.x + btn.w // 2 - txt.get_width() // 2, btn.y + btn.h // 2 - txt.get_height() // 2))
    return btn

# ----------------------------------------------------------------------------
# 15. GUARDADO / CARGA
# ----------------------------------------------------------------------------
def delete_save():
    if os.path.exists(SAVE_FILE):
        try:
            os.remove(SAVE_FILE)
        except Exception:
            pass

def save_game():
    if game_state != STATE_PLAYING or player.hp <= 0:
        return
    data = {
        "px": player.x, "py": player.y, "hp": player.hp, "stamina": player.stamina, "hunger": player.hunger,
        "inv_wood": player.inv_wood, "inv_scrap": player.inv_scrap, "inv_food": player.inv_food,
        "inv_stone": player.inv_stone, "bandages": player.bandages,
        "has_gun": player.has_gun, "ammo": player.ammo, "has_axe": player.has_axe, "has_pickaxe": player.has_pickaxe, "has_bat": player.has_bat,
        "equipped": player.equipped,
        "structures": structures, "day_count": day_count, "world_time": world_time,
        "wood_pickups": wood_pickups, "rock_pickups": rock_pickups,
        "scrap_pickups": scrap_pickups, "food_pickups": food_pickups,
        "ammo_pickups": ammo_pickups, "gun_pickup": gun_pickup,
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print("No se pudo guardar:", e)

def load_game():
    global day_count, world_time, gun_pickup
    if not os.path.exists(SAVE_FILE):
        return False
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if d.get("hp", 0) <= 0:
            raise ValueError("guardado con hp <= 0")

        player.x = d["px"]
        player.y = d["py"]
        player.hp = d["hp"]
        player.stamina = d["stamina"]
        player.hunger = d["hunger"]
        player.inv_wood = d["inv_wood"]
        player.inv_scrap = d["inv_scrap"]
        player.inv_food = d["inv_food"]
        player.inv_stone = d.get("inv_stone", 0)
        player.bandages = d.get("bandages", 0)
        player.has_gun = d.get("has_gun", False)
        player.ammo = d.get("ammo", 0)
        player.has_axe = d.get("has_axe", False)
        player.has_pickaxe = d.get("has_pickaxe", False)
        player.has_bat = d.get("has_bat", False)
        player.equipped = d.get("equipped", "fist")
        if player.equipped not in available_weapons():
            player.equipped = "fist"

        structures[:] = d.get("structures", [])
        day_count = d.get("day_count", 1)
        world_time = d.get("world_time", 0.28)

        for lst, key in ((wood_pickups, "wood_pickups"), (rock_pickups, "rock_pickups"),
                         (scrap_pickups, "scrap_pickups"), (food_pickups, "food_pickups"),
                         (ammo_pickups, "ammo_pickups")):
            if key in d:
                lst[:] = d[key]

        if d.get("gun_pickup") is not None:
            gun_pickup = d["gun_pickup"]
        # Fix pistola duplicada: sincroniza taken con has_gun
        if gun_pickup:
            gun_pickup["taken"] = player.has_gun
    except Exception as e:
        print("Guardado inválido, se descarta:", e)
        delete_save()
        return False
    return True

# ----------------------------------------------------------------------------
# 16. CICLO DE VIDA DE LA PARTIDA
# ----------------------------------------------------------------------------
rain_sound = None

def start_audio():
    global rain_sound
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load("gameplay_1.mp3")
            pygame.mixer.music.set_volume(0.25)
            pygame.mixer.music.play(-1)
        if rain_sound is None:
            rain_sound = pygame.mixer.Sound("soft_rain.ogg")
            rain_sound.set_volume(0.3)
            rain_sound.play(-1)
    except Exception as e:
        print("Audio no disponible:", e)

def reset_run():
    global day_count, world_time, hunger_timer, zombie_spawn_timer, autosave_acc
    zombies.clear()
    bullets.clear()
    structures.clear()
    spawn_resources()
    spawn_gun_and_ammo()

    day_count = 1
    world_time = 0.28
    hunger_timer = 0.0
    zombie_spawn_timer = 0.0
    autosave_acc = 0.0

    player.x = WORLD_W * TILE / 2
    player.y = WORLD_H * TILE / 2
    player.vx = player.vy = 0.0
    player.hp = player.max_hp
    player.stamina = player.max_stamina
    player.exhausted = False
    player.hunger = player.max_hunger
    player.inv_wood, player.inv_scrap, player.inv_food, player.inv_stone, player.bandages = 4, 2, 0, 0, 0
    player.has_gun, player.ammo = False, 0
    player.has_axe, player.has_bat = False, False
    player.has_pickaxe = False
    player.equipped = "fist"
    player.attack_cooldown = 0.0
    player.action_anim = None
    player.hunger_warned = player.hunger_low_warned = False
    log_lines.clear()

def game_over():
    global game_state, survived_days
    if game_state != STATE_PLAYING:
        return
    survived_days = day_count
    game_state = STATE_GAMEOVER
    delete_save()
    pygame.mixer.Channel(1).stop()

def start_game():
    global game_state, inventory_open, build_menu_open
    reset_run()
    if load_game():
        log("Partida cargada.")
    else:
        reset_run()
        log("Nueva partida iniciada.")
    inventory_open = False
    build_menu_open = False
    close_storage()
    game_state = STATE_PLAYING
    start_audio()

# ----------------------------------------------------------------------------
# 17. BUCLE PRINCIPAL
# ----------------------------------------------------------------------------
def main():
    global build_menu_open, inventory_open, game_state, autosave_acc

    attack_pressed = False
    interact_pressed = False
    inv_buttons, storage_buttons, build_buttons = {}, {}, {}
    start_button_rect, retry_button_rect = None, None

    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if game_state == STATE_PLAYING:
                    save_game()
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if game_state == STATE_PLAYING:
                    if event.key == pygame.K_SPACE:
                        attack_pressed = True
                    elif event.key == pygame.K_e:
                        interact_pressed = True
                    elif event.key == pygame.K_q:
                        if active_chest:
                            close_storage()
                        else:
                            inventory_open = not inventory_open
                    elif event.key == pygame.K_b:
                        build_menu_open = not build_menu_open
                    elif event.key == pygame.K_TAB:
                        cycle_weapon()
                    elif event.key == pygame.K_ESCAPE:
                        inventory_open = False
                        build_menu_open = False
                        close_storage()
                    elif build_menu_open and event.key in BUILD_KEYS:
                        build_structure(BUILD_KEYS[event.key])
                elif game_state in (STATE_START, STATE_GAMEOVER):
                    if event.key == pygame.K_RETURN:
                        start_game()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if game_state == STATE_START and start_button_rect and start_button_rect.collidepoint(pos):
                    start_game()
                elif game_state == STATE_GAMEOVER and retry_button_rect and retry_button_rect.collidepoint(pos):
                    start_game()
                elif game_state == STATE_PLAYING:
                    if inventory_open:
                        handle_inventory_click(pos, inv_buttons)
                    elif active_chest:
                        handle_storage_click(pos, storage_buttons)
                    elif build_menu_open:
                        handle_build_click(pos, build_buttons)
                    else:
                        attack_pressed = True

        if game_state == STATE_PLAYING:
            paused_by_menu = inventory_open or (active_chest is not None)
            if paused_by_menu:
                pygame.mixer.Channel(1).stop()
            if not paused_by_menu:
                update_aim_from_mouse()
                update_day_night(dt)
                update_player(dt, pygame.key.get_pressed(), attack_pressed, interact_pressed)
                update_zombies(dt)
                update_bullets(dt)
                update_all_pickups(dt)
                update_camera()

                autosave_acc += dt
                if autosave_acc >= 30.0:   # ← 30 s en lugar de 8 s
                    autosave_acc = 0.0
                    save_game()
            attack_pressed = False
            interact_pressed = False

            render_world(screen)
            render_hud(screen)
            if build_menu_open:
                build_buttons = render_build_menu(screen)
            if inventory_open:
                inv_buttons = render_inventory(screen)
            if active_chest:
                storage_buttons = render_storage(screen)

        elif game_state == STATE_START:
            start_button_rect = render_start_screen(screen)
        elif game_state == STATE_GAMEOVER:
            retry_button_rect = render_gameover_screen(screen)

        pygame.display.flip()

if __name__ == "__main__":
    main()
