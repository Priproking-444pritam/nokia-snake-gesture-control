import { FilesetResolver, HandLandmarker } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm";

const COLS = 32;
const ROWS = 24;
const MAX_HAND_WALLS = 6;
const GOAL = 8;

const DIRS = {
  UP: [0, -1],
  DOWN: [0, 1],
  LEFT: [-1, 0],
  RIGHT: [1, 0],
};
const OPPOSITE = { UP: "DOWN", DOWN: "UP", LEFT: "RIGHT", RIGHT: "LEFT" };

const TYPES = [
  { id: "classic", name: "Classic", tag: "Nokia original", desc: "Balanced. Walls and self kill.", head: "#ccff33", body: "#9bbc0f", dark: "#5a780c", accent: "#b4dc28", base: 8, boost: 14, score: 1, wrap: false, passSelf: false, breaker: false, length: 3 },
  { id: "shadow", name: "Shadow", tag: "Phase the rim", desc: "Wraps the outer edge. Inner maze still kills.", head: "#d2aaff", body: "#7a4ec4", dark: "#3e2070", accent: "#ba8cff", base: 7.5, boost: 13, score: 1.1, wrap: true, passSelf: false, breaker: false, length: 3 },
  { id: "ember", name: "Ember", tag: "High risk heat", desc: "Faster and scores more. One mistake ends it.", head: "#ffbe5a", body: "#e85c2a", dark: "#8c2812", accent: "#ff8c3c", base: 11, boost: 18, score: 1.4, wrap: false, passSelf: false, breaker: false, length: 4 },
  { id: "titan", name: "Titan", tag: "Break the maze", desc: "Slow tank. Pinch-boost into a maze wall to smash it.", head: "#b4dcff", body: "#4678b0", dark: "#1c385c", accent: "#78beff", base: 6, boost: 10, score: 1, wrap: false, passSelf: false, breaker: true, length: 3 },
  { id: "specter", name: "Specter", tag: "No self-bite", desc: "Glides through its body. Walls still kill.", head: "#8cffea", body: "#20a8a8", dark: "#0c4e52", accent: "#5ae6d2", base: 8.5, boost: 15, score: 0.9, wrap: false, passSelf: true, breaker: false, length: 5 },
];

function key(x, y) { return `${x},${y}`; }
function parse(k) { const [x, y] = k.split(",").map(Number); return [x, y]; }
function rect(x0, y0, x1, y1) {
  const s = new Set();
  for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) s.add(key(x, y));
  return s;
}
function hline(y, x0, x1) { const s = new Set(); for (let x = x0; x <= x1; x++) s.add(key(x, y)); return s; }
function vline(x, y0, y1) { const s = new Set(); for (let y = y0; y <= y1; y++) s.add(key(x, y)); return s; }
function union(...sets) { const out = new Set(); for (const s of sets) for (const v of s) out.add(v); return out; }
function diff(a, b) { const out = new Set(a); for (const v of b) out.delete(v); return out; }
function clearSpawn(walls) {
  const cx = 16, cy = 12;
  for (let i = 0; i < 6; i++) walls.delete(key(cx - i, cy));
  walls.delete(key(cx + 1, cy));
  walls.delete(key(cx + 2, cy));
  return walls;
}

