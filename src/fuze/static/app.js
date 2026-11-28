// FUZE agent, the local page. Polls /api/status (this page's own server, on this computer) every few seconds and draws it.
// Read-only: nothing here sends anything but that GET. Every text from the data goes in with textContent, never as markup.
"use strict";
const $ = id => document.getElementById(id);
const POLL_MS = 3000, BURN_S = 10;      // the wire under the header burns down in 10 s; each agent step relights it
const MODE = {
  simulation: ["Simulation", "a simulated account on this computer, no money", "none"],
  testnet: ["Testnet", "Lighter's test exchange, test money", "test"],
  mainnet: ["Real money", "Lighter mainnet, your real account", "real"],
};
const SOURCE = {paper: "practice money (our paper account)", testnet: "test money (Lighter testnet)", mainnet: "real money (Lighter mainnet)"};
let lastRev = null;

// ---- small helpers ----
function h(tag, attrs, ...kids) {        // an element; attrs: className, href, text...; kids: nodes or strings
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "text") el.textContent = v; else if (k === "className") el.className = v; else el.setAttribute(k, v);
  }
  for (const k of kids.flat(Infinity)) if (k != null && k !== false) el.append(k);
  return el;
}
const num = v => typeof v === "number" && isFinite(v);
const money = (v, d = 2) => !num(v) ? "–" : (v < 0 ? "−" : "") + "$" + Math.abs(v).toLocaleString("en-US", {minimumFractionDigits: d, maximumFractionDigits: d});
const signed = (v, d = 2) => { if (!num(v)) return "–"; const r = Number(v.toFixed(d)); return (r > 0 ? "+" : "") + money(r === 0 ? 0 : r, d) };
const pct = (v, d = 2) => { if (!num(v)) return "–"; const r = Number(v.toFixed(d)); return (r > 0 ? "+" : r < 0 ? "−" : "") + Math.abs(r).toFixed(d) + "%" };
const tone = v => !num(v) || Math.abs(v) < 0.005 ? "" : v > 0 ? "pos" : "neg";
const px = v => !num(v) ? "–" : money(v, v >= 1000 ? 0 : 2);
const units = (v, c) => !num(v) ? "–" : `${Math.abs(v).toLocaleString("en-US", {maximumFractionDigits: 6})} ${c}`;
function ago(s) {
  if (!num(s)) return "";
  s = Math.max(0, s);
  if (s < 2) return "just now";
  if (s < 90) return `${Math.round(s)} seconds ago`;
  if (s < 5400) return `${Math.round(s / 60)} minutes ago`;
  if (s < 172800) return `${Math.round(s / 3600)} hours ago`;
  return `${Math.round(s / 86400)} days ago`;
}
function span(s) {                      // a duration in plain words: "2 h 5 min"
  if (!num(s)) return "";
  s = Math.max(0, s);
  if (s < 60) return `${Math.round(s)} s`;
  const m = Math.floor(s / 60), d = Math.floor(m / 1440), hr = Math.floor(m / 60) % 24;
  return d ? `${d} d ${hr} h` : hr ? `${hr} h ${m % 60} min` : `${m} min`;
}
function clock(t, now) {                // local time, with the day when it is not today
  if (!num(t)) return "";
  const d = new Date(t * 1000), today = new Date(now * 1000).toDateString() === d.toDateString();
  const hm = d.toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"});
  return today ? hm : `${d.toLocaleDateString("en-GB", {day: "numeric", month: "short"})}, ${hm}`;
}
function put(el, data, build) {         // rebuild only when the data changed, so a focused link keeps its focus
  const k = JSON.stringify(data);
  if (el.dataset.k === k) return;
  el.dataset.k = k; el.replaceChildren(...[build()].flat(Infinity).filter(x => x != null && x !== false && x !== ""));
}
const cmd = text => h("code", {text});
const say = text => h("q", {text});
function line(...parts) { return h("p", null, ...parts) }
function out(href, text) { return h("a", {href, target: "_blank", rel: "noopener noreferrer"}, text, h("span", {"aria-hidden": "true", text: " ↗"}), h("span", {className: "sr", text: " (opens in a new tab)"})) }

