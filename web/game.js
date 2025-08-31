const heroes = [
  {name: 'Warrior', emoji: '🛡️', hp: 30, maxHp: 30, attack: [4,8], poison:0, poisonTurns:0, shield:0, rage:0},
  {name: 'Mage', emoji: '🪄', hp: 20, maxHp: 20, attack: [5,10], poison:0, poisonTurns:0, shield:0, rage:0}
];
const monsters = [
  {name: 'Goblin', emoji: '👺', hp: 15, maxHp: 15, attack: [3,6], poison:0, poisonTurns:0, shield:0, rage:0},
  {name: 'Orc', emoji: '🪓', hp: 25, maxHp: 25, attack: [2,7], poison:0, poisonTurns:0, shield:0, rage:0}
];

let speed = 1;
let running = true;
let round = 1;
let tauntTarget = null;
let initiativeQueue = [];

const heroesDiv = document.getElementById('heroes');
const monstersDiv = document.getElementById('monsters');
const heroPanel = document.getElementById('hero-panel');
const monsterPanel = document.getElementById('monster-panel');
const logDiv = document.getElementById('log');
const statusDiv = document.getElementById('status');
const effectsSvg = document.getElementById('effects');
const bannerDiv = document.getElementById('winner-banner');
const initiativeDiv = document.getElementById('initiative');

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
  const statuses = document.createElement('div');
  statuses.className = 'statuses';
  div.appendChild(statuses);
  c.dom = {div, hpBar: inner, label, statuses};
  updateChar(c);
  return div;
}

function updateChar(c) {
  c.dom.hpBar.style.width = (c.hp / c.maxHp * 100) + '%';
  c.dom.label.textContent = `${c.hp}/${c.maxHp}`;
  c.dom.statuses.textContent = '';
  if (c.poisonTurns > 0) c.dom.statuses.textContent += '☠️';
  if (c.shield > 0) c.dom.statuses.textContent += '🛡️';
  if (c.rage > 0) c.dom.statuses.textContent += '💢';
}

function updatePanels() {
  heroPanel.textContent = heroes.map(h => `${h.name}: ${h.hp}/${h.maxHp}`).join('\n');
  monsterPanel.textContent = monsters.map(m => `${m.name}: ${m.hp}/${m.maxHp}`).join('\n');
}

function updateInitiative() {
  initiativeDiv.innerHTML = '';
  initiativeQueue.forEach(c => {
    const span = document.createElement('span');
    span.textContent = c.emoji;
    initiativeDiv.appendChild(span);
  });
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

function flash(c, type) {
  c.dom.div.classList.add(type);
  setTimeout(() => c.dom.div.classList.remove(type), 300 / speed);
}

function critText(c) {
  const div = document.createElement('div');
  div.textContent = 'CRIT!';
  div.className = 'crit';
  c.dom.div.appendChild(div);
  setTimeout(() => div.remove(), 600);
}

function die(c) {
  c.dom.div.classList.add('dead');
}

function beginTurn(c) {
  if (c.poisonTurns > 0 && c.hp > 0) {
    c.hp = Math.max(c.hp - c.poison, 0);
    c.poisonTurns--;
    updateChar(c);
    flash(c, 'hit');
    damageNumber(c, c.poison);
    log(`${c.name} suffers ${c.poison} poison. ${c.hp}/${c.maxHp}`);
    if (c.hp <= 0) die(c);
  }
  if (c.rage > 0) c.rage--;
  else if (c.hp > 0 && c.hp <= Math.floor(c.maxHp/3)) {
    c.rage = 3;
    log(`${c.name} enters Rage!`);
  }
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
    let dmg = rand(attacker.attack[0], attacker.attack[1]);
    if (attacker.rage > 0) dmg = Math.floor(dmg * 1.5);
    const crit = Math.random() < 0.2;
    if (crit) dmg *= 2;
    moveForward(attacker.dom.div, attacker.dom.div.parentElement === heroesDiv ? 20 : -20)
    .then(() => {
      lineBetween(attacker, target);
      if (target.rage > 0) dmg = Math.floor(dmg * 1.5);
      if (target.shield > 0) {
        const absorbed = Math.min(target.shield, dmg);
        dmg -= absorbed;
        target.shield -= absorbed;
        if (absorbed) log(`${target.name}'s shield absorbs ${absorbed}.`);
      }
      target.hp = Math.max(target.hp - dmg, 0);
      updateChar(target);
      flash(target, 'hit');
      damageNumber(target, dmg);
      if (crit) critText(target);
      if (Math.random() < 0.1 && target.hp > 0) {
        target.poison = 2;
        target.poisonTurns = 3;
        updateChar(target);
        log(`${target.name} is poisoned!`);
      }
      if (target.hp <= 0) die(target);
      log(`${attacker.name} hits ${target.name} for ${dmg} dmg${crit ? ' (CRIT!)' : ''}. ${target.name} ${target.hp}/${target.maxHp}`);
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
    let msg = `${c.name} heals for ${amt}. ${c.hp}/${c.maxHp}`;
    if (Math.random() < 0.3) {
        const shield = rand(1,3);
        c.shield += shield;
        msg += ` and gains ${shield} shield`;
    }
    updateChar(c);
    flash(c, 'heal');
    damageNumber(c, amt, true);
    log(msg);
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

function showBanner(text) {
  statusDiv.textContent = '';
  bannerDiv.textContent = text;
  bannerDiv.style.display = 'block';
}

async function gameLoop() {
  updatePanels();
  statusDiv.textContent = `Round ${round}`;
  initiativeQueue = [...heroes.filter(h=>h.hp>0), ...monsters.filter(m=>m.hp>0)];
  updateInitiative();
  for (const [side, enemies] of [[heroes, monsters], [monsters, heroes]]) {
    for (const actor of side) {
      if (!actor.hp || !running) await waitWhilePaused();
      if (actor.hp <= 0) { initiativeQueue.shift(); updateInitiative(); continue; }
      beginTurn(actor);
      if (actor.hp <= 0) { initiativeQueue.shift(); updatePanels(); updateInitiative(); await delay(500/speed); continue; }
      const living = enemies.filter(e => e.hp > 0);
      if (!living.length) {
        showBanner(side === heroes ? 'Heroes win!' : 'Monsters win!');
        return;
      }
      let target;
      if (side === monsters && tauntTarget && tauntTarget.hp > 0) target = tauntTarget;
      else target = living[Math.floor(Math.random() * living.length)];
      const r = Math.random();
      if (actor.name === 'Warrior') {
        if (r < 0.2) { tauntTarget = actor; log(`${actor.name} uses Taunt!`); }
        else if (r < 0.9) await attack(actor, target);
        else await heal(actor);
      } else if (actor.name === 'Mage') {
        if (r < 0.2) {
          log(`${actor.name} casts Fireball!`);
          const targets = living.slice().sort(() => 0.5 - Math.random()).slice(0, Math.min(2, living.length));
          for (const t of targets) await attack(actor, t);
        } else if (r < 0.9) await attack(actor, target);
        else await heal(actor);
      } else {
        if (r < 0.8) await attack(actor, target);
        else await heal(actor);
      }
      updatePanels();
      initiativeQueue.shift();
      updateInitiative();
      await delay(500 / speed);
    }
    if (side === monsters) tauntTarget = null;
  }
  round++;
  setTimeout(gameLoop, 10);
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