const LEVELS = [
  { n: 1, name: "Open Field", blurb: "Learn the gestures. No inner walls.", speed: 0, fruit: GOAL, walls: () => new Set() },
  { n: 2, name: "Pillars", blurb: "Four blocks to weave around.", speed: 0.4, fruit: GOAL, walls: () => {
    let w = new Set();
    for (const x of [8, 23]) for (const y of [6, 17]) w = union(w, rect(x, y, x + 1, y + 1));
    return clearSpawn(w);
  }},
  { n: 3, name: "Crossroads", blurb: "Broken cross in the middle.", speed: 0.8, fruit: GOAL, walls: () => clearSpawn(union(hline(12, 4, 12), hline(12, 19, 27), vline(16, 3, 8), vline(16, 15, 20))) },
  { n: 4, name: "Courtyards", blurb: "Four rooms, thin doorways.", speed: 1.1, fruit: GOAL + 1, walls: () => clearSpawn(union(
    diff(rect(3, 3, 10, 8), rect(4, 4, 9, 7)),
    diff(rect(21, 3, 28, 8), rect(22, 4, 27, 7)),
    diff(rect(3, 15, 10, 20), rect(4, 16, 9, 19)),
    diff(rect(21, 15, 28, 20), rect(22, 16, 27, 19)),
  )) },
  { n: 5, name: "Corridors", blurb: "Horizontal lanes. Plan the turn.", speed: 1.5, fruit: GOAL + 1, walls: () => {
    let w = new Set();
    [4, 9, 14, 19].forEach((y, i) => { w = union(w, i % 2 === 0 ? hline(y, 2, 24) : hline(y, 7, 29)); });
    return clearSpawn(w);
  }},
  { n: 6, name: "Arena", blurb: "Ring wall with a split gate.", speed: 1.8, fruit: GOAL + 2, walls: () => clearSpawn(union(diff(rect(6, 4, 25, 19), rect(7, 5, 24, 18)), vline(16, 4, 9), vline(16, 14, 19))) },
  { n: 7, name: "Labyrinth", blurb: "Tight maze, tight timing.", speed: 2.2, fruit: GOAL + 2, walls: () => clearSpawn(union(
    hline(3, 2, 14), hline(3, 18, 29), vline(14, 3, 10), vline(18, 3, 10),
    hline(10, 2, 8), hline(10, 23, 29), vline(8, 10, 16), vline(23, 10, 16),
    hline(16, 8, 23), vline(4, 16, 21), vline(27, 16, 21), hline(21, 4, 12), hline(21, 19, 27),
  )) },
  { n: 8, name: "Gauntlet", blurb: "Vertical gates. Finish the campaign.", speed: 2.6, fruit: GOAL + 3, walls: () => {
    let w = new Set();
    for (let x = 3; x < 29; x += 4) {
      const gap = 5 + (Math.floor(x / 4) % 4);
      w = union(w, diff(vline(x, 2, ROWS - 3), new Set([key(x, gap), key(x, gap + 1), key(x, gap + 2)])));
    }
    return clearSpawn(w);
  }},
];

function loadProgress() {
  try {
    return { unlocked: 1, best: 0, lastType: "classic", ...JSON.parse(localStorage.getItem("viper-progress") || "{}") };
  } catch {
    return { unlocked: 1, best: 0, lastType: "classic" };
  }
}
function saveProgress(p) { localStorage.setItem("viper-progress", JSON.stringify(p)); }

