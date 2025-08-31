import random


class Character:
    """Base character with combat utilities and status management."""

    def __init__(self, name, hp, attack_range, icon, speed=1, crit=0.2):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack_range = attack_range
        self.icon = icon
        self.base_speed = speed
        self.base_crit = crit

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
        """Default behaviour: attack most of the time."""
        if not enemies:
            return []
        target = random.choice(enemies)
        if random.random() < 0.8:
            return self.attack(target)
        return self.heal_self()


# --- Hero classes -------------------------------------------------------


class Warrior(Character):
    def __init__(self):
        super().__init__("Warrior", 30, (4, 8), "⚔️", speed=2)

    def take_turn(self, allies, enemies, game):
        if not enemies:
            return []
        r = random.random()
        if r < 0.2:
            game.taunt_target = self
            return [{"type": "status", "status": "taunt", "actor": self.name}]
        elif r < 0.9:
            target = game.select_target(enemies)
            return self.attack(target)
        else:
            return self.heal_self()


class Mage(Character):
    def __init__(self):
        super().__init__("Mage", 20, (5, 10), "🧙", speed=2)

    def take_turn(self, allies, enemies, game):
        if not enemies:
            return []
        r = random.random()
        if r < 0.2 and len(enemies) > 1:
            events = [{"type": "status", "status": "fireball", "actor": self.name}]
            targets = random.sample(enemies, 2)
            for t in targets:
                events.extend(self.attack(t))
            return events
        elif r < 0.9:
            target = game.select_target(enemies)
            return self.attack(target)
        else:
            return self.heal_self()


# --- Monster classes ----------------------------------------------------


class Goblin(Character):
    def __init__(self):
        super().__init__("Goblin", 15, (3, 6), "👺", speed=2)


class Orc(Character):
    def __init__(self):
        super().__init__("Orc", 25, (2, 7), "👹", speed=1)


class Archer(Character):
    def __init__(self):
        super().__init__("Archer", 18, (4, 7), "🏹", speed=3, crit=0.25)

    def take_turn(self, allies, enemies, game):
        if not enemies:
            return []
        if self.aim == 0 and random.random() < 0.3:
            self.aim = 1
            return [{"type": "status", "status": "aim", "actor": self.name, "turns": 1}]
        target = game.select_target(enemies, ignore_taunt=self.aim)
        events = self.attack(target)
        return events


class Priest(Character):
    def __init__(self):
        super().__init__("Priest", 18, (1, 4), "⛪", speed=2)

    def take_turn(self, allies, enemies, game):
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
            return self.attack(game.select_target(enemies))
        return []


class Troll(Character):
    def __init__(self):
        super().__init__("Troll", 40, (3, 7), "🧌", speed=1)
        self.regen = 2


class Shaman(Character):
    def __init__(self):
        super().__init__("Shaman", 20, (2, 5), "🌀", speed=2)

    def take_turn(self, allies, enemies, game):
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
            target.hexed = 1
            return [{
                "type": "status",
                "status": "hex",
                "target": target.name,
                "turns": 1,
                "actor": self.name,
            }]
        if enemies:
            return self.attack(game.select_target(enemies))
        return []


# --- Game engine --------------------------------------------------------


class Game:
    def __init__(self, tier=1):
        self.tier = tier
        self.heroes = [Warrior(), Mage()]
        self.monsters = self.generate_encounter()
        self.round = 1
        self.taunt_target = None
        self.arena = random.choice([
            "The fight takes place in an abandoned ruin.",
            "A cool breeze sweeps across the battlefield.",
            "Thunder rumbles in the distance.",
        ])
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

    def _char_info(self, c):
        return {
            "name": c.name,
            "hp": c.hp,
            "max_hp": c.max_hp,
            "icon": c.icon,
        }

    # --- event stream --------------------------------------------------
    def _events(self):
        yield {
            "type": "start",
            "arena": self.arena,
            "heroes": [self._char_info(c) for c in self.heroes],
            "monsters": [self._char_info(c) for c in self.monsters],
        }
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
            if not actor.is_alive() or not enemies:
                continue
            events = actor.take_turn(side, [e for e in enemies if e.is_alive()], self)
            for ev in events:
                yield ev
                if self.winner():
                    return
            for ev in actor.end_turn():
                yield ev
            if self.winner():
                return
            if actor is self.taunt_target and actor is not side:
                self.taunt_target = None
        self.round += 1

    def winner(self):
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

