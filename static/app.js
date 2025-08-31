const mapEl = document.getElementById('map');
const toggleGridBtn = document.getElementById('toggle-grid');
const logEl = document.getElementById('log');
const roundLabel = document.getElementById('round-label');
const heroesBanner = document.getElementById('heroes-banner');
const monstersBanner = document.getElementById('monsters-banner');
const missionTitle = document.getElementById('mission-title');
const missionDesc = document.getElementById('mission-desc');
const missionProgress = document.getElementById('mission-progress');
let lang = 'ru';
let strings = {};
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

let totalHeroes = 0;
let totalMonsters = 0;
let currentRound = 0;
let mission = null;
let missionData = {};

function t(key, params = {}) {
  let str = strings[key] || key;
  Object.keys(params).forEach(k => {
    str = str.replace(new RegExp(`{${k}}`, 'g'), params[k]);
  });
  return str;
}

function updateUITexts() {
  playBtn.textContent = t('ui.play');
  pauseBtn.textContent = t('ui.pause');
  document.getElementById('restart').textContent = t('ui.restart');
  toggleGridBtn.textContent = t('ui.grid.toggle');
  document.querySelector('[data-i18n="ui.speed"]').textContent = t('ui.speed');
  roundLabel.textContent = t('ui.round', { n: currentRound });
  updateBanners();
  updateMission();
}

function loadLang(l) {
  fetch('lang/' + l + '.json').then(r => r.json()).then(d => {
    strings = d;
    lang = l;
    updateUITexts();
  });
}

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