class SnakeEngine {
  constructor(type, level) {
    this.type = type;
    this.level = level;
    this.maze = level.walls();
    this.handWalls = new Set();
    this.ghost = null;
    this.dir = "RIGHT";
    this.nextDir = "RIGHT";
    this.score = 0;
    this.eaten = 0;
    this.over = false;
    this.won = false;
    this.boost = false;
    this.breakCd = 0;
    this.particles = [];
    this.resetBody();
    this.spawnFruit();
  }
  resetBody() {
    const len = this.type.length;
    this.snake = Array.from({ length: len }, (_, i) => [16 - i, 12]);
    this.dir = "RIGHT";
    this.nextDir = "RIGHT";
    this.over = false;
    this.won = false;
    this.handWalls.clear();
    this.particles = [];
  }
  occupied() {
    const s = new Set(this.maze);
    for (const w of this.handWalls) s.add(w);
    for (const [x, y] of this.snake) s.add(key(x, y));
    return s;
  }
  spawnFruit() {
    const occ = this.occupied();
    const free = [];
    for (let x = 0; x < COLS; x++) for (let y = 0; y < ROWS; y++) if (!occ.has(key(x, y))) free.push([x, y]);
    this.fruit = free.length ? free[Math.floor(Math.random() * free.length)] : null;
    return Boolean(this.fruit);
  }
  changeDir(name) {
    if (!name || this.over || this.won) return;
    if (OPPOSITE[this.dir] !== name) this.nextDir = name;
  }
  dropWall(cell) {
    if (!cell || this.over || this.won) return false;
    const k = key(cell[0], cell[1]);
    if (cell[0] < 0 || cell[1] < 0 || cell[0] >= COLS || cell[1] >= ROWS) return false;
    if (this.handWalls.size >= MAX_HAND_WALLS) return false;
    if (this.occupied().has(k) || (this.fruit && key(...this.fruit) === k)) return false;
    this.handWalls.add(k);
    return true;
  }
  speed() { return (this.boost ? this.type.boost : this.type.base) + this.level.speed; }
  burst(cell, color) {
    for (let i = 0; i < 10; i++) {
      this.particles.push({ x: cell[0] + 0.5, y: cell[1] + 0.5, vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.4, life: 22, max: 22, color });
    }
  }
  step() {
    if (this.over || this.won) return;
    if (this.breakCd > 0) this.breakCd--;
    this.dir = this.nextDir;
    let [x, y] = this.snake[0];
    const [dx, dy] = DIRS[this.dir];
    x += dx; y += dy;
    if (this.type.wrap) { x = (x + COLS) % COLS; y = (y + ROWS) % ROWS; }
    else if (x < 0 || y < 0 || x >= COLS || y >= ROWS) { this.over = true; return; }
    const k = key(x, y);
    if (this.maze.has(k)) {
      if (this.type.breaker && this.boost && this.breakCd === 0) {
        this.maze.delete(k);
        this.breakCd = 18;
        this.burst([x, y], "#a0b8d2");
      } else { this.over = true; return; }
    }
    if (this.handWalls.has(k)) {
      this.handWalls.delete(k);
      this.burst([x, y], "#8cc8ff");
    }
    const eating = this.fruit && this.fruit[0] === x && this.fruit[1] === y;
    const body = eating ? this.snake : this.snake.slice(0, -1);
    if (!this.type.passSelf && body.some(([bx, by]) => bx === x && by === y)) { this.over = true; return; }
    this.snake.unshift([x, y]);
    if (eating) {
      this.score += Math.floor(10 * this.type.score * (1 + this.level.n * 0.08));
      this.eaten += 1;
      this.burst([x, y], "#e84048");
      if (this.eaten >= this.level.fruit || !this.spawnFruit()) this.won = true;
    } else this.snake.pop();
    this.particles = this.particles.filter((p) => { p.x += p.vx; p.y += p.vy; p.life--; return p.life > 0; });
  }
  draw(ctx, w, h) {
    const cw = w / COLS, ch = h / ROWS;
    ctx.fillStyle = "#060a10";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#162230";
    ctx.lineWidth = 1;
    for (let x = 0; x <= COLS; x++) { ctx.beginPath(); ctx.moveTo(x * cw, 0); ctx.lineTo(x * cw, h); ctx.stroke(); }
    for (let y = 0; y <= ROWS; y++) { ctx.beginPath(); ctx.moveTo(0, y * ch); ctx.lineTo(w, y * ch); ctx.stroke(); }
    const block = (k, fill, edge) => {
      const [x, y] = parse(k);
      roundRect(ctx, x * cw + 1, y * ch + 1, cw - 2, ch - 2, 4, fill, edge);
    };
    for (const k of this.maze) block(k, "#4e6280", "#a0b8d2");
    for (const k of this.handWalls) block(k, "#5ca8ff", "#8cc8ff");
    if (this.ghost) {
      const gk = key(...this.ghost);
      if (!this.occupied().has(gk)) {
        ctx.strokeStyle = "#8cc8ff";
        ctx.strokeRect(this.ghost[0] * cw + 3, this.ghost[1] * ch + 3, cw - 6, ch - 6);
      }
    }
    if (this.fruit) {
      const [fx, fy] = this.fruit;
      const pulse = 1 + 0.1 * Math.sin(Date.now() / 180);
      ctx.fillStyle = "#e84048";
      ctx.beginPath();
      ctx.arc((fx + 0.5) * cw, (fy + 0.52) * ch, (Math.min(cw, ch) / 2 - 3) * pulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#48c460";
      ctx.fillRect((fx + 0.55) * cw, (fy + 0.12) * ch, 7, 4);
    }
    this.snake.forEach(([x, y], i) => {
      roundRect(ctx, x * cw + 2, y * ch + 2, cw - 4, ch - 4, 7, i === 0 ? this.type.head : this.type.body, this.type.dark);
      if (i === 0) {
        ctx.fillStyle = "#0c0e12";
        const eyes = this.dir === "RIGHT" ? [[0.62, 0.32], [0.62, 0.68]]
          : this.dir === "LEFT" ? [[0.32, 0.32], [0.32, 0.68]]
          : this.dir === "UP" ? [[0.32, 0.32], [0.68, 0.32]]
          : [[0.32, 0.68], [0.68, 0.68]];
        for (const [ex, ey] of eyes) ctx.fillRect((x + ex) * cw - 2, (y + ey) * ch - 2, 4, 4);
      }
    });
    for (const p of this.particles) {
      ctx.globalAlpha = p.life / p.max;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x * cw, p.y * ch, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }
}

function roundRect(ctx, x, y, w, h, r, fill, stroke) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.stroke(); }
}

