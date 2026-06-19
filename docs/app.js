// ===== GameDAG Mini App =====
const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if (tg) { try { tg.ready(); tg.expand(); } catch (e) {} }
const D = window.GAME_DATA;
const app = document.getElementById('app');

// ---------- helpers ----------
function h(html) { app.innerHTML = '<div class="fade">' + html + '</div>'; window.scrollTo(0, 0); }
function el(id) { return document.getElementById(id); }
function on(id, ev, fn) { const e = el(id); if (e) e.addEventListener(ev, fn); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function haptic(type) { try { if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type || 'light'); } catch (e) {} }
function notify(type) { try { if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred(type || 'success'); } catch (e) {} }
function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function rand(a) { return a[Math.floor(Math.random() * a.length)]; }
function range(n) { return Array.from({ length: n }, (_, i) => i); }

let backStack = [];
function setBack(fn) {
  if (!tg || !tg.BackButton) return;
  if (fn) { tg.BackButton.show(); tg.BackButton.onClick(handleBack); backStack._fn = fn; }
  else { tg.BackButton.hide(); }
}
function handleBack() { if (backStack._fn) backStack._fn(); }

// names input helper: returns default names
function defaultNames(n) { return range(n).map(i => 'Игрок ' + (i + 1)); }

// ======================================================
//  HOME
// ======================================================
function home() {
  setBack(null);
  h(`
    <div class="center">
      <h1>🎮 GameDAG</h1>
      <p class="hint">Игры для компании — играйте с одного устройства</p>
    </div>
    <div class="spacer"></div>
    <button class="menu-item" id="m-spy"><span class="emoji">🕵️</span><span><div class="ttl">Шпион</div><div class="sub">Найди того, кто не знает слово</div></span></button>
    <button class="menu-item" id="m-mafia"><span class="emoji">🔪</span><span><div class="ttl">Мафия</div><div class="sub">Город против мафии</div></span></button>
    <button class="menu-item" id="m-croc"><span class="emoji">🐊</span><span><div class="ttl">Крокодил</div><div class="sub">Объясни слово без слов</div></span></button>
    <button class="menu-item" id="m-tod"><span class="emoji">🎭</span><span><div class="ttl">Правда или Действие</div><div class="sub">Честность или смелость</div></span></button>
  `);
  on('m-spy', 'click', () => { haptic(); spySetup(); });
  on('m-mafia', 'click', () => { haptic(); mafiaSetup(); });
  on('m-croc', 'click', () => { haptic(); crocSetup(); });
  on('m-tod', 'click', () => { haptic(); todSetup(); });
}

// reusable player-count picker
function countPicker(opts) {
  // opts: {title, sub, min, max, value, onPick}
  const { title, sub, min, max } = opts;
  let val = opts.value || min;
  const chips = range(max - min + 1).map(i => {
    const n = min + i;
    return `<button class="chip" data-n="${n}">${n}</button>`;
  }).join('');
  h(`
    <div class="topbar"><span class="pill">${esc(title)}</span></div>
    <h2>Сколько игроков?</h2>
    <p class="hint">${esc(sub || '')}</p>
    <div class="grid" id="cp-grid">${chips}</div>
    <div class="spacer"></div>
    <button class="btn" id="cp-go">Продолжить</button>
    <button class="btn secondary" id="cp-back">← Назад в меню</button>
  `);
  function mark() { document.querySelectorAll('#cp-grid .chip').forEach(c => c.classList.toggle('active', +c.dataset.n === val)); }
  document.querySelectorAll('#cp-grid .chip').forEach(c => c.addEventListener('click', () => { val = +c.dataset.n; haptic(); mark(); }));
  mark();
  on('cp-go', 'click', () => { haptic(); opts.onPick(val); });
  on('cp-back', 'click', () => { haptic(); home(); });
  setBack(home);
}

