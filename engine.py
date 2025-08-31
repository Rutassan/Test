import random
from collections import deque


class Map:
    """Simple tile map for the battlefield."""

    def __init__(self, width=8, height=5, preset=None):
        self.width = width
        self.height = height
        self.tiles = {}
        self.shrines = set()
        presets = {
            "arena_ruins": {
                "obstacles": [(3, 1), (4, 3)],
                "hazards": [(2, 2)],
                "shrines": [(5, 2)],
            },
            "arena_forest": {
                "obstacles": [(1, 3), (6, 1)],
                "hazards": [(3, 2)],
                "shrines": [(4, 4)],
            },
            "arena_cavern": {
                "obstacles": [(3, 0), (3, 1), (4, 3)],
                "hazards": [(5, 1)],
                "shrines": [(2, 4)],
            },
        }
        if preset is None:
            preset = random.choice(list(presets.keys()))
        layout = presets[preset]
        for y in range(height):
            for x in range(width):
                terrain = "plain"
                passable = True
                if (x, y) in layout.get("obstacles", []):
                    terrain = "obstacle"
                    passable = False
                elif (x, y) in layout.get("hazards", []):
                    terrain = "hazard_poison"
                elif (x, y) in layout.get("shrines", []):
                    terrain = "shrine"
                    self.shrines.add((x, y))
                self.tiles[(x, y)] = {
                    "x": x,
                    "y": y,
                    "terrain": terrain,
                    "passable": passable,
                }

    def tile(self, x, y):
        return self.tiles.get((x, y))

    def neighbors(self, x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield nx, ny


class Character:
    """Base character with combat utilities and status management."""

    def __init__(self, name, hp, attack_range, icon, speed=1, crit=0.2,
                 move_points=3, attack_distance=1):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        # attack_range is damage spread (min,max)
        self.attack_range = attack_range
        self.icon = icon
        self.base_speed = speed
        self.base_crit = crit
        self.move_points = move_points
        self.range = attack_distance
        # grid position
        self.x = 0
        self.y = 0

        # exploration / patrol helpers
        self.patrol_path = []
        self.wander_area = None
        self._patrol_index = 0

        # status trackers
        self.poison = 0
        self.poison_turns = 0
        self.shield = 0
        self.rage = 0

        # new statuses
        self.aim = 0  # next attack bonus
        self.frenzy = 0  # turns remaining
        self.hexed = 0  # turns remaining
        self.regen = 0  # per turn heal amount

    # --- core helpers ---------------------------------------------------
    def is_alive(self):
        return self.hp > 0

    @property
    def speed(self):
        """Effective speed taking frenzy into account."""
        bonus = 1 if self.frenzy > 0 else 0
        return self.base_speed + bonus

    def begin_turn(self):
        """Apply beginning-of-turn effects like poison and rage."""
        events = []
        if self.poison_turns > 0 and self.is_alive():
            dmg = self.poison
            if isinstance(self, Troll):
                dmg *= 2
            self.hp = max(self.hp - dmg, 0)
            self.poison_turns -= 1
            events.append({
                "type": "damage",
                "target": self.name,
                "amount": dmg,
                "hp": self.hp,
                "source": "poison",
            })
            if self.hp == 0:
                events.append({"type": "death", "target": self.name})
        if self.rage > 0:
            self.rage -= 1
        elif self.hp and self.hp <= self.max_hp // 3:
            self.rage = 3
            events.append({"type": "status", "status": "rage", "target": self.name})
        return events

    def end_turn(self):
        """Handle end of turn effects like regeneration and timers."""
        events = []
        if self.regen and self.is_alive():
            heal_amt = min(self.regen, self.max_hp - self.hp)
            if heal_amt:
                self.hp += heal_amt
                events.append({
                    "type": "passive_tick",
                    "status": "regen",
                    "target": self.name,
                    "amount": heal_amt,
                    "hp": self.hp,
                })

        if self.frenzy > 0:
            self.frenzy -= 1
        if self.hexed > 0:
            self.hexed -= 1
        if self.aim > 0:
            self.aim = 0
        return events

    # --- combat actions -------------------------------------------------
    def take_damage(self, dmg):
        events = []
        if self.rage > 0:
            dmg = int(dmg * 1.5)
        if self.shield > 0:
            absorbed = min(self.shield, dmg)
            dmg -= absorbed
            self.shield -= absorbed
            if absorbed:
                events.append({
                    "type": "shield",
                    "target": self.name,
                    "amount": absorbed,
                    "remaining": self.shield,
                })
        self.hp = max(self.hp - dmg, 0)
        events.append({
            "type": "damage",
            "target": self.name,
            "amount": dmg,
            "hp": self.hp,
        })
        if self.hp == 0:
            events.append({"type": "death", "target": self.name})
        return events

    def _crit(self):
        chance = self.base_crit
        if self.aim:
            chance += 0.5
        return random.random() < chance

    def _damage_mod(self):
        dmg = 1.0
        if self.aim:
            dmg *= 1.25
        if self.frenzy > 0:
            dmg *= 1.25
        if self.hexed > 0:
            dmg *= 0.75
        if self.rage > 0:
            dmg *= 1.5
        return dmg

    def attack(self, other):
        events = []
        dmg = random.randint(*self.attack_range)
        dmg = int(dmg * self._damage_mod())
        crit = self._crit()
        if crit:
            dmg *= 2
        events.append({
            "type": "attack",
            "attacker": self.name,
            "target": other.name,
            "damage": dmg,
            "crit": crit,
        })
        events.extend(other.take_damage(dmg))
        if random.random() < 0.1 and other.is_alive():
            other.poison = random.randint(1, 3)
            other.poison_turns = 3
            events.append({
                "type": "status",
                "status": "poison",
                "target": other.name,
                "amount": other.poison,
                "turns": 3,
            })
        return events

    def heal_self(self):
        events = []
        amt = random.randint(1, 5)
        self.hp = min(self.hp + amt, self.max_hp)
        events.append({
            "type": "heal",
            "actor": self.name,
            "amount": amt,
            "hp": self.hp,
        })
        if random.random() < 0.3:
            shield_amt = random.randint(1, 3)
            self.shield += shield_amt
            events.append({
                "type": "status",
                "status": "shield",
                "target": self.name,
                "amount": shield_amt,
                "remaining": self.shield,
            })
        return events

    # --- AI -------------------------------------------------------------
    def take_turn(self, allies, enemies, game):
        """Default behaviour with simple movement towards target."""
        if not enemies:
            return []
        kite_ev = game.kite(self, enemies)
        if kite_ev:
            return kite_ev
        target = game.select_target(enemies)
        events = []
        dist = game.distance(self, target)
        if dist > self.range:
            events.extend(game.move_unit_towards(self, target))
            dist = game.distance(self, target)
            if dist > self.range:
                return events
        if self.range > 1 and not game.line_of_sight(self, target):
            events.append({
                "type": "los_blocked",
                "attacker_id": self.name,
                "target_id": target.name,
            })
            return events
        if random.random() < 0.8:
            events.extend(self.attack(target))
        else:
            events.extend(self.heal_self())
        return events


# --- Hero classes -------------------------------------------------------


class Warrior(Character):
    def __init__(self):
        super().__init__("Warrior", 30, (4, 8), "⚔️", speed=2, attack_distance=1)

    def take_turn(self, allies, enemies, game):
        if not enemies:
            return []
        kite_ev = game.kite(self, enemies)
        if kite_ev:
            return kite_ev
        target = game.select_target(enemies)
        events = []
        dist = game.distance(self, target)
        if dist > self.range:
            events.extend(game.move_unit_towards(self, target))
            dist = game.distance(self, target)
            if dist > self.range:
                return events
        r = random.random()
        if r < 0.2:
            game.taunt_target = self
            events.append({"type": "status", "status": "taunt", "actor": self.name})
        elif r < 0.9:
            events.extend(self.attack(target))
        else:
            events.extend(self.heal_self())
        return events


class Mage(Character):
    def __init__(self):
        super().__init__("Mage", 20, (5, 10), "🧙", speed=2, attack_distance=3)

    def take_turn(self, allies, enemies, game):
        if not enemies:
            return []
        target = game.select_target(enemies)
        events = []
        dist = game.distance(self, target)
        if dist > self.range:
            events.extend(game.move_unit_towards(self, target))
            dist = game.distance(self, target)
            if dist > self.range:
                return events
        r = random.random()
        if r < 0.2 and len(enemies) > 1:
            if not game.line_of_sight(self, target):
                events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": target.name})
                return events
            events.append({"type": "status", "status": "fireball", "actor": self.name})
            targets = random.sample(enemies, min(2, len(enemies)))
            for t in targets:
                if game.line_of_sight(self, t):
                    events.extend(self.attack(t))
                else:
                    events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": t.name})
            return events
        elif r < 0.9:
            if self.range > 1 and not game.line_of_sight(self, target):
                events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": target.name})
            else:
                events.extend(self.attack(target))
        else:
            events.extend(self.heal_self())
        return events


# --- Monster classes ----------------------------------------------------


class Goblin(Character):
    def __init__(self):
        super().__init__("Goblin", 15, (3, 6), "👺", speed=2, attack_distance=1)


class Orc(Character):
    def __init__(self):
        super().__init__("Orc", 25, (2, 7), "👹", speed=1, move_points=2, attack_distance=1)


class Archer(Character):
    def __init__(self):
        super().__init__("Archer", 18, (4, 7), "🏹", speed=3, crit=0.25, attack_distance=3)

    def take_turn(self, allies, enemies, game):
        if not enemies:
            return []
        kite_ev = game.kite(self, enemies)
        if kite_ev:
            return kite_ev
        target = game.select_target(enemies, ignore_taunt=self.aim)
        events = []
        dist = game.distance(self, target)
        if dist > self.range:
            events.extend(game.move_unit_towards(self, target))
            dist = game.distance(self, target)
            if dist > self.range:
                return events
        if self.range > 1 and not game.line_of_sight(self, target):
            events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": target.name})
            return events
        if self.aim == 0 and random.random() < 0.3:
            self.aim = 1
            events.append({"type": "status", "status": "aim", "actor": self.name, "turns": 1})
        else:
            events.extend(self.attack(target))
        return events


class Priest(Character):
    def __init__(self):
        super().__init__("Priest", 18, (1, 4), "⛪", speed=2, attack_distance=2)

    def take_turn(self, allies, enemies, game):
        if enemies:
            kite_ev = game.kite(self, enemies)
            if kite_ev:
                return kite_ev
        allies_alive = [a for a in allies if a.is_alive()]
        if allies_alive:
            target = min(allies_alive, key=lambda c: c.hp / c.max_hp)
            heal = random.randint(4, 6)
            target.hp = min(target.hp + heal, target.max_hp)
            events = [{
                "type": "heal",
                "actor": self.name,
                "amount": heal,
                "hp": target.hp,
                "target": target.name,
            }]
            target.shield += 4
            events.append({
                "type": "status",
                "status": "shield",
                "target": target.name,
                "amount": 4,
                "remaining": target.shield,
            })
            return events
        # fallback attack
        if enemies:
            target = game.select_target(enemies)
            events = []
            dist = game.distance(self, target)
            if dist > self.range:
                events.extend(game.move_unit_towards(self, target))
                dist = game.distance(self, target)
                if dist > self.range:
                    return events
            if self.range > 1 and not game.line_of_sight(self, target):
                events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": target.name})
                return events
            events.extend(self.attack(target))
            return events
        return []


class Troll(Character):
    def __init__(self):
        super().__init__("Troll", 40, (3, 7), "🧌", speed=1, move_points=2, attack_distance=1)
        self.regen = 2


class Shaman(Character):
    def __init__(self):
        super().__init__("Shaman", 20, (2, 5), "🌀", speed=2, move_points=2, attack_distance=2)

    def take_turn(self, allies, enemies, game):
        if enemies:
            kite_ev = game.kite(self, enemies)
            if kite_ev:
                return kite_ev
        r = random.random()
        allies_alive = [a for a in allies if a.is_alive() and a is not self]
        if r < 0.5 and allies_alive:
            target = random.choice(allies_alive)
            target.frenzy = 2
            return [{
                "type": "status",
                "status": "frenzy",
                "target": target.name,
                "turns": 2,
                "actor": self.name,
            }]
        if r < 0.6 and enemies:
            target = game.select_target(enemies)
            events = []
            dist = game.distance(self, target)
            if dist > self.range:
                events.extend(game.move_unit_towards(self, target))
                dist = game.distance(self, target)
                if dist > self.range:
                    return events
            if self.range > 1 and not game.line_of_sight(self, target):
                events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": target.name})
                return events
            target.hexed = 1
            events.append({
                "type": "status",
                "status": "hex",
                "target": target.name,
                "turns": 1,
                "actor": self.name,
            })
            return events
        if enemies:
            target = game.select_target(enemies)
            events = []
            dist = game.distance(self, target)
            if dist > self.range:
                events.extend(game.move_unit_towards(self, target))
                dist = game.distance(self, target)
                if dist > self.range:
                    return events
            if self.range > 1 and not game.line_of_sight(self, target):
                events.append({"type": "los_blocked", "attacker_id": self.name, "target_id": target.name})
                return events
            events.extend(self.attack(target))
            return events
        return []


# --- Objective helpers --------------------------------------------------

class EnemyShrine(Character):
    """Immobile structure used for destroy_shrine missions."""

    def __init__(self, hp=20):
        super().__init__("Enemy Shrine", hp, (0, 0), "🏯", speed=0, move_points=0, attack_distance=1)

    def take_turn(self, allies, enemies, game):
        # Shrine does nothing on its turn
        return []


# --- Game engine --------------------------------------------------------


class Game:
    def __init__(self, tier=1, mission=None):
        self.tier = tier
        self.map = Map()
        # heroes and monsters
        self.heroes = [Warrior(), Mage()]
        self.mission = mission or random.choice([
            "capture_point",
            "escort",
            "survival",
            "destroy_shrine",
        ])
        # mission specific setup
        self.objective_complete = False
        self.objective_failed = None
        self.objective_progress = 0
        self.objective_required = 0
        self.control_point = None
        self.vip = None
        self.exit_tile = None
        self.survival_rounds = 0
        self.wave_interval = 3
        self.shrine = None

        if self.mission == "escort":
            # add a priest VIP and exit tile
            self.vip = Priest()
            self.heroes.append(self.vip)
            self.exit_tile = (self.map.width - 1, self.map.height - 1)
            tile = self.map.tile(*self.exit_tile)
            tile["terrain"] = "exit"
        if self.mission == "capture_point":
            self.control_point = (self.map.width // 2, self.map.height // 2)
            tile = self.map.tile(*self.control_point)
            tile["terrain"] = "control_point"
            self.objective_required = 3
        if self.mission == "survival":
            self.survival_rounds = 10
            self.objective_required = self.survival_rounds
        if self.mission == "destroy_shrine":
            self.shrine = EnemyShrine(20)
            # place shrine near enemy side
            self.shrine.x = self.map.width - 2
            self.shrine.y = self.map.height // 2
            self.monsters = [self.shrine]
        else:
            self.monsters = self.generate_encounter()

        # place units on the map
        for i, h in enumerate(self.heroes):
            h.x = i % 2
            h.y = i // 2
        if self.mission != "destroy_shrine":
            for i, m in enumerate(self.monsters):
                m.x = self.map.width - 1 - (i % 2)
                m.y = i // 2
                left = max(0, m.x - 4)
                m.patrol_path = [(m.x, m.y), (left, m.y)]

        self.round = 1
        self.taunt_target = None
        self.arena = random.choice([
            "The fight takes place in an abandoned ruin.",
            "A cool breeze sweeps across the battlefield.",
            "Thunder rumbles in the distance.",
        ])
        self.phase = "prebattle"
        self.aggro_radius = 3
        self._opp_tracker = {}
        self._event_gen = self._events()

    # --- encounter generation ----------------------------------------
    def generate_encounter(self):
        archetype = random.choice(["swarm", "elite", "double"])
        mons = []
        if archetype == "swarm":
            mons = [Goblin(), Goblin(), Archer()]
            if random.random() < 0.5:
                mons.append(Shaman())
        elif archetype == "elite":
            front = random.choice([Orc(), Troll()])
            support = random.choice([Priest(), Shaman()])
            mons = [front, support]
        else:  # double wall
            mons = [Orc(), Troll(), random.choice([Shaman(), Priest()])]

        hp_scale = 1 + 0.05 * (self.tier - 1)
        for m in mons:
            m.max_hp = int(m.max_hp * hp_scale)
            m.hp = m.max_hp
            if self.tier % 2 == 1 and isinstance(m, (Goblin, Orc, Archer)):
                m.attack_range = (m.attack_range[0] + 1, m.attack_range[1])
        return mons

    # --- util ----------------------------------------------------------
    def select_target(self, enemies, ignore_taunt=False):
        living = [e for e in enemies if e.is_alive()]
        if not living:
            return None
        if not ignore_taunt and self.taunt_target and self.taunt_target in living:
            return self.taunt_target
        return random.choice(living)

    def distance(self, a, b):
        return abs(a.x - b.x) + abs(a.y - b.y)

    def distance_coords(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def line_of_sight(self, a, b):
        if a.x == b.x:
            step = 1 if b.y > a.y else -1
            for y in range(a.y + step, b.y, step):
                if self.map.tile(a.x, y)["terrain"] == "obstacle":
                    return False
        elif a.y == b.y:
            step = 1 if b.x > a.x else -1
            for x in range(a.x + step, b.x, step):
                if self.map.tile(x, a.y)["terrain"] == "obstacle":
                    return False
        return True

    def find_path(self, start, goal, blocked):
        queue = deque([start])
        came = {start: None}
        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            for nx, ny in self.map.neighbors(*cur):
                if (nx, ny) in blocked and (nx, ny) != goal:
                    continue
                if not self.map.tile(nx, ny)["passable"]:
                    continue
                if (nx, ny) not in came:
                    came[(nx, ny)] = cur
                    queue.append((nx, ny))
        if goal not in came:
            return None
        path = [goal]
        while path[-1] != start:
            path.append(came[path[-1]])
        path.reverse()
        return path

    def _check_zoc(self, mover, from_pos, events, tracker):
        enemies = self.monsters if mover in self.heroes else self.heroes
        for e in enemies:
            if not e.is_alive() or e.range > 1:
                continue
            if self.distance_coords((e.x, e.y), from_pos) == 1:
                if e.name in tracker:
                    continue
                tracker.add(e.name)
                dmg = random.randint(*e.attack_range)
                dmg = int(dmg * e._damage_mod() * 0.5)
                events.append({
                    "type": "opportunity_hit",
                    "attacker_id": e.name,
                    "defender_id": mover.name,
                    "dmg": dmg,
                })
                events.extend(mover.take_damage(dmg))

    def move_unit_towards(self, unit, target):
        start = (unit.x, unit.y)
        blocked = {(c.x, c.y) for c in self.heroes + self.monsters if c.is_alive() and c is not unit}
        path = self.find_path(start, (target.x, target.y), blocked)
        if not path:
            return []
        steps = []
        events = []
        tracker = set()
        for step in path[1:]:
            if len(steps) >= unit.move_points or step == (target.x, target.y):
                break
            from_pos = (unit.x, unit.y)
            tile_from = self.map.tile(*from_pos)
            events.append({"type": "leave_tile", "unit_id": unit.name, "tile": tile_from})
            self._check_zoc(unit, from_pos, events, tracker)
            unit.x, unit.y = step
            steps.append({"x": step[0], "y": step[1]})
            tile = self.map.tile(*step)
            applied = None
            if tile["terrain"] == "hazard_poison":
                unit.poison = 1
                unit.poison_turns = 2
                applied = {"status": "poison", "turns": 2}
                events.append({"type": "status", "status": "poison", "target": unit.name, "turns": 2})
            elif tile["terrain"] == "shrine" and (step in self.map.shrines):
                heal = min(3, unit.max_hp - unit.hp)
                unit.hp += heal
                unit.shield += 2
                self.map.shrines.remove(step)
                tile["terrain"] = "plain"
                applied = {"status": "shrine", "heal": heal, "shield": 2}
                if heal:
                    events.append({"type": "heal", "actor": unit.name, "amount": heal, "hp": unit.hp})
                events.append({"type": "status", "status": "shield", "target": unit.name, "amount": 2, "remaining": unit.shield})
            events.append({"type": "enter_tile", "unit_id": unit.name, "tile": tile, "applied_status": applied})
            events.extend(self._objective_on_move(unit))
        if steps:
            move_ev = {
                "type": "move",
                "unit_id": unit.name,
                "from": {"x": start[0], "y": start[1]},
                "to": {"x": unit.x, "y": unit.y},
                "path": steps,
            }
            return [move_ev] + events
        return []

    def move_unit_to(self, unit, dest):
        start = (unit.x, unit.y)
        blocked = {(c.x, c.y) for c in self.heroes + self.monsters if c.is_alive() and c is not unit}
        path = self.find_path(start, dest, blocked)
        if not path or len(path) < 2:
            return []
        step = path[1]
        steps = []
        events = []
        tracker = set()
        from_pos = start
        tile_from = self.map.tile(*from_pos)
        events.append({"type": "leave_tile", "unit_id": unit.name, "tile": tile_from})
        self._check_zoc(unit, from_pos, events, tracker)
        unit.x, unit.y = step
        steps.append({"x": step[0], "y": step[1]})
        tile = self.map.tile(*step)
        applied = None
        if tile["terrain"] == "hazard_poison":
            unit.poison = 1
            unit.poison_turns = 2
            applied = {"status": "poison", "turns": 2}
            events.append({"type": "status", "status": "poison", "target": unit.name, "turns": 2})
        elif tile["terrain"] == "shrine" and (step in self.map.shrines):
            heal = min(3, unit.max_hp - unit.hp)
            unit.hp += heal
            unit.shield += 2
            self.map.shrines.remove(step)
            tile["terrain"] = "plain"
            applied = {"status": "shrine", "heal": heal, "shield": 2}
            if heal:
                events.append({"type": "heal", "actor": unit.name, "amount": heal, "hp": unit.hp})
            events.append({"type": "status", "status": "shield", "target": unit.name, "amount": 2, "remaining": unit.shield})
        events.append({"type": "enter_tile", "unit_id": unit.name, "tile": tile, "applied_status": applied})
        events.extend(self._objective_on_move(unit))
        move_ev = {
            "type": "move",
            "unit_id": unit.name,
            "from": {"x": start[0], "y": start[1]},
            "to": {"x": unit.x, "y": unit.y},
            "path": steps,
        }
        return [move_ev] + events

    def move_unit_away(self, unit, enemies):
        candidates = []
        for nx, ny in self.map.neighbors(unit.x, unit.y):
            tile = self.map.tile(nx, ny)
            if not tile["passable"]:
                continue
            if any(c.x == nx and c.y == ny and c.is_alive() for c in self.heroes + self.monsters):
                continue
            dist = min(self.distance_coords((nx, ny), (e.x, e.y)) for e in enemies if e.is_alive())
            candidates.append(((nx, ny), dist))
        candidates = [c for c in candidates if c[1] > 1]
        if not candidates:
            return []
        dest, _ = max(candidates, key=lambda x: x[1])
        return self.move_unit_to(unit, dest)

    def kite(self, unit, enemies):
        if unit.range <= 1:
            return []
        if all(self.distance(unit, e) > 1 for e in enemies if e.is_alive()):
            return []
        return self.move_unit_away(unit, enemies)

    def check_aggro(self):
        for h in self.heroes:
            if not h.is_alive():
                continue
            for m in self.monsters:
                if not m.is_alive():
                    continue
                if self.distance(h, m) <= self.aggro_radius and self.line_of_sight(h, m):
                    return h, m
        return None, None

    def patrol_step(self, unit):
        if unit.patrol_path:
            dest = unit.patrol_path[unit._patrol_index]
            if (unit.x, unit.y) == dest:
                unit._patrol_index = (unit._patrol_index + 1) % len(unit.patrol_path)
                dest = unit.patrol_path[unit._patrol_index]
            return dest
        if unit.wander_area:
            x1, y1, x2, y2 = unit.wander_area
            opts = []
            for nx, ny in self.map.neighbors(unit.x, unit.y):
                if not (x1 <= nx <= x2 and y1 <= ny <= y2):
                    continue
                if not self.map.tile(nx, ny)["passable"]:
                    continue
                if any(c.x == nx and c.y == ny and c.is_alive() for c in self.heroes + self.monsters):
                    continue
                opts.append((nx, ny))
            if opts:
                return random.choice(opts)
        return unit.x, unit.y

    def _char_info(self, c):
        return {
            "name": c.name,
            "hp": c.hp,
            "max_hp": c.max_hp,
            "icon": c.icon,
            "x": c.x,
            "y": c.y,
        }

    # --- objective system ---------------------------------------------

    def _objective_init_event(self):
        data = {}
        if self.mission == "capture_point" and self.control_point:
            data = {
                "tiles": [{"x": self.control_point[0], "y": self.control_point[1]}],
                "required": self.objective_required,
            }
        elif self.mission == "escort" and self.vip and self.exit_tile:
            data = {
                "vip": self.vip.name,
                "exit": {"x": self.exit_tile[0], "y": self.exit_tile[1]},
            }
        elif self.mission == "survival":
            data = {"rounds": self.survival_rounds, "wave_interval": self.wave_interval}
        elif self.mission == "destroy_shrine" and self.shrine:
            data = {
                "shrine": {
                    "x": self.shrine.x,
                    "y": self.shrine.y,
                    "hp": self.shrine.hp,
                }
            }
        return {"type": "objective_init", "mission": self.mission, "data": data}

    def _objective_on_move(self, unit):
        events = []
        if self.mission == "escort" and self.vip and unit is self.vip:
            if (unit.x, unit.y) == self.exit_tile:
                self.objective_complete = True
                events.append({"type": "objective_complete", "mission": self.mission})
        return events

    def _objective_process_event(self, ev):
        if self.mission == "escort" and ev.get("type") == "death" and ev.get("target") == (self.vip.name if self.vip else None):
            self.objective_failed = True
            return [{"type": "objective_fail", "mission": self.mission}]
        if self.mission == "destroy_shrine" and self.shrine:
            if ev.get("type") == "damage" and ev.get("target") == self.shrine.name:
                progress = self.shrine.max_hp - self.shrine.hp
                return [{
                    "type": "objective_progress",
                    "mission": self.mission,
                    "progress": progress,
                    "required": self.shrine.max_hp,
                }]
            if ev.get("type") == "death" and ev.get("target") == self.shrine.name:
                self.objective_complete = True
                return [{"type": "objective_complete", "mission": self.mission}]
        return []

    def _objective_round_end(self):
        events = []
        if self.mission == "capture_point" and self.control_point:
            holder = None
            for h in self.heroes:
                if h.is_alive() and (h.x, h.y) == self.control_point:
                    holder = h
                    break
            occupied_by_enemy = any(
                m.is_alive() and (m.x, m.y) == self.control_point for m in self.monsters
            )
            if holder and not occupied_by_enemy:
                self.objective_progress += 1
                events.append({
                    "type": "objective_progress",
                    "mission": self.mission,
                    "holder": holder.name,
                    "progress": self.objective_progress,
                    "required": self.objective_required,
                })
                if self.objective_progress >= self.objective_required:
                    self.objective_complete = True
                    events.append({"type": "objective_complete", "mission": self.mission})
            elif self.objective_progress:
                self.objective_progress = 0
                events.append({
                    "type": "objective_progress",
                    "mission": self.mission,
                    "progress": 0,
                    "required": self.objective_required,
                })
        if self.mission == "survival":
            self.objective_progress += 1
            events.append({
                "type": "objective_progress",
                "mission": self.mission,
                "progress": self.objective_progress,
                "required": self.objective_required,
            })
            if self.objective_progress >= self.objective_required:
                self.objective_complete = True
                events.append({"type": "objective_complete", "mission": self.mission})
            elif self.objective_progress % self.wave_interval == 0:
                # spawn a simple goblin at enemy edge
                g = Goblin()
                g.x = self.map.width - 1
                g.y = random.randrange(self.map.height)
                self.monsters.append(g)
                events.append({
                    "type": "wave_spawn",
                    "round": self.round,
                    "monsters": [self._char_info(g)],
                })
        return events

    # --- event stream --------------------------------------------------
    def _events(self):
        yield {
            "type": "map_init",
            "width": self.map.width,
            "height": self.map.height,
            "tiles": list(self.map.tiles.values()),
        }
        yield {
            "type": "start",
            "arena": self.arena,
            "heroes": [self._char_info(c) for c in self.heroes],
            "monsters": [self._char_info(c) for c in self.monsters],
        }
        yield self._objective_init_event()
        yield {"type": "phase_change", "value": "prebattle"}
        while self.phase == "prebattle":
            moved = False
            for unit in self.heroes + self.monsters:
                if unit.patrol_path or unit.wander_area:
                    dest = self.patrol_step(unit)
                    move_events = self.move_unit_to(unit, dest)
                    if move_events:
                        moved = True
                        mv = move_events[0]
                        yield {
                            "type": "patrol_tick",
                            "unit_id": unit.name,
                            "from": mv["from"],
                            "to": mv["to"],
                        }
            h, m = self.check_aggro()
            if h:
                yield {
                    "type": "aggro_trigger",
                    "source_id": h.name,
                    "target_id": m.name,
                    "radius": self.aggro_radius,
                }
                self.phase = "combat"
                yield {"type": "phase_change", "value": "combat"}
                break
        for c in self.heroes + self.monsters:
            if c.regen:
                yield {"type": "status", "status": "regen", "target": c.name}
        while not self.winner():
            yield from self.step()
        yield {"type": "end", "winner": self.winner()}

    def step(self):
        order = sorted(
            [c for c in self.heroes + self.monsters if c.is_alive()],
            key=lambda c: c.speed,
            reverse=True,
        )
        yield {
            "type": "round",
            "round": self.round,
            "order": [c.name for c in order],
        }
        for actor in order:
            side = self.heroes if actor in self.heroes else self.monsters
            enemies = self.monsters if side is self.heroes else self.heroes
            for ev in actor.begin_turn():
                yield ev
                for oev in self._objective_process_event(ev):
                    yield oev
            if not actor.is_alive() or not enemies:
                continue
            events = actor.take_turn(side, [e for e in enemies if e.is_alive()], self)
            for ev in events:
                yield ev
                for oev in self._objective_process_event(ev):
                    yield oev
                if self.winner():
                    return
            for ev in actor.end_turn():
                yield ev
                for oev in self._objective_process_event(ev):
                    yield oev
                if self.winner():
                    return
            if actor is self.taunt_target and actor is not side:
                self.taunt_target = None
        self.round += 1
        for ev in self._objective_round_end():
            yield ev
            if self.winner():
                return

    def winner(self):
        if self.objective_complete:
            return "Heroes"
        if self.objective_failed:
            return "Monsters"
        if all(not m.is_alive() for m in self.monsters):
            return "Heroes"
        if all(not h.is_alive() for h in self.heroes):
            return "Monsters"
        return None

    def next_event(self):
        try:
            return next(self._event_gen)
        except StopIteration:
            return None

