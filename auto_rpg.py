import random
import time

class Character:
    def __init__(self, name, hp, attack_range):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack_range = attack_range
        # status values
        self.poison = 0         # damage per turn
        self.poison_turns = 0   # turns remaining
        self.shield = 0         # damage absorbed before HP
        self.rage = 0           # turns remaining of increased dmg/taken

    def is_alive(self):
        return self.hp > 0

    def begin_turn(self):
        """Apply status effects at the start of the turn."""
        if self.poison_turns > 0 and self.is_alive():
            self.hp = max(self.hp - self.poison, 0)
            self.poison_turns -= 1
            print(f"{self.name} suffers {self.poison} poison damage. {self.hp}/{self.max_hp} HP left.")
        if self.rage > 0:
            self.rage -= 1
        elif self.hp and self.hp <= self.max_hp // 3:
            self.rage = 3
            print(f"{self.name} is enraged!")

    def take_damage(self, dmg):
        if self.rage > 0:
            dmg = int(dmg * 1.5)
        if self.shield > 0:
            absorbed = min(self.shield, dmg)
            dmg -= absorbed
            self.shield -= absorbed
            if absorbed:
                print(f"{self.name}'s shield absorbs {absorbed} damage.")
        self.hp = max(self.hp - dmg, 0)

    def attack(self, other):
        dmg = random.randint(*self.attack_range)
        if self.rage > 0:
            dmg = int(dmg * 1.5)
        other.take_damage(dmg)
        print(f"{self.name} hits {other.name} for {dmg} damage. {other.name} has {other.hp}/{other.max_hp} HP left.")
        # 10% chance to poison
        if random.random() < 0.1 and other.is_alive():
            other.poison = 2
            other.poison_turns = 3
            print(f"{other.name} is poisoned!")

    def heal(self):
        amt = random.randint(1, 5)
        self.hp = min(self.hp + amt, self.max_hp)
        msg = f"{self.name} heals for {amt} HP. {self.hp}/{self.max_hp} HP now."
        # 30% chance to gain a small shield when healing
        if random.random() < 0.3:
            shield_amt = random.randint(1, 3)
            self.shield += shield_amt
            msg += f" Gains a {shield_amt} shield."
        print(msg)

class Game:
    def __init__(self):
        self.heroes = [
            Character("Warrior", 30, (4, 8)),
            Character("Mage", 20, (5, 10)),
        ]
        self.monsters = [
            Character("Goblin", 15, (3, 6)),
            Character("Orc", 25, (2, 7)),
        ]
        self.round = 1
        self.taunt_target = None

    def step(self):
        print(f"\n-- Round {self.round} --")
        for side, enemies in ((self.heroes, self.monsters), (self.monsters, self.heroes)):
            for actor in side:
                if not actor.is_alive():
                    continue
                actor.begin_turn()
                if not actor.is_alive():
                    continue
                living_enemies = [e for e in enemies if e.is_alive()]
                if not living_enemies:
                    return
                # handle taunt when monsters choose targets
                target = None
                if side is self.monsters and self.taunt_target and self.taunt_target.is_alive():
                    target = self.taunt_target
                else:
                    target = random.choice(living_enemies)

                r = random.random()
                if actor.name == "Warrior":
                    if r < 0.2:
                        self.taunt_target = actor
                        print(f"{actor.name} uses Taunt! Enemies will attack him.")
                    elif r < 0.9:
                        actor.attack(target)
                    else:
                        actor.heal()
                elif actor.name == "Mage":
                    if r < 0.2:
                        print(f"{actor.name} casts Fireball!")
                        targets = random.sample(living_enemies, min(2, len(living_enemies)))
                        for t in targets:
                            actor.attack(t)
                    elif r < 0.9:
                        actor.attack(target)
                    else:
                        actor.heal()
                else:
                    if r < 0.8:
                        actor.attack(target)
                    else:
                        actor.heal()
                time.sleep(0.3)
            # reset taunt after monsters finish their turn
            if side is self.monsters:
                self.taunt_target = None
        self.round += 1

    def winner(self):
        if all(not m.is_alive() for m in self.monsters):
            return "Heroes"
        if all(not h.is_alive() for h in self.heroes):
            return "Monsters"
        return None

    def play(self):
        print("A battle begins! Heroes vs Monsters. Sit back and watch...\n")
        while not self.winner():
            self.step()
        print(f"\n{self.winner()} win the day!")

if __name__ == "__main__":
    Game().play()
