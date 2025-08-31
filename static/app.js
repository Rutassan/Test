const mapEl = document.getElementById('map');
const toggleGridBtn = document.getElementById('toggle-grid');
const logEl = document.getElementById('log');
const roundEl = document.getElementById('round');
const initEl = document.getElementById('initiative');

let timer = null;
let speed = 1;
const characters = {};
let initiative = [];
let fireball = null;
let currentRunId = null;
let nextAbortController = null;
let state = 'idle'; // idle, running, paused, finished
const playBtn = document.getElementById('play');
const pauseBtn = document.getElementById('pause');
pauseBtn.disabled = true;

const TILE_SIZE = 64;
let mapWidth = 0;
let mapHeight = 0;
const tiles = {};
let movedActor = null;

function log(msg, cls = '') {
  const div = document.createElement('div');
  div.textContent = msg;
  if (cls) div.className = cls;
  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;
}

function showAbilityBanner(text = 'Special Ability!') {
  const banner = document.createElement('div');
  banner.className = 'ability-banner';
  banner.textContent = text;
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 1000);
}

function renderInitiative() {
  initEl.innerHTML = '';
  initiative.forEach((n, i) => {
    const div = document.createElement('div');
    div.className = 'turn' + (i === 0 ? ' active' : '');
    div.textContent = characters[n].icon;
    initEl.appendChild(div);
  });
}

function renderMap(width, height, tileData) {
  mapWidth = width;
  mapHeight = height;
  mapEl.innerHTML = '';
  mapEl.style.gridTemplateColumns = `repeat(${width}, ${TILE_SIZE}px)`;
  mapEl.style.gridTemplateRows = `repeat(${height}, ${TILE_SIZE}px)`;
  tileData.forEach(t => {
    tiles[`${t.x},${t.y}`] = t;
    const div = document.createElement('div');
    div.className = `tile ${t.terrain}`;
    div.id = `tile-${t.x}-${t.y}`;
    let symbol = '.';
    if (t.terrain === 'obstacle') symbol = '■';
    else if (t.terrain === 'hazard_poison') symbol = '☠';
    else if (t.terrain === 'shrine') symbol = '✚';
    div.textContent = symbol;
    mapEl.appendChild(div);
  });
}

function setupChars(chars) {
  chars.forEach(c => {
    characters[c.name] = { ...c, statuses: {} };
    const div = document.createElement('div');
    div.className = 'char';
    div.id = 'char-' + c.name;
    div.innerHTML = `<div class="icon">${c.icon}</div><div class="hp-bar"><div class="hp"></div></div><div class="status-icons"></div>`;
    mapEl.appendChild(div);
    placeChar(c.name, c.x, c.y);
    updateHp(c.name, c.hp);
    updateStatuses(c.name);
  });
}

function placeChar(name, x, y) {
  const el = document.getElementById('char-' + name);
  el.style.left = (x * TILE_SIZE) + 'px';
  el.style.top = (y * TILE_SIZE) + 'px';
  characters[name].x = x;
  characters[name].y = y;
}