// ---- the hero: state and mode ----
function hero(d) {
  const a = d.agent, f = d.flags, m = d.mode, [name, words, money_] = MODE[m.trading] || MODE.simulation;
  document.documentElement.dataset.money = money_;
  $("realbar").hidden = money_ !== "real";
  $("realbar").textContent = a.running ? "Real money: this agent trades a real Lighter account" : "Real money: your settings trade a real Lighter account";
  $("plate-name").textContent = name; $("plate-words").textContent = words;
  const st = {
    running: ["Your FUZE agent is", "Running"], paused: ["Your FUZE agent is", "Paused"], flatten: ["Your FUZE agent has", "Flatten on"],
    daily_stop: ["Your FUZE agent is", "Stopped for today"], stopped: ["Your FUZE agent is", "Not running"], never: ["Your FUZE agent has", "Not started yet"],
  }[a.state] || ["Your FUZE agent", "–"];
  $("lead").textContent = st[0];
  if ($("state").textContent !== st[1]) $("state").textContent = st[1];
  $("state").className = a.state === "running" ? "on" : "";
  document.title = `${st[1]}, ${name.toLowerCase()} · FUZE agent`;
  const since = $("since");
  since.replaceChildren();
  if (a.state === "stopped" && num(a.last_step)) since.append("Its last step was at ", h("b", {text: clock(a.last_step, d.now)}), ` (${ago(d.now - a.last_step)}).`);
  else if (a.state === "daily_stop") since.append("Everything is closed until the next UTC day starts, at ", h("b", {text: clock(Math.ceil(d.now / 86400) * 86400, d.now)}), " your time.");
  else if (num(a.since)) since.append("Since ", h("b", {text: clock(a.since, d.now)}), ` (${span(d.now - a.since)}).`);
  $("doing").textContent = a.running && a.reason ? a.reason : a.state === "never" ? "No status yet: the agent writes one as soon as it starts." : "";
  const mm = $("mismatch");
  mm.hidden = !m.mismatch;
  if (m.mismatch) mm.textContent = `The agent runs in ${m.trading}; your settings now say ${m.name}. Stop it and start it again (fuze run) to trade in ${m.name}.`;
  if (!a.running && m.name !== m.trading) { mm.hidden = false; mm.textContent = `Your settings say ${m.name}.` }
  put($("state-do"), [a.state, f.pause, f.flatten, d.config_error], () => {
    const p = [];
    if (d.config_error) p.push(line(h("b", {text: "Your settings cannot be read: "}), d.config_error, ". Check them with ", cmd("fuze check"), "."));
    if (a.state === "running") p.push(line(h("b", {text: "Pause"}), " (hold what it has, open nothing new): ", cmd("fuze pause"), " or tell your AI tool ", say("pause FUZE"), ". ", h("b", {text: "Close everything"}), ": ", cmd("fuze flatten"), " or ", say("flatten FUZE"), "."));
    if (a.state === "paused") p.push(line(h("b", {text: "Resume"}), ": ", cmd("fuze resume"), " in your own terminal. Your AI tool can pause, never resume."));
    if (a.state === "flatten" || f.flatten) p.push(line(h("b", {text: "Follow again"}), ": ", cmd("fuze unflatten"), " in your own terminal."));
    if (a.state === "stopped" || a.state === "never") {
      p.push(line(h("b", {text: "Start it"}), " in its own terminal: ", cmd("fuze run"), ". Stop it there with Ctrl+C."));
      if (f.pause) p.push(line("PAUSE is on: when it starts it holds and opens nothing new (", cmd("fuze resume"), " to undo)."));
      if (f.flatten && a.state !== "flatten") p.push(line("FLATTEN is on: when it starts it closes everything and stays out."));
    }
    return p;
  });
  // the numbers under the hero
  const ac = d.account, lim = d.limits, rows = [];
  rows.push(["Balance", money(ac.balance), m.trading === "simulation" && num(ac.simulated_start) ? `simulated, started at ${money(ac.simulated_start, 0)}` : m.trading === "testnet" ? "test money" : m.trading === "mainnet" ? "real money" : ""]);
  rows.push(["Today", ac.today_known ? signed(ac.today) : "–", ac.today_known ? `${pct(ac.today_pct)} since 00:00 UTC` : "counts once the agent runs today", ac.today_known ? tone(ac.today) : ""]);
  rows.push(["Held", money(ac.exposure, 0), num(ac.exposure_x) ? `${ac.exposure_x.toFixed(2)} times the balance` : ""]);
  const dl = lim.daily;
  rows.push(["Daily loss stop used", dl && num(dl.used) ? `${Math.round(dl.used * 100)}%` : "–", `of ${Math.round(lim.daily_frac * 100)}% a day`]);
  put($("panel"), rows, () => rows.map(([k, v, sub, cls]) => h("div", null, h("dt", {text: k}), h("dd", {className: cls || null}, v, sub ? h("small", {text: sub}) : null))));
}