// privacy gate: 'Передайте телефон X' -> reveal callback
function passDevice(toWhom, btnLabel, onReady) {
  h(`
    <div class="reveal-box">
      <div style="font-size:48px">📱➡️</div>
      <h2>Передайте устройство</h2>
      <p class="big">${esc(toWhom)}</p>
      <p class="hint">Остальные — не подглядывайте 🙈</p>
    </div>
    <button class="btn" id="pd-go">${esc(btnLabel || 'Я готов(а)')}</button>
  `);
  on('pd-go', 'click', () => { haptic('medium'); onReady(); });
}

// ======================================================
//  ШПИОН
// ======================================================
let spy = {};
function spySetup() {
  const themes = Object.keys(D.THEMES);
  countPicker({
    title: '🕵️ ШПИОН', sub: 'Минимум 3 игрока', min: 3, max: 12, value: 4,
    onPick(n) {
      spy = { count: n };
      // theme select
      const items = ['🎲 Случайная тема', ...themes].map((t, i) =>
        `<button class="menu-item" data-theme="${i === 0 ? '__rand__' : esc(t)}"><span class="ttl">${esc(t)}</span></button>`).join('');
      h(`<div class="topbar"><span class="pill">🕵️ ШПИОН</span><span class="hint">${n} игроков</span></div>
         <h2>Выбери тему</h2>${items}
         <button class="btn secondary" id="sp-back">← Назад</button>`);
      document.querySelectorAll('[data-theme]').forEach(b => b.addEventListener('click', () => {
        haptic();
        let theme = b.dataset.theme;
        if (theme === '__rand__') theme = rand(themes);
        spyStart(theme);
      }));
      on('sp-back', 'click', () => { haptic(); spySetup(); });
      setBack(spySetup);
    }
  });
}
function spyStart(theme) {
  const word = rand(D.THEMES[theme]);
  const spyIndex = Math.floor(Math.random() * spy.count);
  spy.theme = theme; spy.word = word; spy.spyIndex = spyIndex; spy.cur = 0;
  spyReveal();
}
function spyReveal() {
  const i = spy.cur;
  if (i >= spy.count) return spyDiscuss();
  passDevice('Игрок ' + (i + 1), 'Посмотреть мою роль', () => {
    const isSpy = i === spy.spyIndex;
    h(`
      <div class="reveal-box">
        <div class="hint">Тема: ${esc(spy.theme)}</div>
        ${isSpy
          ? `<div style="font-size:48px">🕵️</div><h2>Вы ШПИОН</h2><p>Не знаете слово. Притворяйтесь и вычислите остальных!</p>`
          : `<div style="font-size:48px">🤫</div><h3>Секретное слово:</h3><div class="huge">${esc(spy.word)}</div>`}
      </div>
      <button class="btn" id="sp-next">Скрыть и передать дальше</button>
    `);
    on('sp-next', 'click', () => { haptic(); spy.cur++; spyReveal(); });
  });
}
function spyDiscuss() {
  setBack(home);
  h(`
    <div class="topbar"><span class="pill">🕵️ ШПИОН</span></div>
    <div class="card center">
      <h2>Все узнали роли!</h2>
      <p>По очереди называйте слово-ассоциацию по теме <b>«${esc(spy.theme)}»</b>, не выдавая само слово.</p>
      <p class="hint">Цель мирных — вычислить шпиона. Цель шпиона — угадать слово и не спалиться.</p>
    </div>
    <button class="btn warn" id="sp-reveal">🗳️ Показать, кто шпион</button>
    <button class="btn secondary" id="sp-home">🏠 В меню</button>
  `);
  on('sp-reveal', 'click', () => {
    haptic('heavy');
    h(`<div class="reveal-box">
        <div style="font-size:48px">🕵️</div>
        <h2>Шпионом был…</h2>
        <div class="huge">Игрок ${spy.spyIndex + 1}</div>
        <p>Слово было: <b>${esc(spy.word)}</b></p>
        <p class="hint">Тема: ${esc(spy.theme)}</p>
      </div>
      <button class="btn" id="sp-again">🔁 Сыграть ещё</button>
      <button class="btn secondary" id="sp-home2">🏠 В меню</button>`);
    on('sp-again', 'click', () => { haptic(); spySetup(); });
    on('sp-home2', 'click', () => { haptic(); home(); });
  });
  on('sp-home', 'click', () => { haptic(); home(); });
}