const appEl = document.getElementById("app");
const titleEl = document.getElementById("header-title");
const subEl = document.getElementById("header-sub");
const bestEl = document.getElementById("best-score");
const video = document.getElementById("cam");

const state = {
  screen: "menu",
  progress: loadProgress(),
  type: TYPES.find((t) => t.id === loadProgress().lastType) || TYPES[0],
  game: null,
  keys: new Set(),
  gestureDir: null,
  pinch: false,
  dropWall: false,
  ghost: null,
  hasHand: false,
  landmarker: null,
  lastStep: 0,
  toast: "",
  toastUntil: 0,
  peaceHeld: false,
  camReady: false,
  raf: 0,
};

bestEl.textContent = state.progress.best;

function setHeader(title, sub) {
  titleEl.textContent = title;
  subEl.textContent = sub;
}

function toast(msg) {
  state.toast = msg;
  state.toastUntil = Date.now() + 1400;
}

function render() {
  cancelAnimationFrame(state.raf);
  if (state.screen === "menu") return renderMenu();
  if (state.screen === "howto") return renderHowto();
  if (state.screen === "types") return renderTypes();
  if (state.screen === "levels") return renderLevels();
  renderPlay();
}

function renderMenu() {
  setHeader("Viper", "Hand-guided snake · maze walls · five breeds");
  appEl.innerHTML = `
    <section class="hero">
      <h2>Play it in the browser.</h2>
      <p>Allow the camera, then point your index finger to steer. Pinch for a boost. A peace sign drops a hand-wall under your palm. Arrows still work if you skip the webcam.</p>
      <div class="actions">
        <button class="primary" data-go="levels">Play</button>
        <button data-go="types">Snake types</button>
        <button data-go="howto">How to play</button>
      </div>
      <div class="card">
        <h3>${state.type.name}</h3>
        <p class="tag">${state.type.tag}</p>
        <p>${state.type.desc}</p>
        <p>Campaign: level ${Math.min(state.progress.unlocked, 8)} of 8 unlocked · camera ${state.camReady ? "ready" : "will ask on Play"}</p>
      </div>
    </section>`;
  bindNav();
}

function renderHowto() {
  setHeader("How to play", "Esc or Back returns to the menu");
  const cards = [
    ["Point", "Aim your index finger up, down, left, or right. The snake follows that heading."],
    ["Pinch", "Thumb + index together is a speed boost. Titan uses this to smash maze walls."],
    ["Peace", "Index + middle up drops a hand-wall on the cell under your palm (max 6)."],
    ["Keyboard", "Arrows / WASD to steer, Shift to boost, F to drop a wall in front of the head."],
    ["Levels", "Eat the fruit quota to clear. Inner maze walls kill unless Titan is boosting."],
    ["Edges", "Classic, Ember, Titan, and Specter die on the rim. Shadow wraps around."],
  ];
  appEl.innerHTML = `<div class="actions"><button data-go="menu">Back</button></div>
    <div class="grid howto">${cards.map(([t, b]) => `<article class="card"><h3>${t}</h3><p>${b}</p></article>`).join("")}</div>`;
  bindNav();
}

