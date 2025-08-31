import random
import time

class Character:
    def __init__(self, name, hp, attack_range):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack_range = attack_range

    def is_alive(self):
        return self.hp > 0

    def attack(self, other):
        dmg = random.randint(*self.attack_range)
        other.hp = max(other.hp - dmg, 0)
        print(f"{self.name} hits {other.name} for {dmg} damage. {other.name} has {other.hp}/{other.max_hp} HP left.")

    def heal(self):
        amt = random.randint(1, 5)
        self.hp = min(self.hp + amt, self.max_hp)
        print(f"{self.name} heals for {amt} HP. {self.hp}/{self.max_hp} HP now.")

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

    def step(self):
        print(f"\n-- Round {self.round} --")
        for side, enemies in ((self.heroes, self.monsters), (self.monsters, self.heroes)):
            for actor in side:
                if not actor.is_alive():
                    continue
                living_enemies = [e for e in enemies if e.is_alive()]
                if not living_enemies:
                    return
                target = random.choice(living_enemies)
                if random.random() < 0.8:
                    actor.attack(target)
                else:
                    actor.heal()
                time.sleep(0.3)
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