// ======================================================
//  КРОКОДИЛ
// ======================================================
let croc = {};
function crocSetup() {
  const diffs = Object.keys(D.CROCODILE_WORDS);
  const items = diffs.map(d => `<button class="menu-item" data-diff="${esc(d)}"><span class="ttl">${esc(d)}</span></button>`).join('');
  h(`<div class="topbar"><span class="pill">🐊 КРОКОДИЛ</span></div>
     <h2>Выбери сложность</h2>${items}
     <button class="btn secondary" id="cr-back">← Назад в меню</button>`);
  document.querySelectorAll('[data-diff]').forEach(b => b.addEventListener('click', () => {
    haptic(); croc.diff = b.dataset.diff; crocPlayers();
  }));
  on('cr-back', 'click', () => { haptic(); home(); });
  setBack(home);
}
function crocPlayers() {
  countPicker({
    title: '🐊 КРОКОДИЛ', sub: 'Минимум 2 игрока. Один объясняет — остальные угадывают.', min: 2, max: 12, value: 4,
    onPick(n) {
      croc.count = n;
      croc.scores = range(n).map(() => 0);
      croc.pool = shuffle(D.CROCODILE_WORDS[croc.diff]);
      croc.poolIdx = 0;
      croc.turn = 0;
      crocTurn();
    }
  });
}
function nextCrocWord() {
  if (croc.poolIdx >= croc.pool.length) { croc.pool = shuffle(D.CROCODILE_WORDS[croc.diff]); croc.poolIdx = 0; }
  return croc.pool[croc.poolIdx++];
}
function crocTurn() {
  setBack(home);
  const explainer = croc.turn % croc.count;
  passDevice('Игрок ' + (explainer + 1) + ' (объясняет)', 'Показать слово', () => {
    croc.word = nextCrocWord();
    crocShowWord(explainer);
  });
}
function crocShowWord(explainer) {
  h(`
    <div class="topbar"><span class="pill">🐊 ${esc(croc.diff)}</span><span class="hint">Объясняет: Игрок ${explainer + 1}</span></div>
    <div class="reveal-box">
      <h3>Объясни слово без слов и однокоренных:</h3>
      <div class="huge">${esc(croc.word)}</div>
    </div>
    <button class="btn success" id="cr-ok">✅ Угадали (+1 балл)</button>
    <button class="btn warn" id="cr-skip">⏭️ Пропустить слово</button>
    <button class="btn secondary" id="cr-end">🏁 Завершить игру</button>
  `);
  on('cr-ok', 'click', () => { notify('success'); croc.scores[explainer]++; croc.turn++; crocTurn(); });
  on('cr-skip', 'click', () => { haptic(); croc.word = nextCrocWord(); crocShowWord(explainer); });
  on('cr-end', 'click', () => { haptic(); crocScore(); });
}
function crocScore() {
  setBack(home);
  const order = range(croc.count).map(i => ({ i, s: croc.scores[i] })).sort((a, b) => b.s - a.s);
  const medals = ['🥇', '🥈', '🥉'];
  const rows = order.map((o, idx) =>
    `<div class="scorerow"><span>${medals[idx] || (idx + 1) + '.'} Игрок ${o.i + 1}</span><b>${o.s}</b></div>`).join('');
  h(`<div class="topbar"><span class="pill">🐊 КРОКОДИЛ</span></div>
     <h2>🏆 Итоги</h2><div class="card">${rows}</div>
     <button class="btn" id="cr-again">🔁 Сыграть ещё</button>
     <button class="btn secondary" id="cr-home">🏠 В меню</button>`);
  on('cr-again', 'click', () => { haptic(); crocSetup(); });
  on('cr-home', 'click', () => { haptic(); home(); });
}

