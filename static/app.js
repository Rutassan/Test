const heroesEl = document.getElementById('heroes');
const monstersEl = document.getElementById('monsters');
const logEl = document.getElementById('log');
const roundEl = document.getElementById('round');
let timer = null;
let speed = 1;
const characters = {};

function log(msg) {
  const div = document.createElement('div');
  div.textContent = msg;
  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;
}

function setup(sideEl, chars) {
  sideEl.innerHTML = '';
  chars.forEach(c => {
    characters[c.name] = c;
    const div = document.createElement('div');
    div.className = 'char';
    div.id = 'char-' + c.name;
    div.innerHTML = `<div class="icon">${c.icon}</div><div>${c.name}</div><div class="hp-bar"><div class="hp"></div></div>`;
    sideEl.appendChild(div);
    updateHp(c.name, c.hp);
  });
}

function updateHp(name, hp) {
  const bar = document.querySelector(`#char-${name} .hp`);
  const max = characters[name].max_hp;
  bar.style.width = (hp / max * 100) + '%';
  characters[name].hp = hp;
  if (hp <= 0) {
    document.getElementById('char-' + name).classList.add('dead');
  }
}

function handleEvent(ev) {
  if (!ev) return;
  switch (ev.type) {
    case 'start':
      setup(heroesEl, ev.heroes);
      setup(monstersEl, ev.monsters);
      log('Battle begins in ' + ev.arena);
      break;
    case 'round':
      roundEl.textContent = ev.round;
      log('Round ' + ev.round);
      break;
    case 'attack':
      log(`${ev.attacker} hits ${ev.target} for ${ev.damage}${ev.crit ? ' (crit!)' : ''}`);
      break;
    case 'damage':
      updateHp(ev.target, ev.hp);
      break;
    case 'heal':
      updateHp(ev.actor, ev.hp);
      log(`${ev.actor} heals ${ev.amount}`);
      break;
    case 'status':
      log(`${ev.target || ev.actor} gains ${ev.status}`);
      break;
    case 'death':
      log(`${ev.target} dies`);
      break;
    case 'end':
      log(`${ev.winner} win!`);
      const banner = document.createElement('div');
      banner.id = 'banner';
      banner.textContent = `${ev.winner} win!`;
      document.body.appendChild(banner);
      break;
  }
}

function fetchNext() {
  fetch('/next').then(r => r.json()).then(ev => {
    if (!ev || !ev.type) { pause(); return; }
    handleEvent(ev);
    if (ev.type === 'end') pause();
  });
}

function start() {
  fetch('/start').then(r => r.json()).then(ev => {
    logEl.innerHTML = '';
    roundEl.textContent = '0';
    handleEvent(ev);
    resume();
  });
}

function resume() {
  if (timer) clearInterval(timer);
  timer = setInterval(fetchNext, 1000 / speed);
}

function pause() {
  if (timer) clearInterval(timer);
  timer = null;
}

function restart() {
  pause();
  start();
}

function setSpeed(s) {
  speed = Number(s);
  if (timer) resume();
}

document.getElementById('play').addEventListener('click', start);
document.getElementById('pause').addEventListener('click', pause);
document.getElementById('restart').addEventListener('click', restart);
document.getElementById('speed').addEventListener('change', e => setSpeed(e.target.value));
