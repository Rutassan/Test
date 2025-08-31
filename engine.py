import random

class Character:
    def __init__(self, name, hp, attack_range, icon):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack_range = attack_range
        self.icon = icon
        self.poison = 0
        self.poison_turns = 0
        self.shield = 0
        self.rage = 0

    def is_alive(self):
        return self.hp > 0

    def begin_turn(self):
        events = []
        if self.poison_turns > 0 and self.is_alive():
            self.hp = max(self.hp - self.poison, 0)
            self.poison_turns -= 1
            events.append({
                "type": "damage",
                "target": self.name,
                "amount": self.poison,
                "hp": self.hp,
                "source": "poison"
            })
            if self.hp == 0:
                events.append({"type": "death", "target": self.name})
        if self.rage > 0:
            self.rage -= 1
        elif self.hp and self.hp <= self.max_hp // 3:
            self.rage = 3
            events.append({"type": "status", "status": "rage", "target": self.name})
        return events

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
                    "remaining": self.shield
                })
        self.hp = max(self.hp - dmg, 0)
        events.append({
            "type": "damage",
            "target": self.name,
            "amount": dmg,
            "hp": self.hp
        })
        if self.hp == 0:
            events.append({"type": "death", "target": self.name})
        return events

    def attack(self, other):
        events = []
        dmg = random.randint(*self.attack_range)
        if self.rage > 0:
            dmg = int(dmg * 1.5)
        crit = random.random() < 0.2
        if crit:
            dmg *= 2
        events.append({
            "type": "attack",
            "attacker": self.name,
            "target": other.name,
            "damage": dmg,
            "crit": crit
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
                "turns": 3
            })
        return events

    def heal(self):
        events = []
        amt = random.randint(1, 5)
        self.hp = min(self.hp + amt, self.max_hp)
        events.append({
            "type": "heal",
            "actor": self.name,
            "amount": amt,
            "hp": self.hp
        })
        if random.random() < 0.3:
            shield_amt = random.randint(1, 3)
            self.shield += shield_amt
            events.append({
                "type": "status",
                "status": "shield",
                "target": self.name,
                "amount": shield_amt,
                "remaining": self.shield
            })
        return events

class Game:
    def __init__(self):
        self.heroes = [
            Character("Warrior", 30, (4, 8), "⚔️"),
            Character("Mage", 20, (5, 10), "🧙"),
        ]
        self.monsters = [
            Character("Goblin", 15, (3, 6), "👺"),
            Character("Orc", 25, (2, 7), "👹"),
        ]
        self.round = 1
        self.taunt_target = None
        self.arena = random.choice([
            "The fight takes place in an abandoned ruin.",
            "A cool breeze sweeps across the battlefield.",
            "Thunder rumbles in the distance." 
        ])
        self._event_gen = self._events()

    def _char_info(self, c):
        return {
            "name": c.name,
            "hp": c.hp,
            "max_hp": c.max_hp,
            "icon": c.icon,
        }

    def _events(self):
        yield {
            "type": "start",
            "arena": self.arena,
            "heroes": [self._char_info(c) for c in self.heroes],
            "monsters": [self._char_info(c) for c in self.monsters],
        }
        while not self.winner():
            yield from self.step()
        yield {"type": "end", "winner": self.winner()}

    def step(self):
        yield {
            "type": "round",
            "round": self.round,
            "order": [c.name for c in self.heroes + self.monsters if c.is_alive()],
        }
        for side, enemies in ((self.heroes, self.monsters), (self.monsters, self.heroes)):
            for actor in side:
                if not actor.is_alive():
                    continue
                for ev in actor.begin_turn():
                    yield ev
                if not actor.is_alive():
                    continue
                living_enemies = [e for e in enemies if e.is_alive()]
                if not living_enemies:
                    return
                target = None
                if side is self.monsters and self.taunt_target and self.taunt_target.is_alive():
                    target = self.taunt_target
                else:
                    target = random.choice(living_enemies)
                r = random.random()
                if actor.name == "Warrior":
                    if r < 0.2:
                        self.taunt_target = actor
                        yield {"type": "status", "status": "taunt", "actor": actor.name}
                    elif r < 0.9:
                        for ev in actor.attack(target):
                            yield ev
                    else:
                        for ev in actor.heal():
                            yield ev
                elif actor.name == "Mage":
                    if r < 0.2:
                        yield {"type": "status", "status": "fireball", "actor": actor.name}
                        targets = random.sample(living_enemies, min(2, len(living_enemies)))
                        for t in targets:
                            for ev in actor.attack(t):
                                yield ev
                    elif r < 0.9:
                        for ev in actor.attack(target):
                            yield ev
                    else:
                        for ev in actor.heal():
                            yield ev
                else:
                    if r < 0.8:
                        for ev in actor.attack(target):
                            yield ev
                    else:
                        for ev in actor.heal():
                            yield ev
                if self.winner():
                    return
            if side is self.monsters:
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