// ---- positions and the short-term part ----
function positions(d) {
  const when = $("pos-when"), stale = !d.agent.running && num(d.agent.last_step) && (d.positions.length || d.short);
  when.hidden = !stale;
  if (stale) when.textContent = `As the agent last read the account, at ${clock(d.agent.last_step, d.now)}. Nothing is updated, and nothing follows the signal, until it runs again.`;
  put($("positions"), d.positions, () => {
    if (!d.positions.length) return h("p", {className: "empty", text: d.agent.state === "never" ? "Nothing yet." : "No open position."});
    return d.positions.map(p => h("div", {className: `posn ${p.side}`},
      h("h3", null, h("span", {className: p.side === "short" ? "s" : "l", text: p.side === "short" ? "Short" : "Long"}), ` ${p.name}`),
      h("dl", {className: "nums"},
        h("div", null, h("dt", {text: "Size"}), h("dd", null, money(p.usd, 0), h("small", {text: units(p.units, p.coin)}))),
        h("div", null, h("dt", {text: "Entry"}), h("dd", {text: px(p.entry)})),
        h("div", null, h("dt", {text: "Price now"}), h("dd", {text: px(p.mark)})),
        h("div", null, h("dt", {text: "Result"}), h("dd", {className: tone(p.result) || null}, signed(p.result), p.result == null ? null : h("small", {text: pct(p.result_pct)}))),
        h("div", null, h("dt", {text: "Emergency stop"}), h("dd", null, num(p.stop) ? px(p.stop) : "none", num(p.stop) ? h("small", {text: `for ${units(p.stop_units, p.coin)}`}) : null)))));
  });
  const asked = (d.asked && d.asked.lines) || [];  // what the signal asks for next to what is held, in dollars
  put($("pos-asked"), asked, () => asked.length ? [h("b", {text: "The signal and you"}), ...asked.map(t => h("span", {text: t}))] : []);
  $("pos-asked").hidden = !asked.length;
  const s = d.short, box = $("short");
  box.hidden = !s;
  if (s) {
    const lo = Math.min(s.tp, s.sl), hi = Math.max(s.tp, s.sl), at = v => 20 + 960 * Math.min(1, Math.max(0, (v - lo) / (hi - lo || 1)));
    const x = num(s.mark) ? at(s.mark) : 500, tpLow = s.tp < s.sl, pos = d.positions.find(p => p.coin === s.coin);
    const entry = pos && s.units && Math.abs(Math.abs(pos.units) - Math.abs(s.units)) < 1e-9 ? pos.entry : null;  // the position is only this part: its entry is this part's
    $("spark").setAttribute("transform", `translate(${x.toFixed(1)} 0)`);
    const n = $("f-now"); n.textContent = `${s.name} ${px(s.mark)}`; n.setAttribute("x", Math.min(860, Math.max(140, x)).toFixed(1));
    $("f-lo").textContent = `${tpLow ? "Take profit" : "Stop loss"} ${px(lo)}`; $("f-hi").textContent = `${tpLow ? "Stop loss" : "Take profit"} ${px(hi)}`;
    $("burnt").setAttribute("x1", (num(entry) ? at(entry) : x).toFixed(1)); $("burnt").setAttribute("x2", x.toFixed(1));
    box.classList.toggle("cold", !d.agent.running);
    $("short-h").textContent = s.held ? `The short-term part: ${s.side} ${s.name}, ${money(s.usd, 0)}` : `The short-term trade in the signal: ${s.side} ${s.name}`;
    const cap = $("short-cap"), live = d.mode.trading !== "simulation";
    cap.replaceChildren();
    if (s.held) cap.append(s.protected ? h("b", {text: live ? "Its take profit and stop loss rest on the exchange" : d.agent.running ? "Its take profit and stop loss are set in the simulated account" : "Its take profit and stop loss are set in the simulated account, which checks them only while the agent runs"}) : h("b", {text: "Its take profit and stop loss are not shown on the exchange right now"}),
      `: it closes by itself when the price reaches either end of the line.${num(entry) ? ` The bright part runs from the entry, ${px(entry)}, to the price now.` : ""} The rest of the position follows the slow trend. It has no take profit or stop loss; an emergency stop rests for it, far from the price, and fills only when the agent is not there to move it.`);
    else cap.append("Your agent holds no short-term part right now; its last step says why, at the top of this page.");
  }
  put($("pos-do"), [d.positions.length > 0, d.limits.percent, d.limits.fixed_usd, d.limits.size_mode], () => d.positions.length ? [
    line(h("b", {text: "Smaller positions"}), ": ", cmd(`fuze limits ${lower(d.limits).flag}`), " or tell your AI tool ", say(lower(d.limits).ask), "."),
    line(h("b", {text: "Close everything now"}), ": ", cmd("fuze flatten"), " or ", say("flatten FUZE"), ".")] : []);
}

