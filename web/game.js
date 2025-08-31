const heroes = [
  {name: 'Warrior', emoji: '🛡️', hp: 30, maxHp: 30, attack: [4,8]},
  {name: 'Mage', emoji: '🪄', hp: 20, maxHp: 20, attack: [5,10]}
];
const monsters = [
  {name: 'Goblin', emoji: '👺', hp: 15, maxHp: 15, attack: [3,6]},
  {name: 'Orc', emoji: '🪓', hp: 25, maxHp: 25, attack: [2,7]}
];

let speed = 1;
let running = true;
let round = 1;

const heroesDiv = document.getElementById('heroes');
const monstersDiv = document.getElementById('monsters');
const heroPanel = document.getElementById('hero-panel');
const monsterPanel = document.getElementById('monster-panel');
const logDiv = document.getElementById('log');
const statusDiv = document.getElementById('status');
const effectsSvg = document.getElementById('effects');

document.getElementById('play-pause').onclick = () => {
  running = !running;
  document.getElementById('play-pause').textContent = running ? 'Pause' : 'Play';
};
document.getElementById('restart').onclick = () => location.reload();
document.getElementById('speed').oninput = e => {
  speed = parseFloat(e.target.value);
};

function createCharElem(c) {
  const div = document.createElement('div');
  div.className = 'character';
  const icon = document.createElement('span');
  icon.className = 'icon';
  icon.textContent = c.emoji;
  div.appendChild(icon);
  const hpBar = document.createElement('div');
  hpBar.className = 'hp-bar';
  const inner = document.createElement('div');
  inner.className = 'hp-bar-inner';
  hpBar.appendChild(inner);
  div.appendChild(hpBar);
  const label = document.createElement('div');
  label.className = 'hp-label';
  div.appendChild(label);
  c.dom = {div, hpBar: inner, label};
  updateChar(c);
  return div;
}

function updateChar(c) {
  c.dom.hpBar.style.width = (c.hp / c.maxHp * 100) + '%';
  c.dom.label.textContent = `${c.hp}/${c.maxHp}`;
}

function updatePanels() {
  heroPanel.textContent = heroes.map(h => `${h.name}: ${h.hp}/${h.maxHp}`).join('\n');
  monsterPanel.textContent = monsters.map(m => `${m.name}: ${m.hp}/${m.maxHp}`).join('\n');
}

function log(msg) {
  const entry = document.createElement('div');
  entry.textContent = msg;
  entry.className = 'log-entry';
  logDiv.appendChild(entry);
  if (logDiv.childNodes.length > 6) logDiv.removeChild(logDiv.firstChild);
  logDiv.scrollTop = logDiv.scrollHeight;
}

function damageNumber(c, amount, heal=false) {
  const div = document.createElement('div');
  div.textContent = amount;
  div.className = 'damage';
  if (heal) div.classList.add('heal');
  c.dom.div.appendChild(div);
  setTimeout(() => div.remove(), 1000);
}

function lineBetween(a,b) {
  const rectA = a.dom.div.getBoundingClientRect();
  const rectB = b.dom.div.getBoundingClientRect();
  const svgRect = effectsSvg.getBoundingClientRect();
  const line = document.createElementNS('http://www.w3.org/2000/svg','line');
  line.setAttribute('x1', rectA.left + rectA.width/2 - svgRect.left);
  line.setAttribute('y1', rectA.top + rectA.height/2 - svgRect.top);
  line.setAttribute('x2', rectB.left + rectB.width/2 - svgRect.left);
  line.setAttribute('y2', rectB.top + rectB.height/2 - svgRect.top);
  line.classList.add('attack-line');
  effectsSvg.appendChild(line);
  setTimeout(() => line.remove(), 300);
}

function attack(attacker, target) {
  return new Promise(resolve => {
    attacker.dom.div.classList.add('active');
    const dmg = rand(attacker.attack[0], attacker.attack[1]);
    moveForward(attacker.dom.div, attacker.dom.div.parentElement === heroesDiv ? 20 : -20)
    .then(() => {
      lineBetween(attacker, target);
      target.hp = Math.max(target.hp - dmg, 0);
      updateChar(target);
      damageNumber(target, dmg);
      log(`${attacker.name} hits ${target.name} for ${dmg} dmg. ${target.name} ${target.hp}/${target.maxHp}`);
      setTimeout(() => {
        attacker.dom.div.classList.remove('active');
        moveForward(attacker.dom.div, 0).then(resolve);
      }, 300 / speed);
    });
  });
}

function heal(c) {
  return new Promise(resolve => {
    c.dom.div.classList.add('active');
    const amt = rand(1,5);
    c.hp = Math.min(c.hp + amt, c.maxHp);
    updateChar(c);
    damageNumber(c, amt, true);
    log(`${c.name} heals for ${amt}. ${c.hp}/${c.maxHp}`);
    setTimeout(() => {
      c.dom.div.classList.remove('active');
      resolve();
    }, 300 / speed);
  });
}

function rand(a,b) { return Math.floor(Math.random()*(b-a+1))+a; }

function moveForward(elem, distance) {
  return new Promise(res => {
    elem.style.transform = `translateX(${distance}px)`;
    setTimeout(res, 300 / speed);
  });
}

async function gameLoop() {
  updatePanels();
  statusDiv.textContent = `Round ${round}`;
  for (const [side, enemies] of [[heroes, monsters], [monsters, heroes]]) {
    for (const actor of side) {
      if (!actor.hp || !running) await waitWhilePaused();
      if (actor.hp <= 0) continue;
      const living = enemies.filter(e => e.hp > 0);
      if (!living.length) return;
      const target = living[Math.floor(Math.random() * living.length)];
      if (Math.random() < 0.8) await attack(actor, target);
      else await heal(actor);
      updatePanels();
      await delay(500 / speed);
    }
  }
  round++;
  if (heroes.every(h => h.hp <= 0)) statusDiv.textContent = 'Monsters win!';
  else if (monsters.every(m => m.hp <= 0)) statusDiv.textContent = 'Heroes win!';
  else setTimeout(gameLoop, 10);
}

function waitWhilePaused() {
  return new Promise(r => {
    (function check() {
      if (running) r(); else setTimeout(check, 100);
    })();
  });
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

function init() {
  heroes.forEach(h => heroesDiv.appendChild(createCharElem(h)));
  monsters.forEach(m => monstersDiv.appendChild(createCharElem(m)));
  gameLoop();
}
init();