function showAbilityBanner(text = t('ability.special')) {
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

function addChar(c, side) {
  characters[c.name] = { ...c, statuses: {}, side };
  const div = document.createElement('div');
  div.className = 'char ' + (side === 'heroes' ? 'hero' : 'monster');
  div.id = 'char-' + c.name;
  const badge = side === 'heroes' ? 'H' : 'M';
  div.innerHTML = `<div class="badge">${badge}</div><div class="icon">${c.icon}</div><div class="hp-bar"><div class="hp"></div></div><div class="status-icons"></div>`;
  mapEl.appendChild(div);
  placeChar(c.name, c.x, c.y);
  updateHp(c.name, c.hp);
  updateStatuses(c.name);
}

function setupChars(heroes, monsters) {
  totalHeroes = heroes.length;
  totalMonsters = monsters.length;
  heroes.forEach(c => addChar(c, 'heroes'));
  monsters.forEach(c => addChar(c, 'monsters'));
  updateBanners();
}

function updateBanners() {
  const heroesAlive = Object.values(characters).filter(c => c.side === 'heroes' && c.hp > 0).length;
  const monstersAlive = Object.values(characters).filter(c => c.side === 'monsters' && c.hp > 0).length;
  heroesBanner.textContent = `${t('ui.sides.heroes')} (${heroesAlive}/${totalHeroes})`;
  monstersBanner.textContent = `${t('ui.sides.monsters')} (${monstersAlive}/${totalMonsters})`;
}

function updateMission() {
  if (!mission) return;
  const title = t('mission.title', { name: t(`mission.${mission}.name`) });
  missionTitle.textContent = title;
  if (mission === 'capture_point') {
    missionDesc.textContent = t(`mission.${mission}.desc`, { need: missionData.required });
    missionProgress.textContent = t(`mission.${mission}.progress`, { p: missionData.progress || 0, need: missionData.required });
  } else if (mission === 'escort') {
    missionDesc.textContent = t(`mission.${mission}.desc`);
    if (missionData.done) {
      missionProgress.textContent = t('mission.escort.done');
    } else {
      missionProgress.textContent = t(`mission.${mission}.progress`, { hp: missionData.hp, max: missionData.max });
    }
  } else if (mission === 'survival') {
    missionDesc.textContent = t(`mission.${mission}.desc`, { need: missionData.required });
    missionProgress.textContent = t(`mission.${mission}.progress`, { cur: missionData.progress || 0, need: missionData.required });
  } else if (mission === 'destroy_shrine') {
    missionDesc.textContent = t(`mission.${mission}.desc`);
    missionProgress.textContent = t(`mission.${mission}.progress`, { hp: missionData.hp, max: missionData.max });
  }
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
  updateBanners();
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
      setupChars(ev.heroes, ev.monsters);
      log(t('log.start'));
      log(t(ev.arena));
      currentRound = 1;
      roundLabel.textContent = t('ui.round', { n: currentRound });
      break;
    case 'objective_init':
      mission = ev.mission;
      missionData = {};
      if (mission === 'capture_point') {
        missionData.required = ev.data.required;
        missionData.progress = 0;
      } else if (mission === 'escort') {
        missionData.vip = ev.data.vip;
        const vip = characters[missionData.vip];
        missionData.max = vip.max_hp;
        missionData.hp = vip.hp;
        missionData.done = false;
      } else if (mission === 'survival') {
        missionData.required = ev.data.rounds;
        missionData.progress = 0;
      } else if (mission === 'destroy_shrine') {
        missionData.max = ev.data.shrine.hp;
        missionData.hp = ev.data.shrine.hp;
      }
      updateMission();
      const mtitle = t('mission.title', { name: t(`mission.${mission}.name`) });
      showAbilityBanner(mtitle);
      log(mtitle);
      break;
    case 'objective_progress':
      if (mission === 'capture_point') {
        missionData.progress = ev.progress;
      } else if (mission === 'survival') {
        missionData.progress = ev.progress;
      } else if (mission === 'destroy_shrine') {
        missionData.hp = ev.required - ev.progress;
      }
      updateMission();
      showAbilityBanner(t('mission.update'));
      break;
    case 'objective_complete':
      if (mission === 'escort') {
        missionData.done = true;
        updateMission();
      }
      break;
    case 'round':
      currentRound = ev.round;
      roundLabel.textContent = t('ui.round', { n: currentRound });
      log(t('ui.round', { n: currentRound }));
      initiative = ev.order.slice();
      Object.keys(characters).forEach(n => { delete characters[n].statuses.taunt; updateStatuses(n); });
      renderInitiative();
      break;
    case 'move':
      log(t('log.move', { a: ev.unit_id, from: `(${ev.from.x},${ev.from.y})`, to: `(${ev.to.x},${ev.to.y})` }));
      animateMove(ev.unit_id, ev.path);
      movedActor = ev.unit_id;
      break;
    case 'enter_tile': {
      const tile = ev.tile;
      const el = document.getElementById('char-' + ev.unit_id);
      if (ev.applied_status && ev.applied_status.status === 'poison') {
        el.classList.add('trap');
        setTimeout(() => el.classList.remove('trap'), 300);
        log(t('log.trap.poison', { a: ev.unit_id }), 'log-damage');
      } else if (ev.applied_status && ev.applied_status.status === 'shrine') {
        el.classList.add('shrine');
        const sh = document.createElement('div');
        sh.className = 'shield-effect';
        sh.textContent = '🛡️';
        el.appendChild(sh);
        setTimeout(() => el.classList.remove('shrine'), 300);
        const heal = ev.applied_status.heal || 0;
        const shield = ev.applied_status.shield || 0;
        log(t('log.shrine.enter', { a: ev.unit_id, heal, shield }), 'log-heal');
        const tileEl = document.getElementById(`tile-${tile.x}-${tile.y}`);
        if (tileEl) { tileEl.className = 'tile plain'; tileEl.textContent = '.'; }
      }
      break;
    }
    case 'attack':
      log(t('log.attack', { a: ev.attacker, b: ev.target, dmg: ev.damage }) + (ev.crit ? ' (' + t('log.crit') + ')' : ''), 'log-damage');
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
        log(t('log.damage.poison', { a: ev.target, dmg: ev.amount }), 'log-damage');
        const st = characters[ev.target].statuses;
        if (st.poison) {
          st.poison--;
          if (st.poison <= 0) delete st.poison;
          updateStatuses(ev.target);
        }
      }
      if (mission === 'escort' && missionData.vip === ev.target) {
        missionData.hp = ev.hp;
        updateMission();
      }
      break;
    case 'heal':
      const tgt = ev.target || ev.actor;
      updateHp(tgt, ev.hp);
      const healText = t('log.heal', { a: ev.actor, b: tgt, amt: ev.amount });
      log(healText, 'log-heal');
      if (mission === 'escort' && missionData.vip === tgt) {
        missionData.hp = ev.hp;
        updateMission();
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
          log(t('status.poison', { a: name }), 'log-damage');
          break;
        case 'shield':
          characters[name].statuses.shield = ev.remaining;
          updateStatuses(name);
          log(t('status.shield', { a: name }), 'log-heal');
          break;
        case 'rage':
          characters[name].statuses.rage = 3;
          updateStatuses(name);
           log(t('status.rage', { a: name }), 'log-damage');
          break;
        case 'taunt':
          characters[ev.actor].statuses.taunt = 1;
          updateStatuses(ev.actor);
          log(t('status.taunt', { a: ev.actor }));
          showAbilityBanner(t('ability.taunt'));
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'fireball':
          log(t('status.fireball', { a: ev.actor }), 'log-damage');
          showAbilityBanner(t('ability.fireball'));
          fireball = { actor: ev.actor, remaining: 2 };
          break;
        case 'aim':
          characters[name].statuses.aim = ev.turns || 1;
          updateStatuses(name);
          log(t('status.aim', { a: name }), 'log-buff');
          showAbilityBanner(t('ability.aim'));
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'frenzy':
          characters[name].statuses.frenzy = ev.turns;
          updateStatuses(name);
          log(t('status.frenzy', { a: name }), 'log-buff');
          shiftInitiative(ev.actor);
          movedActor = null;
          break;
        case 'hex':
          characters[name].statuses.hex = ev.turns;
          updateStatuses(name);
          log(t('status.hex', { a: name }), 'log-debuff');
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
      log(t('log.death', { a: ev.target }), 'log-death');
      const d = document.getElementById('char-' + ev.target);
      if (d) { d.style.transition = 'opacity 0.5s'; d.style.opacity = '0'; setTimeout(() => d.remove(), 500); }
      break;
    case 'passive_tick':
      if (ev.status === 'regen') {
        updateHp(ev.target, ev.hp);
        log(t('status.regen', { a: ev.target, amt: ev.amount }), 'log-heal');
      }
      break;
    case 'end':
      const key = ev.winner === 'Heroes' ? 'ui.victory.heroes' : 'ui.victory.monsters';
      const text = t(key);
      log(text);
      const banner = document.createElement('div');
      banner.id = 'banner';
      banner.textContent = text;
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
    currentRound = 1;
    roundLabel.textContent = t('ui.round', { n: currentRound });
    initiative = [];
    fireball = null;
    for (const k in characters) delete characters[k];
    movedActor = null;
    mission = null;
    missionData = {};
    missionTitle.textContent = '';
    missionDesc.textContent = '';
    missionProgress.textContent = '';
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
document.querySelectorAll('#lang-switch button').forEach(btn => {
  btn.addEventListener('click', () => loadLang(btn.dataset.lang));
});

loadLang(lang);