// ---- the signal ----
function signal(d) {
  const s = d.signal, peekEl = $("sig-peek");
  peekEl.hidden = !(s && s.origin === "page");
  if (s && s.origin === "page") peekEl.textContent = "Your agent is not running. This is the signal now, read and checked by this page; your agent acts on it once you start it with fuze run.";
  const rows = [];
  if (!s) rows.push(["Signal", d.agent.running ? "Waiting for the first signed message." : "None yet. The agent reads it when it runs.", ""]);
  else {
    const what = {live: "Live", flat: "Flat: our account is out of the market", offline: "Offline: our account is not trading"}[s.state] || "–";
    rows.push(["State", what, s.fresh || s.origin === "page" ? "" : "Not fresh: the agent holds what it has and opens nothing new."]);
    const held = s.targets.filter(t => num(t.x) && Math.abs(t.x) >= 0.005).map(t => `${t.x < 0 ? "short" : "long"} ${t.name} ${Math.abs(t.x).toFixed(2)} times our balance`);
    if (s.state === "live") rows.push(["Our position", held.length ? held.join(", ") : "nothing", s.scalp ? `including a short-term trade on ${s.scalp.coin === "BTC" ? "Bitcoin" : "Ether"}: take profit ${px(s.scalp.tp)}, stop loss ${px(s.scalp.sl)}` : ""]);
    rows.push(["Revision", num(s.rev) ? String(s.rev) : "–", "goes up each time our position changes"]);
    rows.push(["Signed", "", ""]);                 // filled below, every poll
    rows.push(["Signature", s.origin === "page" ? "Checked by this page against the key built into FUZE" : "Checked against the key built into FUZE before use", d.agent.last_drop ? `Last message dropped: ${d.agent.last_drop}.` : ""]);
    rows.push(["Our account", SOURCE[s.source] || "–", ""]);
  }
  put($("signal"), rows, () => rows.map(([k, v, sub]) => [h("dt", {text: k}), h("dd", {"data-row": k}, v, sub ? h("small", {text: sub}) : null)]));
  const signed = document.querySelector('#signal dd[data-row="Signed"]');
  if (signed && s) signed.textContent = num(s.age) ? ago(s.age) : "–";
  const note = $("sig-note");
  note.hidden = !(s && s.note);
  if (s && s.note) note.textContent = s.note;
  const why = $("sig-why");
  why.hidden = !(s && s.why);
  if (s && s.why) put(why, s.why, () => ["In our words (text from the signal, for reading only): ", say(s.why)]);
  if (s && s.state === "live" && lastRev != null && s.rev !== lastRev) { const m = $("mark"); m.classList.remove("lit"); void m.offsetWidth; m.classList.add("lit") }   // our position changed: the spark flares once
  lastRev = s ? s.rev : null;
}