// ======================================================
//  ПРАВДА ИЛИ ДЕЙСТВИЕ
// ======================================================
let tod = {};
function todSetup() {
  h(`<div class="topbar"><span class="pill">🎭 ПРАВДА ИЛИ ДЕЙСТВИЕ</span></div>
     <h2>Выбери режим</h2>
     <button class="menu-item" data-mode="normal"><span class="emoji">😊</span><span><div class="ttl">Обычный</div><div class="sub">Весёлые вопросы для любой компании</div></span></button>
     <button class="menu-item" data-mode="18plus"><span class="emoji">🔞</span><span><div class="ttl">18+</div><div class="sub">Более смелые вопросы для взрослых</div></span></button>
     <button class="btn secondary" id="td-back">← Назад в меню</button>`);
  document.querySelectorAll('[data-mode]').forEach(b => b.addEventListener('click', () => {
    haptic(); tod.mode = b.dataset.mode; todPlayers();
  }));
  on('td-back', 'click', () => { haptic(); home(); });
  setBack(home);
}
function todPlayers() {
  countPicker({
    title: '🎭 ' + (tod.mode === '18plus' ? '18+' : 'Обычный'), sub: 'Минимум 2 игрока', min: 2, max: 12, value: 4,
    onPick(n) {
      tod.count = n; tod.turn = 0;
      tod.truths = shuffle(D.TOD_QUESTIONS[tod.mode].truth); tod.ti = 0;
      tod.dares = shuffle(D.TOD_QUESTIONS[tod.mode].dare); tod.di = 0;
      todTurn();
    }
  });
}
function todTurn() {
  setBack(home);
  const p = tod.turn % tod.count;
  h(`
    <div class="topbar"><span class="pill">🎭 ${tod.mode === '18plus' ? '18+' : 'Обычный'}</span></div>
    <div class="reveal-box">
      <h2>Ход игрока</h2>
      <div class="big">Игрок ${p + 1}</div>
      <p class="hint">Что выбираешь?</p>
    </div>
    <button class="btn" id="td-truth">🤔 ПРАВДА</button>
    <button class="btn warn" id="td-dare">💪 ДЕЙСТВИЕ</button>
    <button class="btn secondary" id="td-home">🏠 В меню</button>
  `);
  on('td-truth', 'click', () => { haptic(); todShow(p, 'truth'); });
  on('td-dare', 'click', () => { haptic(); todShow(p, 'dare'); });
  on('td-home', 'click', () => { haptic(); home(); });
}
function todShow(p, kind) {
  let q;
  if (kind === 'truth') { if (tod.ti >= tod.truths.length) { tod.truths = shuffle(tod.truths); tod.ti = 0; } q = tod.truths[tod.ti++]; }
  else { if (tod.di >= tod.dares.length) { tod.dares = shuffle(tod.dares); tod.di = 0; } q = tod.dares[tod.di++]; }
  h(`
    <div class="topbar"><span class="pill">Игрок ${p + 1}</span><span class="hint">${kind === 'truth' ? '🤔 Правда' : '💪 Действие'}</span></div>
    <div class="reveal-box"><div style="font-size:40px">${kind === 'truth' ? '🤔' : '💪'}</div><p class="big">${esc(q)}</p></div>
    <button class="btn success" id="td-done">✅ Выполнено / Ответил(а)</button>
    <button class="btn danger" id="td-skip">❌ Отказываюсь (пропуск)</button>
  `);
  on('td-done', 'click', () => { notify('success'); tod.turn++; todTurn(); });
  on('td-skip', 'click', () => { haptic(); tod.turn++; todTurn(); });
}