function renderTypes() {
  setHeader("Snake types", "Pick a breed, then Continue");
  appEl.innerHTML = `
    <div class="grid types">
      ${TYPES.map((t) => `
        <button class="card ${t.id === state.type.id ? "selected" : ""}" data-type="${t.id}" style="--accent:${t.accent}">
          <div class="swatch" style="background:${t.body}"><span style="background:${t.head}"></span></div>
          <h3>${t.name}</h3>
          <div class="tag">${t.tag}</div>
          <p>${t.desc}</p>
          <p>spd ${t.base}/${t.boost} · x${t.score}</p>
        </button>`).join("")}
    </div>
    <div class="actions"><button data-go="menu">Back</button><button class="primary" data-go="levels">Continue</button></div>`;
  bindNav();
  appEl.querySelectorAll("[data-type]").forEach((btn) => {
    btn.onclick = () => {
      state.type = TYPES.find((t) => t.id === btn.dataset.type);
      state.progress.lastType = state.type.id;
      saveProgress(state.progress);
      renderTypes();
    };
  });
}

function renderLevels() {
  setHeader("Campaign", `Playing as ${state.type.name}`);
  appEl.innerHTML = `
    <div class="actions"><button data-go="types">Types</button><button data-go="menu">Menu</button></div>
    <div class="grid levels">
      ${LEVELS.map((lv) => {
        const open = lv.n <= state.progress.unlocked;
        return `<button class="card ${open ? "" : "locked"}" data-level="${lv.n}" ${open ? "" : "disabled"}>
          <h3>${lv.n}  ${lv.name}</h3>
          <p>${open ? lv.blurb : "Clear the previous level to unlock."}</p>
          <p>${lv.fruit} fruit · +${lv.speed} speed</p>
        </button>`;
      }).join("")}
    </div>`;
  bindNav();
  appEl.querySelectorAll("[data-level]").forEach((btn) => {
    btn.onclick = () => startRun(Number(btn.dataset.level));
  });
}

function bindNav() {
  appEl.querySelectorAll("[data-go]").forEach((btn) => {
    btn.onclick = () => { state.screen = btn.dataset.go; render(); };
  });
}

async function startRun(n) {
  cancelAnimationFrame(state.raf);
  const level = LEVELS[n - 1];
  state.game = new SnakeEngine(state.type, level);
  state.screen = "play";
  state.lastStep = performance.now();
  state.progress.lastType = state.type.id;
  saveProgress(state.progress);
  await ensureCamera();
  renderPlay();
  loop();
}

function renderPlay() {
  const g = state.game;
  if (!g) return;
  setHeader(`Lv ${g.level.n}  ${g.level.name}`, `${g.type.name} · ${g.level.blurb}`);
  appEl.innerHTML = `
    <div class="play-wrap">
      <div class="board-frame">
        <canvas id="board" width="768" height="576"></canvas>
        <div class="toast ${Date.now() < state.toastUntil ? "show" : ""}">${state.toast}</div>
        <div class="banner ${g.over || g.won ? "show" : ""}" id="banner">
          <div>
            <h2 style="color:${g.won ? "var(--gold)" : "var(--danger)"}">${g.won ? "LEVEL CLEAR" : "GAME OVER"}</h2>
            <p>Score ${g.score} · fruit ${g.eaten}/${g.level.fruit}</p>
            <div class="actions" style="justify-content:center">
              <button class="primary" id="again">${g.won ? "Next" : "Retry"}</button>
              <button data-go="menu">Menu</button>
            </div>
          </div>
        </div>
      </div>
      <aside class="sidebar">
        <div class="stat"><span>score</span><strong id="st-score">${g.score}</strong></div>
        <div class="stat"><span>fruit</span><strong id="st-fruit">${g.eaten}/${g.level.fruit}</strong></div>
        <div class="stat"><span>hand-walls</span><strong id="st-walls">${g.handWalls.size}/${MAX_HAND_WALLS}</strong></div>
        <div class="stat"><span>speed</span><strong id="st-speed">${g.speed().toFixed(1)}</strong></div>
        <div class="cam-box"><canvas id="cam-overlay"></canvas></div>
        <div class="hand-state ${state.hasHand ? "on" : ""}" id="hand-state">${state.hasHand ? "HAND LOCKED" : "SHOW YOUR HAND"}</div>
        <p class="sub">Shift boost · F wall · Esc menu</p>
      </aside>
    </div>`;
  bindNav();
  const again = document.getElementById("again");
  if (again) again.onclick = () => {
    if (g.won) {
      const nxt = g.level.n + 1;
      if (nxt <= LEVELS.length) startRun(nxt);
      else { toast("Campaign complete"); state.screen = "menu"; render(); }
    } else {
      g.score = 0; g.eaten = 0; g.resetBody(); g.spawnFruit(); state.lastStep = performance.now();
    }
  };
  drawGame();
}