// ---- limits ----
function limits(d) {
  const L = d.limits;
  put($("sizing"), L.lines, () => L.lines.map((t, i) => h("li", {className: i === L.lines.length - 1 ? "ex" : null, text: t})));
  const dl = L.daily, frac = Math.round(L.daily_frac * 100);
  put($("daily"), [dl, frac], () => {
    if (!dl) return [h("p", null, h("b", {text: `Daily loss stop, ${frac}%`})), h("small", {text: "It measures from the balance at the start of the UTC day, once the agent runs today."})];
    const used = Math.max(0, Math.min(1, dl.used || 0)), bar = h("div", {className: "val" + (used >= 0.75 ? " hot" : "")});
    bar.style.width = (used * 100).toFixed(1) + "%";
    return [h("p", null, h("b", {text: `Daily loss stop, ${frac}%: ${Math.round(used * 100)}% used`})),
      h("div", {className: "trk", role: "img", "aria-label": `${Math.round(used * 100)} percent of today's loss stop used`}, bar),
      h("small", {text: `Lost today ${money(dl.lost)} of ${money(dl.allowed)}. Everything closes until the next UTC day if the balance reaches ${money(dl.floor)}.`})];
  });
  put($("lim-do"), [L.size_mode, L.percent, L.fixed_usd, L.values.stale_flat_min], () => {
    const lo = lower(L);
    return [line(`Close everything after no live signal for: ${L.values.stale_flat_min}.`),
      line(h("b", {text: "Lower"}), " (applies at once): ", cmd(`fuze limits ${lo.flag}`), " or tell your AI tool ", say(lo.ask), "."),
      line(h("b", {text: "Raise"}), " only in your own terminal, with ", cmd("fuze limits"), " and the new value; it asks you to type RAISE. Your AI tool cannot raise a limit. ", cmd("fuze limits -h"), " lists every setting.")];
  });
}

function lower(L) {                      // an example of a smaller size than the current one, as a flag and as a sentence
  if (L.size_mode === "fixed") { const v = Math.max(10, Math.round(L.fixed_usd / 2)); return {flag: `--fixed-usd ${v}`, ask: `follow FUZE with $${v} instead`} }
  const v = Math.max(1, Math.round(L.percent / 2)); return {flag: `--percent ${v}`, ask: `lower my FUZE share to ${v}%`};
}

// ---- recent orders ----
const KIND = {market: "market order", stop_loss: "stop loss", take_profit: "take profit"};
function orders(d) {
  put($("orders"), d.trades, () => {
    if (!d.trades.length) return h("li", {className: "empty", text: "No orders yet."});
    return d.trades.map(t => {
      const u = num(t.units) ? t.units : 0, verb = u > 0 ? "Bought" : u < 0 ? "Sold" : "No fill:", name = t.coin === "BTC" ? "Bitcoin" : "Ether";
      const head = `${verb} ${units(u || t.asked, t.coin)}${num(t.px) ? ` at ${px(t.px)} (${money(Math.abs(u) * t.px, 0)})` : ""}`;
      const sub = [KIND[t.kind] || t.kind, t.result && t.result !== "filled" ? t.result : "", num(t.asked) && t.asked !== u ? `asked ${units(t.asked, t.coin)}` : "", num(t.worst) ? `worst price ${px(t.worst)}` : "", t.mode && t.mode !== "simulation" ? t.mode : ""].filter(Boolean).join(", ");
      const res = num(t.pnl) && Math.abs(t.pnl) >= 0.005 ? h("span", {className: `res ${tone(t.pnl)}`, text: signed(t.pnl)}) : t.link ? h("span", {className: "res"}, out(t.link, "explorer")) : h("span", {className: "res"});
      return h("li", null, h("time", {text: clock(t.t, d.now)}), h("span", {className: "what"}, head, h("span", {className: "sr", text: ` ${name}`}), h("small", {text: sub})), res);
    });
  });
}