function animateMove(name, path) {
  let i = 0;
  function step() {
    if (i >= path.length) return;
    const pos = path[i];
    placeChar(name, pos.x, pos.y);
    i++;
    if (i < path.length) {
      setTimeout(step, 300 / speed);
    }
  }
  step();
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

function updateStatuses(name) {
  const st = characters[name].statuses;
  const div = document.querySelector(`#char-${name} .status-icons`);
  let html = '';
  if (st.poison) html += '<span class="poison">☠️</span>';
  if (st.shield) html += '<span class="shield">🛡️</span>';
  if (st.rage) html += '<span class="rage">🔥</span>';
  if (st.taunt) html += '<span class="taunt">🛡️</span>';
  if (st.aim) html += '<span class="aim">🎯</span>';
  if (st.frenzy) html += '<span class="frenzy">⚡</span>';
  if (st.hex) html += '<span class="hex">🌀</span>';
  if (st.regen) html += '<span class="regen">♻️</span>';
  div.innerHTML = html;
  const charDiv = document.getElementById('char-' + name);
  if (st.shield) charDiv.classList.add('has-shield'); else charDiv.classList.remove('has-shield');
}

function flash(name) {
  const el = document.getElementById('char-' + name);
  el.classList.add('flash');
  setTimeout(() => el.classList.remove('flash'), 300);
}

function shiftInitiative(name) {
  if (initiative[0] === name) {
    initiative.shift();
    const st = characters[name].statuses;
    if (st.rage) {
      st.rage--;
      if (st.rage <= 0) delete st.rage;
    }
    if (st.aim) {
      st.aim--;
      if (st.aim <= 0) delete st.aim;
    }
    if (st.frenzy) {
      st.frenzy--;
      if (st.frenzy <= 0) delete st.frenzy;
    }
    if (st.hex) {
      st.hex--;
      if (st.hex <= 0) delete st.hex;
    }
    updateStatuses(name);
    renderInitiative();
  }
}

function handleEvent(ev) {
  if (!ev || (ev.runId && ev.runId !== currentRunId)) return;
  const actor = ev.attacker || ev.actor || ev.unit_id;
  if (movedActor && actor !== movedActor) {
    shiftInitiative(movedActor);
    movedActor = null;
  } else if (movedActor && !actor) {
    shiftInitiative(movedActor);
    movedActor = null;
  }
  switch (ev.type) {
    case 'map_init':
      renderMap(ev.width, ev.height, ev.tiles);
      break;
    case 'start':
      setupChars(ev.heroes.concat(ev.monsters));
      log(ev.arena);
      break;
    case 'round':
      roundEl.textContent = ev.round;
      log('Round ' + ev.round);
      initiative = ev.order.slice();
      Object.keys(characters).forEach(n => { delete characters[n].statuses.taunt; updateStatuses(n); });
      renderInitiative();
      break;
    case 'move':
      log(`${ev.unit_id} moves from (${ev.from.x},${ev.from.y}) → (${ev.to.x},${ev.to.y})`);
      animateMove(ev.unit_id, ev.path);
      movedActor = ev.unit_id;
      break;
    case 'enter_tile': {
      const tile = ev.tile;
      const el = document.getElementById('char-' + ev.unit_id);
      if (ev.applied_status && ev.applied_status.status === 'poison') {
        el.classList.add('trap');
        setTimeout(() => el.classList.remove('trap'), 300);
        log(`${ev.unit_id} steps on hazard: Poison applied!`, 'log-damage');
      } else if (ev.applied_status && ev.applied_status.status === 'shrine') {
        el.classList.add('shrine');
        const sh = document.createElement('div');
        sh.className = 'shield-effect';
        sh.textContent = '🛡️';
        el.appendChild(sh);
        setTimeout(() => el.classList.remove('shrine'), 300);
        const heal = ev.applied_status.heal || 0;
        const shield = ev.applied_status.shield || 0;
        log(`${ev.unit_id} enters shrine: +${heal} HP, +${shield} shield`, 'log-heal');
        const tileEl = document.getElementById(`tile-${tile.x}-${tile.y}`);
        if (tileEl) { tileEl.className = 'tile plain'; tileEl.textContent = '.'; }
      }
      break;
    }
    case 'attack':
      log(`${ev.attacker} hits ${ev.target} for ${ev.damage}${ev.crit ? ' (crit!)' : ''}`, 'log-damage');
      if (fireball && fireball.actor === ev.attacker) {
        flash(ev.target);
        fireball.remaining--;
        if (fireball.remaining <= 0) {
          shiftInitiative(ev.attacker);
          fireball = null;
        }
      } else {
        shiftInitiative(ev.attacker);
      }
      movedActor = null;
      break;
    case 'damage':
      updateHp(ev.target, ev.hp);
      if (ev.source === 'poison') {
        log(`${ev.target} takes ${ev.amount} poison damage`, 'log-damage');
        const st = characters[ev.target].statuses;
        if (st.poison) {
          st.poison--;
          if (st.poison <= 0) delete st.poison;
          updateStatuses(ev.target);
        }
      }
      break;
    case 'heal':
      const tgt = ev.target || ev.actor;
      updateHp(tgt, ev.hp);
      if (ev.target && ev.target !== ev.actor) {
        log(`${ev.actor} heals ${ev.target} for ${ev.amount}`, 'log-heal');
      } else {
        log(`${ev.actor} heals ${ev.amount}`, 'log-heal');
      }
      shiftInitiative(ev.actor);
      movedActor = null;
      break;
    case 'status': {
      const name = ev.target || ev.actor;
      switch (ev.status) {
        case 'poison':
          characters[name].statuses.poison = ev.turns;
          updateStatuses(name);
          log(`${name} is poisoned`, 'log-damage');
          break;
        case 'shield':
          characters[name].statuses.shield = ev.remaining;
          updateStatuses(name);
          log(`${name} gains a shield`, 'log-heal');
          break;
        case 'rage':
          characters[name].statuses.rage = 3;
          updateStatuses(name);
          log(`${name} is enraged!`, 'log-damage');
          break;
        case 'taunt':
          characters[ev.actor].statuses.taunt = 1;
          updateStatuses(ev.actor);
          log(`${ev.actor} uses Taunt!`);
          showAbilityBanner();
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'fireball':
          log(`${ev.actor} casts Fireball!`, 'log-damage');
          showAbilityBanner();
          fireball = { actor: ev.actor, remaining: 2 };
          break;
        case 'aim':
          characters[name].statuses.aim = ev.turns || 1;
          updateStatuses(name);
          log(`${name} takes aim`, 'log-buff');
          showAbilityBanner('Archer aims...');
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'frenzy':
          characters[name].statuses.frenzy = ev.turns;
          updateStatuses(name);
          log(`${name} is frenzied`, 'log-buff');
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'hex':
          characters[name].statuses.hex = ev.turns;
          updateStatuses(name);
          log(`${name} is hexed`, 'log-debuff');
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'regen':
          characters[name].statuses.regen = 1;
          updateStatuses(name);
          break;
      }
      break;
    }
    case 'shield':
      if (ev.remaining > 0) {
        characters[ev.target].statuses.shield = ev.remaining;
      } else {
        delete characters[ev.target].statuses.shield;
      }
      updateStatuses(ev.target);
      break;
    case 'death':
      log(`${ev.target} dies`, 'log-death');
      const d = document.getElementById('char-' + ev.target);
      if (d) { d.style.transition = 'opacity 0.5s'; d.style.opacity = '0'; setTimeout(() => d.remove(), 500); }
      break;
    case 'passive_tick':
      if (ev.status === 'regen') {
        updateHp(ev.target, ev.hp);
        log(`${ev.target} regenerates ${ev.amount}`, 'log-heal');
      }
      break;
    case 'end':
      log(`${ev.winner} win!`);
      const banner = document.createElement('div');
      banner.id = 'banner';
      banner.textContent = `${ev.winner} win!`;
      document.body.appendChild(banner);
      pause();
      state = 'finished';
      break;
  }
}

function fetchNext() {
  if (!currentRunId || state !== 'running') return;
  nextAbortController = new AbortController();
  fetch('/next?runId=' + encodeURIComponent(currentRunId), { signal: nextAbortController.signal })
    .then(r => r.json())
    .then(ev => {
      if (state !== 'running' || !ev || ev.runId !== currentRunId) return;
      handleEvent(ev);
    })
    .catch(() => {});
}

function start(auto = true) {
  if (nextAbortController) nextAbortController.abort();
  fetch('/start').then(r => r.json()).then(ev => {
    if (!ev) return;
    currentRunId = ev.runId;
    logEl.innerHTML = '';
    roundEl.textContent = '1';
    initiative = [];
    fireball = null;
    for (const k in characters) delete characters[k];
    movedActor = null;
    document.getElementById('banner')?.remove();
    if (!auto) {
      speed = 1;
      document.getElementById('speed').value = '1';
    }
    handleEvent(ev);
    if (auto) {
      resume();
    } else {
      state = 'paused';
      playBtn.disabled = false;
      pauseBtn.disabled = true;
    }
  });
}

function resume() {
  if (!currentRunId) return;
  if (timer) clearInterval(timer);
  timer = setInterval(fetchNext, 1000 / speed);
  state = 'running';
  playBtn.disabled = true;
  pauseBtn.disabled = false;
  fetchNext();
}

function pause() {
  if (timer) clearInterval(timer);
  timer = null;
  if (nextAbortController) nextAbortController.abort();
  state = 'paused';
  pauseBtn.disabled = true;
  playBtn.disabled = false;
}

function restart() {
  pause();
  if (nextAbortController) nextAbortController.abort();
  start(false);
}

function setSpeed(s) {
  speed = Number(s);
  if (timer) resume();
}
function play() {
  if (state === 'idle' || state === 'finished') {
    start();
  } else if (state === 'paused') {
    resume();
  }
}

function debounceButton(btn, computeDisabled) {
  btn.disabled = true;
  setTimeout(() => { btn.disabled = computeDisabled(); }, 300);
}

playBtn.addEventListener('click', () => {
  if (playBtn.disabled) return;
  debounceButton(playBtn, () => state === 'running');
  play();
});

pauseBtn.addEventListener('click', () => {
  if (pauseBtn.disabled) return;
  debounceButton(pauseBtn, () => state !== 'running');
  pause();
});

document.getElementById('restart').addEventListener('click', restart);
document.getElementById('speed').addEventListener('change', e => setSpeed(e.target.value));
toggleGridBtn.addEventListener('click', () => {
  mapEl.classList.toggle('no-grid');
});