function hudUpdate() {
  const g = state.game;
  if (!g) return;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set("st-score", g.score);
  set("st-fruit", `${g.eaten}/${g.level.fruit}`);
  set("st-walls", `${g.handWalls.size}/${MAX_HAND_WALLS}`);
  set("st-speed", g.speed().toFixed(1));
  const hand = document.getElementById("hand-state");
  if (hand) { hand.textContent = state.hasHand ? "HAND LOCKED" : "SHOW YOUR HAND"; hand.classList.toggle("on", state.hasHand); }
  const banner = document.getElementById("banner");
  if (banner) {
    banner.classList.toggle("show", g.over || g.won);
    if (g.over || g.won) {
      banner.querySelector("h2").textContent = g.won ? "LEVEL CLEAR" : "GAME OVER";
      banner.querySelector("h2").style.color = g.won ? "var(--gold)" : "var(--danger)";
    }
  }
  const t = document.querySelector(".toast");
  if (t) { t.textContent = state.toast; t.classList.toggle("show", Date.now() < state.toastUntil); }
  bestEl.textContent = state.progress.best;
}

function drawGame() {
  const g = state.game;
  const canvas = document.getElementById("board");
  if (!g || !canvas) return;
  const ctx = canvas.getContext("2d");
  g.ghost = state.ghost;
  g.draw(ctx, canvas.width, canvas.height);
  hudUpdate();
}

function loop(now = performance.now()) {
  if (state.screen !== "play" || !state.game) return;
  const g = state.game;
  detectHands();
  if (!g.over && !g.won) {
    const keyDir = state.keys.has("ArrowUp") || state.keys.has("w") ? "UP"
      : state.keys.has("ArrowDown") || state.keys.has("s") ? "DOWN"
      : state.keys.has("ArrowLeft") || state.keys.has("a") ? "LEFT"
      : state.keys.has("ArrowRight") || state.keys.has("d") ? "RIGHT"
      : null;
    g.changeDir(keyDir || state.gestureDir);
    g.boost = state.pinch || state.keys.has("Shift");
    if (state.dropWall) {
      state.dropWall = false;
      toast(g.dropWall(state.ghost) ? "Hand-wall placed" : "Can't place wall");
    }
    const interval = 1000 / Math.max(3, g.speed());
    if (now - state.lastStep >= interval) {
      g.step();
      state.lastStep = now;
      if (g.score > state.progress.best) { state.progress.best = g.score; saveProgress(state.progress); }
      if (g.won) {
        state.progress.unlocked = Math.max(state.progress.unlocked, Math.min(g.level.n + 1, 9));
        saveProgress(state.progress);
      }
    }
  }
  drawGame();
  state.raf = requestAnimationFrame(loop);
}

async function ensureCamera() {
  if (state.landmarker) { state.camReady = true; return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: 640, height: 480 } });
    video.srcObject = stream;
    await video.play();
    const files = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm");
    const model = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
    try {
      state.landmarker = await HandLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: model, delegate: "GPU" },
        runningMode: "VIDEO",
        numHands: 1,
      });
    } catch {
      state.landmarker = await HandLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: model, delegate: "CPU" },
        runningMode: "VIDEO",
        numHands: 1,
      });
    }
    state.camReady = true;
  } catch (err) {
    console.warn("Camera / MediaPipe unavailable, keyboard only.", err);
    state.camReady = false;
  }
}