// ---- setup ----
function setup(d) {
  const item = c => h("li", {className: c.ok ? "ok" : "no"}, h("i", {"aria-hidden": "true", text: c.ok ? "✓" : "✕"}), h("span", null, h("span", {className: "sr", text: c.ok ? "OK: " : "Not OK: "}), c.check, c.detail ? h("small", {text: c.detail}) : null));
  put($("checks"), d.checks, () => {         // what fails is always shown; what passes sits behind one line
    const bad = d.checks.filter(c => !c.ok), good = d.checks.filter(c => c.ok);
    return [bad.length ? h("ul", {className: "checks"}, bad.map(item)) : null,
      good.length ? h("details", null, h("summary", {text: bad.length ? `${good.length} more checks pass` : `All ${good.length} checks pass`}), h("ul", {className: "checks"}, good.map(item))) : null];
  });
  const rows = [];
  for (const net of ["testnet", "mainnet"]) {
    const k = d.keys[net];
    rows.push([`Lighter ${net}`, `API key ${k.key}`, k.account != null ? `account ${k.account}` : "no account set", k.link]);
  }
  rows.push(["Mainnet unlock", d.rehearsal === "passed" ? "Testnet rehearsal passed on this machine" : "Locked", d.rehearsal === "passed" ? "" : d.rehearsal]);
  rows.push(["Signal server", d.server, ""]);
  put($("keys"), rows, () => rows.map(([k, v, sub, link]) => [h("dt", {text: k}), h("dd", null, v, sub || link ? h("small", null, sub || "", link ? [", ", out(link, "explorer")] : null) : null)]));
  put($("set-do"), [d.mode.name], () => [
    d.mode.name === "simulation" ? line(h("b", {text: "Mode"}), ": test money with ", cmd("fuze mode testnet"), " in your own terminal, with the agent stopped (it asks you to type RAISE). Real money only with ", cmd("fuze mode mainnet"), ", after ", cmd("fuze rehearse"), " passed on testnet. Your AI tool cannot change the mode.")
      : line(h("b", {text: "Mode"}), ": back to no money with ", cmd("fuze mode simulation"), " in your own terminal, once nothing is open (", cmd("fuze flatten"), ", let the agent close everything, stop it).", d.mode.name === "testnet" ? [" Real money: ", cmd("fuze mode mainnet"), " after ", cmd("fuze rehearse"), " passed."] : null, " Your AI tool cannot change the mode."),
    line(h("b", {text: "Keys"}), ": ", cmd(`fuze keys ${d.mode.name === "mainnet" ? "mainnet" : "testnet"}`), " in your own terminal, typed hidden. Never paste a key into a chat. ", h("b", {text: "Check everything"}), ": ", cmd("fuze check"), "."),
    line("Step by step: ", out("https://docs.fuze.trade", "docs.fuze.trade"), ".")]);
}

// ---- the wire under the header: how long ago the agent's last step was ----
function beat(d) {
  const a = d.agent, b = $("beat"), fresh = a.running && num(a.age);
  const f = fresh ? Math.min(1, a.age / BURN_S) : 1;
  b.classList.toggle("cold", !fresh); $("mark").classList.toggle("cold", !fresh || !(d.signal && d.signal.fresh));
  b.style.setProperty("--burn", (f * 100).toFixed(1) + "%");
}

function draw(d) {
  hero(d); positions(d); signal(d); limits(d); orders(d); setup(d); beat(d);
  $("version").textContent = `FUZE ${d.version}`;
}

async function poll() {
  try {
    const r = await fetch("/api/status", {cache: "no-store"});
    if (!r.ok) throw new Error(String(r.status));
    const d = await r.json();
    $("down").hidden = true;
    draw(d);
  } catch (e) {
    $("down").hidden = false;
    $("beat").classList.add("cold"); $("mark").classList.add("cold");
  }
}
poll();
setInterval(poll, POLL_MS);
