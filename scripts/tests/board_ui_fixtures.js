"use strict";
// Shared fixtures for the live board's page tests: a fake document and window, and a
// fetch that answers like the v2 server. Lives under tests/, so it is outside the
// coverage denominator (scripts/coverage.sh excludes scripts/tests/**).
const path = require("node:path");
const ui = require(path.join(__dirname, "..", "board", "board_ui.js"));

const tr = ui.makeT("tr");
const en = ui.makeT("en");
const NOW = new Date(2026, 8, 29, 10, 0, 0);
const iso = (d) => d.toISOString();
const ago = (sec) => iso(new Date(NOW.getTime() - sec * 1000));

function state(over = {}) {
  return {
    mode: "C", roles: ["analyst", "developer"], last_event: iso(NOW),
    tasks: {}, agents: {}, sessions: {}, control: { removed_tasks: [], disabled_roles: [] },
    ...over,
  };
}

const PROJECTS = [
  { id: "aaaaaaaaaa", name: "alpha", running: 1, total: 2, turn_open: true },
  { id: "bbbbbbbbbb", name: "beta", running: 0, total: 1, turn_open: false },
];

// Answers like the v2 server: the project list, a project's state, and controls.
const serverLike = (calls, over = {}) => async (url, opts) => {
  calls.push([url, opts]);
  if (url === "/api/projects") return { ok: true, json: async () => over.projects ?? PROJECTS };
  if (url === "/api/control") return over.control ?? { ok: true, json: async () => ({ version: 1 }) };
  return { ok: true, json: async () => state({ sessions: { s: { turn_open: true } } }) };
};

function fakePage({ stored = {}, storageThrows = false, fetchImpl, server, notes = {}, active = null } = {}) {
  const els = {};
  const el = (id) => (els[id] ||= { id, textContent: "", innerHTML: "", className: "",
    shown: null, classList: { toggle: (_c, on) => { els[id].shown = on; } } });
  const labels = [{ dataset: { i18n: "title" }, textContent: "" }];
  let clickHandler = null;
  const doc = {
    documentElement: {}, title: "",
    getElementById: el,
    activeElement: active,
    querySelector: (sel) => (sel in notes ? { value: notes[sel] } : null),
    querySelectorAll: () => labels,
    addEventListener: (type, fn) => { if (type === "click") clickHandler = fn; },
  };
  const saved = {};
  const errors = [];
  const win = {
    setInterval: () => 0,
    console: { error: (...a) => errors.push(a) },
    get localStorage() {
      if (storageThrows) throw new Error("blocked");
      return { getItem: (k) => stored[k] ?? null, setItem: (k, v) => { saved[k] = v; } };
    },
  };
  const calls = [];
  const fetchFn = fetchImpl || serverLike(calls, server);
  const app = ui.start(doc, win, fetchFn);
  return { app, els, labels, doc, saved, errors, calls, click: (target) => clickHandler({ target }) };
}

const target = (over = {}) => ({ id: "", closest: () => null, ...over });

module.exports = { ui, tr, en, NOW, iso, ago, state, PROJECTS, serverLike, fakePage, target };