function detectHands() {
  const overlay = document.getElementById("cam-overlay");
  if (!overlay) return;
  const octx = overlay.getContext("2d");
  if (overlay.width !== 320) { overlay.width = 320; overlay.height = 240; }
  if (video.readyState >= 2) {
    octx.save();
    octx.scale(-1, 1);
    octx.drawImage(video, -overlay.width, 0, overlay.width, overlay.height);
    octx.restore();
  } else {
    octx.fillStyle = "#05070b";
    octx.fillRect(0, 0, overlay.width, overlay.height);
  }
  if (!state.landmarker || video.readyState < 2) { state.hasHand = false; return; }
  const result = state.landmarker.detectForVideo(video, performance.now());
  const hand = result.landmarks && result.landmarks[0];
  state.hasHand = Boolean(hand);
  if (!hand) { state.peaceHeld = false; return; }
  const wrist = hand[0], index = hand[8], middle = hand[12], ring = hand[16], pinky = hand[20];
  const indexPip = hand[6], middlePip = hand[10], ringPip = hand[14], pinkyPip = hand[18], thumb = hand[4], mcp = hand[9];
  const dx = index.x - wrist.x, dy = index.y - wrist.y;
  if (Math.hypot(dx, dy) > 0.12) {
    state.gestureDir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "LEFT" : "RIGHT") : (dy > 0 ? "DOWN" : "UP");
  }
  // video is mirrored in the overlay; MediaPipe x is from the raw (unmirrored) frame, so invert left/right.
  const pinch = Math.hypot(thumb.x - index.x, thumb.y - index.y) < 0.055;
  state.pinch = pinch;
  const peace = index.y < indexPip.y - 0.02 && middle.y < middlePip.y - 0.02 && ring.y > ringPip.y - 0.01 && pinky.y > pinkyPip.y - 0.01 && !pinch;
  if (peace && !state.peaceHeld) { state.dropWall = true; state.peaceHeld = true; }
  else if (!peace) state.peaceHeld = false;
  const palmX = 1 - (wrist.x + mcp.x) / 2;
  const palmY = (wrist.y + mcp.y) / 2;
  state.ghost = [Math.max(0, Math.min(COLS - 1, Math.floor(palmX * COLS))), Math.max(0, Math.min(ROWS - 1, Math.floor(palmY * ROWS)))];
  octx.fillStyle = "#ffb43c";
  octx.beginPath();
  octx.arc(palmX * overlay.width, palmY * overlay.height, 6, 0, Math.PI * 2);
  octx.fill();
  octx.fillStyle = "#50ffc8";
  octx.font = "12px Outfit, sans-serif";
  octx.fillText(`${state.gestureDir || "—"} ${pinch ? "BOOST" : ""} ${peace ? "WALL" : ""}`, 8, 18);
}

window.addEventListener("keydown", (e) => {
  state.keys.add(e.key);
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) e.preventDefault();
  if (e.key === "Escape") {
    state.screen = "menu";
    render();
    return;
  }
  if (state.screen === "play" && state.game && e.key === "f") {
    const [hx, hy] = state.game.snake[0];
    const [dx, dy] = DIRS[state.game.dir];
    let x = hx + dx, y = hy + dy;
    if (state.game.type.wrap) { x = (x + COLS) % COLS; y = (y + ROWS) % ROWS; }
    toast(state.game.dropWall([x, y]) ? "Hand-wall placed" : "Can't place wall");
  }
  if (state.screen === "play" && e.key === "r" && state.game) {
    state.game.score = 0; state.game.eaten = 0; state.game.resetBody(); state.game.spawnFruit();
  }
  if (state.screen === "play" && e.key === "Enter" && state.game) {
    document.getElementById("again")?.click();
  }
});
window.addEventListener("keyup", (e) => state.keys.delete(e.key));

render();
