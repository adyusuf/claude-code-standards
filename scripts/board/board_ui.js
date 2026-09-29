"use strict";
/* Live board UI (standards/22-live-board.md). Pure view functions plus start(), which wires
   them to a document. board.html loads it in the browser; scripts/tests/board_ui.test.js
   requires it in Node, so the same code is measured that the page runs. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.BoardView = api;
    api.start(root.document, root, root.fetch.bind(root));
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  const POLL_MS = 1500;
  const LANG_KEY = "board.lang";
  const PROJECT_KEY = "board.project";
  const LIVE = new Set(["starting", "running"]);
  const I18N = {
    tr: {
      title: "Canlı İş Panosu", mode: "Mod", lastEvent: "son olay:", agentsHdr: "Ajanlar",
      tasksHdr: "İşler", activityHdr: "Ajan hareketleri", colTask: "İş", colBranch: "Dal",
      colRole: "Rol / ajan", colStatus: "Durum", colTime: "Süre", colNote: "Not",
      colAgent: "Ajan", colStarted: "Başladı", turnOpen: "Claude çalışıyor", turnClosed: "Tur bitti",
      noSession: "Oturum yok", allDone: "Tüm işler bitti.", remove: "Çıkar", restore: "Geri al",
      noTasks: "Henüz iş yok — Claude plan yazınca burada görünecek.", noAgents: "Henüz ajan başlatılmadı.",
      running: "çalışan", stRunning: "Çalışıyor", stWaiting: "Bekliyor", stDone: "Bitti",
      stRemoved: "Çıkarıldı", stPlanned: "Planlandı", unreachable: "Sunucuya ulaşılamıyor",
      notMeasured: "ölçülemiyor", sec: "sn", min: "dk", hr: "sa", roleOff: "kapalı", roleOn: "açık",
      s_planned: "planlandı", s_running: "çalışıyor", s_agent_done: "ajan bitti · onay bekliyor",
      s_waiting: "bekliyor", s_done: "bitti", s_failed: "başarısız", s_removed: "çıkarıldı",
      s_starting: "başlıyor", s_denied: "reddedildi",
      noProjects: "Henüz proje yok — bir projede Claude oturumu başlayınca burada görünür.",
      s_needs_decision: "karar bekliyor", stDecision: "Karar bekliyor", decided: "Karar",
      continue: "Devam", reject: "Reddet", notePh: "not (isteğe bağlı)",
    },
    en: {
      title: "Live Work Board", mode: "Mode", lastEvent: "last event:", agentsHdr: "Agents",
      tasksHdr: "Tasks", activityHdr: "Agent activity", colTask: "Task", colBranch: "Branch",
      colRole: "Role / agent", colStatus: "Status", colTime: "Time", colNote: "Note",
      colAgent: "Agent", colStarted: "Started", turnOpen: "Claude is working", turnClosed: "Turn finished",
      noSession: "No session", allDone: "All tasks are done.", remove: "Remove", restore: "Restore",
      noTasks: "No tasks yet — they appear once Claude writes the plan.", noAgents: "No agent started yet.",
      running: "running", stRunning: "Running", stWaiting: "Waiting", stDone: "Done",
      stRemoved: "Removed", stPlanned: "Planned", unreachable: "Server unreachable",
      notMeasured: "not measured", sec: "s", min: "m", hr: "h", roleOff: "off", roleOn: "on",
      s_planned: "planned", s_running: "running", s_agent_done: "agent done · awaiting review",
      s_waiting: "waiting", s_done: "done", s_failed: "failed", s_removed: "removed",
      s_starting: "starting", s_denied: "denied",
      noProjects: "No project yet — one appears when a Claude session starts in it.",
      s_needs_decision: "awaiting decision", stDecision: "Awaiting decision", decided: "Decision",
      continue: "Continue", reject: "Reject", notePh: "note (optional)",
    },
  };

  const makeT = (lang) => (k) => (I18N[lang] || {})[k] ?? I18N.tr[k] ?? k;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad = (n) => String(n).padStart(2, "0");
  // #12: dd/mm/yyyy, built by hand — no locale-aware formatting.
  const fmtDate = (d) => `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
  const fmtTime = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

  function fmtStamp(iso, now = new Date()) {
    if (!iso) return "–";
    const d = new Date(iso);
    return fmtDate(d) === fmtDate(now) ? fmtTime(d) : `${fmtDate(d)} ${fmtTime(d)}`;
  }

  function fmtDur(t, fromIso, toIso, now = new Date()) {
    if (!fromIso) return t("notMeasured");
    const s = Math.max(0, Math.round(((toIso ? new Date(toIso) : now) - new Date(fromIso)) / 1000));
    if (s < 60) return `${s} ${t("sec")}`;
    if (s < 3600) return `${Math.floor(s / 60)} ${t("min")} ${s % 60} ${t("sec")}`;
    return `${Math.floor(s / 3600)} ${t("hr")} ${Math.floor(s / 60) % 60} ${t("min")}`;
  }

  const badge = (t, status) => `<span class="badge s-${esc(status)}">${esc(t("s_" + status))}</span>`;

  function taskSpan(task, agents) {
    const own = task.agents.map((k) => agents[k]).filter(Boolean);
    if (!own.length) return [null, null];
    const start = own.map((a) => a.started).sort()[0];
    const live = own.some((a) => LIVE.has(a.status));
    const end = live ? null : own.map((a) => a.ended).filter(Boolean).sort().pop();
    return [start, end];
  }

  function liveAgents(task, agents) {
    const live = task.agents.map((k) => agents[k]).filter((a) => a && LIVE.has(a.status));
    return live.length ? `<div class="live-agents">${live.map((a) =>
      `<span class="agent-chip"><span class="dot on"></span>${esc(a.type)}</span>`).join("")}</div>` : "";
  }

  /** A question Claude put on the board: its choices and a note field, or the answer given. */
  function decisionHtml(task, defaults, t) {
    if (task.status !== "needs_decision") return "";
    if (task.decision) {
      return `<div class="decided">${esc(t("decided"))}: <b>${esc(task.decision.choice)}</b>${
        task.decision.note ? ` — ${esc(task.decision.note)}` : ""}</div>`;
    }
    const choices = task.options && task.options.length
      ? task.options.map((o) => [o, o]) : defaults.map((d) => [d, t(d)]);
    return `<div class="decide" data-decide-task="${esc(task.id)}">${choices.map(([value, label]) =>
      `<button class="act" data-choice="${esc(value)}">${esc(label)}</button>`).join("")}
      <input class="dnote" data-note-for="${esc(task.id)}" maxlength="500" placeholder="${esc(t("notePh"))}"></div>`;
  }

  /** The project tabs: name, live-agent dot, running count; the selected one marked. */
  function projectsHtml(projects, selected, t) {
    if (!projects.length) return `<span class="muted">${esc(t("noProjects"))}</span>`;
    return projects.map((p) => `<button class="tab${p.id === selected ? " on" : ""}" data-project="${esc(p.id)}"
      aria-pressed="${p.id === selected}"><span class="dot${p.turn_open ? " on" : ""}"></span>${esc(p.name)}
      <span class="cnt">${p.running}/${p.total}</span></button>`).join("");
  }

  /** Everything the page shows, computed from the server state; no DOM access. */
  function view(st, t, now = new Date()) {
    const tasks = Object.values(st.tasks);
    const agents = st.agents;
    const agentList = Object.values(agents).sort((a, b) => (b.started || "").localeCompare(a.started || ""));
    const sessions = Object.values(st.sessions);
    const turnOpen = sessions.some((s) => s.turn_open);
    const count = (pred) => tasks.filter(pred).length;
    const stats = [
      [t("stRunning"), count((x) => x.status === "running")],
      [t("stWaiting"), count((x) => x.status === "waiting" || x.status === "agent_done")],
      [t("stDecision"), count((x) => x.status === "needs_decision")],
      [t("stPlanned"), count((x) => x.status === "planned")],
      [t("stDone"), count((x) => x.status === "done")],
      [t("stRemoved"), count((x) => x.status === "removed")],
    ];
    const active = tasks.filter((x) => x.status !== "removed");
    const disabled = new Set(st.control.disabled_roles);
    // A role that was only ever DENIED gets no switch: it is not part of the mode.
    const started = agentList.filter((a) => a.status !== "denied").map((a) => a.type);
    const roleNames = [...new Set([...(st.roles || []), ...started, ...disabled])].filter(Boolean);
    return {
      mode: st.mode ?? "–",
      last: fmtStamp(st.last_event, now),
      turnOpen,
      turnText: !sessions.length ? t("noSession") : turnOpen ? t("turnOpen") : t("turnClosed"),
      statsHtml: stats.map(([l, n]) =>
        `<div class="stat"><div class="n">${n}</div><div class="l">${esc(l)}</div></div>`).join(""),
      allDone: active.length > 0 && active.every((x) => x.status === "done") &&
        !agentList.some((a) => LIVE.has(a.status)),
      rolesHtml: roleNames.map((r) => {
        const on = !disabled.has(r);
        const n = agentList.filter((a) => a.type === r && LIVE.has(a.status)).length;
        return `<div class="role${on ? "" : " off"}"><button class="switch" role="switch" aria-checked="${on}"
          aria-label="${esc(r)} ${esc(on ? t("roleOn") : t("roleOff"))}" data-role="${esc(r)}"></button>
          <span>${esc(r)}</span><span class="cnt">${n} ${esc(t("running"))}</span></div>`;
      }).join(""),
      tasksHtml: !tasks.length ? `<tr><td colspan="7" class="empty">${esc(t("noTasks"))}</td></tr>` :
        tasks.map((x) => {
          const [start, end] = taskSpan(x, agents);
          const removed = x.status === "removed";
          return `<tr class="${removed ? "removed" : ""}">
            <td><span class="tid">${esc(x.id)}</span><span class="title">${esc(x.title)}</span></td>
            <td>${x.branch ? `<code>${esc(x.branch)}</code>` : "—"}</td>
            <td>${esc(x.role || "—")}${liveAgents(x, agents)}</td><td>${badge(t, x.status)}</td>
            <td class="muted">${start ? esc(fmtDur(t, start, end, now)) : "—"}</td>
            <td>${esc(x.note)}${decisionHtml(x, st.decision_defaults || [], t)}</td>
            <td><button class="act" data-task="${esc(x.id)}" data-action="${removed ? "restore_task" : "remove_task"}">
              ${esc(removed ? t("restore") : t("remove"))}</button></td></tr>`;
        }).join(""),
      agentsHtml: !agentList.length ? `<tr><td colspan="6" class="empty">${esc(t("noAgents"))}</td></tr>` :
        agentList.slice(0, 30).map((a) => `<tr><td>${esc(a.type)}</td><td>${esc(a.task || "—")}</td>
          <td>${badge(t, a.status)}</td><td class="muted">${esc(fmtStamp(a.started, now))}</td>
          <td class="muted">${esc(a.status === "denied" ? "—" : fmtDur(t, a.started, a.ended, now))}</td>
          <td>${esc(a.reason || a.description)}</td></tr>`).join(""),
    };
  }

  function readKey(win, key) {
    try { return win.localStorage.getItem(key); } catch { return null; }
  }

  function writeKey(win, key, value) {
    try { win.localStorage.setItem(key, value); } catch { /* per-viewer convenience only */ }
  }

  /** Wires the view to a document: polling, controls, language switch. */
  function start(doc, win, fetchImpl) {
    const stored = readKey(win, LANG_KEY);
    let lang = I18N[stored] ? stored : "tr";  // tr is the primary locale
    let t = makeT(lang);
    let lastState = null;
    let project = readKey(win, PROJECT_KEY);
    const $ = (id) => doc.getElementById(id);

    function applyStatic() {
      doc.documentElement.lang = lang;
      doc.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
      doc.title = t("title");
      $("lang").textContent = lang === "tr" ? "EN" : "TR";
    }

    function render(st) {
      lastState = st;
      const v = view(st, t);
      $("mode").textContent = v.mode;
      $("last").textContent = v.last;
      $("dot").className = "dot" + (v.turnOpen ? " on" : "");
      $("turn").textContent = v.turnText;
      $("stats").innerHTML = v.statsHtml;
      $("banner").classList.toggle("show", v.allDone);
      $("roles").innerHTML = v.rolesHtml;
      // Typing a note: do not redraw the table under the cursor, or the text is lost.
      const typing = doc.activeElement && doc.activeElement.dataset && doc.activeElement.dataset.noteFor;
      if (!typing) $("tasks").innerHTML = v.tasksHtml;
      $("agents").innerHTML = v.agentsHtml;
    }

    async function refresh() {
      try {
        const projects = await (await fetchImpl("/api/projects", { cache: "no-store" })).json();
        if (!projects.some((p) => p.id === project)) project = projects.length ? projects[0].id : null;
        $("projects").innerHTML = projectsHtml(projects, project, t);
        if (!project) { $("err").textContent = ""; return; }
        const res = await fetchImpl(`/api/state?p=${encodeURIComponent(project)}`, { cache: "no-store" });
        render(await res.json());
        $("err").textContent = "";
      } catch (err) {
        $("err").textContent = t("unreachable");
        win.console.error("board refresh failed", err);
      }
    }

    async function control(action, value, extra = {}) {
      const res = await fetchImpl("/api/control", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, value, project, ...extra }),
      });
      const refused = res.ok ? "" : (await res.json()).error;
      await refresh();  // refresh clears the error line, so a refusal is written after it
      if (refused) $("err").textContent = refused;
    }

    function onClick(e) {
      if (e.target.id === "lang") {
        lang = lang === "tr" ? "en" : "tr";
        t = makeT(lang);
        writeKey(win, LANG_KEY, lang);
        applyStatic();
        if (lastState) render(lastState);
        return null;
      }
      const tab = e.target.closest("[data-project]");
      if (tab) {
        project = tab.dataset.project;
        writeKey(win, PROJECT_KEY, project);
        return refresh();
      }
      const pick = e.target.closest("[data-choice]");
      if (pick) {
        const task = pick.closest("[data-decide-task]").dataset.decideTask;
        const noteEl = doc.querySelector(`[data-note-for="${task}"]`);
        return control("decide", task, { choice: pick.dataset.choice, note: noteEl ? noteEl.value : "" });
      }
      const sw = e.target.closest("[data-role]");
      if (sw) return control(sw.getAttribute("aria-checked") === "true" ? "disable_role" : "enable_role", sw.dataset.role);
      const btn = e.target.closest("[data-task]");
      return btn ? control(btn.dataset.action, btn.dataset.task) : null;
    }

    doc.addEventListener("click", onClick);
    applyStatic();
    const first = refresh();
    win.setInterval(refresh, POLL_MS);
    return { first, refresh, control, onClick, lang: () => lang, project: () => project };
  }

  return { I18N, makeT, esc, fmtDate, fmtTime, fmtStamp, fmtDur, view, projectsHtml, decisionHtml, start };
});