// ======================================================
//  МАФИЯ
// ======================================================
let mafia = {};
function mafiaSetup() {
  countPicker({
    title: '🔪 МАФИЯ', sub: 'От 4 до 10 игроков. 5+ — комиссар, 6+ — доктор, 7+ — 2 мафии.', min: 4, max: 10, value: 5,
    onPick(n) { mafiaAssign(n); }
  });
}
function mafiaAssign(n) {
  const ids = range(n);
  const roles = {};
  let pool = shuffle(ids);
  const mafiaCount = n >= 7 ? 2 : 1;
  const mafiaIds = pool.slice(0, mafiaCount); pool = pool.slice(mafiaCount);
  mafiaIds.forEach(i => roles[i] = 'мафия');
  let komissar = null, doctor = null;
  if (n >= 5 && pool.length) { komissar = pool.shift(); roles[komissar] = 'комиссар'; }
  if (n >= 6 && pool.length) { doctor = pool.shift(); roles[doctor] = 'доктор'; }
  pool.forEach(i => roles[i] = 'мирный');
  mafia = {
    count: n, roles, mafiaIds, komissar, doctor,
    alive: ids.reduce((o, i) => (o[i] = true, o), {}),
    day: 1, cur: 0
  };
  mafiaReveal();
}
const ROLE_INFO = {
  'мафия':   { emoji: '🔪', text: 'Ночью вы убиваете мирных. Не выдайте себя днём.' },
  'комиссар':{ emoji: '🕵️', text: 'Ночью вы проверяете одного игрока — мафия он или нет.' },
  'доктор':  { emoji: '💊', text: 'Ночью вы спасаете одного игрока от убийства.' },
  'мирный':  { emoji: '👤', text: 'Днём вычисляйте мафию и голосуйте против неё.' }
};
function mafiaReveal() {
  const i = mafia.cur;
  if (i >= mafia.count) return mafiaNightStart();
  passDevice('Игрок ' + (i + 1), 'Узнать мою роль', () => {
    const role = mafia.roles[i];
    const info = ROLE_INFO[role];
    let extra = '';
    if (role === 'мафия' && mafia.mafiaIds.length > 1) {
      const others = mafia.mafiaIds.filter(x => x !== i).map(x => 'Игрок ' + (x + 1)).join(', ');
      extra = `<p class="hint">Ваши напарники: ${esc(others)}</p>`;
    }
    h(`<div class="reveal-box">
        <div style="font-size:52px">${info.emoji}</div>
        <h2>${esc(role.toUpperCase())}</h2>
        <p>${info.text}</p>${extra}
      </div>
      <button class="btn" id="mf-next">Скрыть и передать дальше</button>`);
    on('mf-next', 'click', () => { haptic(); mafia.cur++; mafiaReveal(); });
  });
}
function aliveList(excludeSelf) {
  return range(mafia.count).filter(i => mafia.alive[i] && i !== excludeSelf);
}
function targetButtons(targets, prefix) {
  return targets.map(i => `<button class="btn secondary" data-t="${i}" id="${prefix}-${i}">Игрок ${i + 1}</button>`).join('');
}
function mafiaNightStart() {
  mafia.night = {};
  setBack(null);
  h(`<div class="reveal-box"><div style="font-size:52px">🌙</div><h2>Ночь ${mafia.day}</h2><p>Город засыпает…</p></div>
     <button class="btn" id="mf-go">Начать ночь</button>`);
  on('mf-go', 'click', () => { haptic(); mafiaMafiaTurn(); });
}
function mafiaMafiaTurn() {
  passDevice('Мафия 🔪', 'Открыть глаза', () => {
    const targets = range(mafia.count).filter(i => mafia.alive[i] && !mafia.mafiaIds.includes(i));
    h(`<h2>🔪 Мафия выбирает жертву</h2><p class="hint">Кого убить этой ночью?</p>${targetButtons(targets, 'mk')}`);
    targets.forEach(i => on('mk-' + i, 'click', () => { haptic('medium'); mafia.night.victim = i; mafiaDoctorTurn(); }));
  });
}
function mafiaDoctorTurn() {
  if (mafia.doctor === null || !mafia.alive[mafia.doctor]) return mafiaKomissarTurn();
  passDevice('Доктор 💊', 'Открыть глаза', () => {
    const targets = range(mafia.count).filter(i => mafia.alive[i]);
    h(`<h2>💊 Доктор спасает</h2><p class="hint">Кого вылечить этой ночью?</p>${targetButtons(targets, 'mh')}`);
    targets.forEach(i => on('mh-' + i, 'click', () => { haptic('medium'); mafia.night.heal = i; mafiaKomissarTurn(); }));
  });
}
function mafiaKomissarTurn() {
  if (mafia.komissar === null || !mafia.alive[mafia.komissar]) return mafiaResolveNight();
  passDevice('Комиссар 🕵️', 'Открыть глаза', () => {
    const targets = aliveList(mafia.komissar);
    h(`<h2>🕵️ Комиссар проверяет</h2><p class="hint">Кого проверить?</p>${targetButtons(targets, 'mc')}`);
    targets.forEach(i => on('mc-' + i, 'click', () => {
      haptic('medium');
      const isMafia = mafia.mafiaIds.includes(i);
      h(`<div class="reveal-box"><div style="font-size:48px">${isMafia ? '🔪' : '✅'}</div>
          <h2>Игрок ${i + 1}</h2><p class="big">${isMafia ? 'МАФИЯ' : 'НЕ мафия'}</p></div>
         <button class="btn" id="mc-ok">Закрыть глаза</button>`);
      on('mc-ok', 'click', () => { haptic(); mafiaResolveNight(); });
    }));
  });
}
function mafiaResolveNight() {
  const v = mafia.night.victim, hl = mafia.night.heal;
  let killedMsg;
  if (v != null && v !== hl) { mafia.alive[v] = false; killedMsg = `☠️ Этой ночью убит <b>Игрок ${v + 1}</b>.`; }
  else if (v != null && v === hl) { killedMsg = '💊 Доктор спас жертву! Все живы.'; }
  else { killedMsg = 'Этой ночью никто не погиб.'; }
  passDevice('Все 🌅', 'Показать итоги ночи', () => {
    h(`<div class="reveal-box"><div style="font-size:48px">🌅</div><h2>Утро ${mafia.day}</h2><p class="big">${killedMsg}</p></div>
       <button class="btn" id="mf-cont">Продолжить</button>`);
    on('mf-cont', 'click', () => { haptic(); const w = mafiaCheckWin(); if (w) return mafiaEnd(w); mafiaDay(); });
  });
}
function mafiaCheckWin() {
  const aliveMafia = mafia.mafiaIds.filter(i => mafia.alive[i]).length;
  const aliveCiv = range(mafia.count).filter(i => mafia.alive[i] && !mafia.mafiaIds.includes(i)).length;
  if (aliveMafia === 0) return 'civilians';
  if (aliveMafia >= aliveCiv) return 'mafia';
  return null;
}
function mafiaDay() {
  setBack(null);
  const aliveP = range(mafia.count).filter(i => mafia.alive[i]);
  const rows = aliveP.map(i => `Игрок ${i + 1}`).join(', ');
  h(`<div class="topbar"><span class="pill">☀️ День ${mafia.day}</span></div>
     <div class="card"><h3>Живые игроки</h3><p>${rows}</p></div>
     <p class="hint">Обсудите, кто мафия. Затем начните голосование — каждый живой игрок голосует по очереди на этом устройстве.</p>
     <button class="btn warn" id="mf-vote">🗳️ Начать голосование</button>`);
  on('mf-vote', 'click', () => { haptic(); mafia.votes = {}; mafia.voteOrder = aliveP.slice(); mafia.voteIdx = 0; mafiaVoteStep(); });
}
function mafiaVoteStep() {
  if (mafia.voteIdx >= mafia.voteOrder.length) return mafiaVoteResult();
  const voter = mafia.voteOrder[mafia.voteIdx];
  passDevice('Игрок ' + (voter + 1) + ' голосует', 'Голосовать', () => {
    const targets = aliveList(voter);
    h(`<h2>🗳️ За кого голосует Игрок ${voter + 1}?</h2>
       ${targetButtons(targets, 'mv')}
       <button class="btn secondary" id="mv-skip">Воздержаться</button>`);
    targets.forEach(i => on('mv-' + i, 'click', () => { haptic(); mafia.votes[i] = (mafia.votes[i] || 0) + 1; mafia.voteIdx++; mafiaVoteStep(); }));
    on('mv-skip', 'click', () => { haptic(); mafia.voteIdx++; mafiaVoteStep(); });
  });
}
function mafiaVoteResult() {
  const entries = Object.entries(mafia.votes);
  let out = '', eliminated = null;
  if (!entries.length) { out = 'Никто не проголосовал — день прошёл спокойно.'; }
  else {
    const max = Math.max(...entries.map(e => e[1]));
    const top = entries.filter(e => e[1] === max).map(e => +e[0]);
    if (top.length > 1) { out = 'Голоса разделились поровну — никого не выгнали.'; }
    else {
      eliminated = top[0]; mafia.alive[eliminated] = false;
      const role = mafia.roles[eliminated];
      out = `Город изгнал <b>Игрока ${eliminated + 1}</b>. Его роль: <b>${esc(role)}</b> ${ROLE_INFO[role].emoji}`;
    }
  }
  h(`<div class="reveal-box"><div style="font-size:48px">⚖️</div><h2>Итог голосования</h2><p class="big">${out}</p></div>
     <button class="btn" id="mf-cont">Продолжить</button>`);
  on('mf-cont', 'click', () => {
    haptic();
    const w = mafiaCheckWin(); if (w) return mafiaEnd(w);
    mafia.day++; mafiaNightStart();
  });
}
function mafiaEnd(winner) {
  notify('success');
  setBack(home);
  const roleRows = range(mafia.count).map(i =>
    `<div class="scorerow"><span>Игрок ${i + 1} ${mafia.alive[i] ? '' : '💀'}</span><b>${esc(mafia.roles[i])} ${ROLE_INFO[mafia.roles[i]].emoji}</b></div>`).join('');
  h(`<div class="reveal-box"><div style="font-size:52px">${winner === 'mafia' ? '🔪' : '🏆'}</div>
      <h2>${winner === 'mafia' ? 'Победила Мафия!' : 'Победил Город!'}</h2></div>
     <div class="card"><h3>Все роли</h3>${roleRows}</div>
     <button class="btn" id="mf-again">🔁 Сыграть ещё</button>
     <button class="btn secondary" id="mf-home">🏠 В меню</button>`);
  on('mf-again', 'click', () => { haptic(); mafiaSetup(); });
  on('mf-home', 'click', () => { haptic(); home(); });
}

// ======================================================
//  РОУТИНГ (дип-линки из бота)
// ======================================================
function routeStart() {
  // Бот может открыть конкретную игру через ?game=... в URL
  let g = '';
  try { g = new URLSearchParams(location.search).get('game') || ''; } catch (e) {}
  // или через start_param (startapp=...) в Telegram
  try { if (!g && tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) g = tg.initDataUnsafe.start_param; } catch (e) {}
  switch (g) {
    case 'spy': return spySetup();
    case 'mafia': return mafiaSetup();
    case 'crocodile': case 'croc': return crocSetup();
    case 'tod': return todSetup();
    default: return home();
  }
}
routeStart();
