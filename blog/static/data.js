/* data.js -- cycle explorer for the bundled benchmark dataset (dist/data/).
   build.py embeds a JSON manifest in #data-manifest; this script renders
   env/app pickers, a cycle strip, and a per-cycle timeline from the raw
   harness JSON under ./<env>/<app>.stages.json.
   Permalinks: /data/?env=phone&app=p3_mlkit&cycle=3
   Without JavaScript the server-rendered summary tables stay in place. */
(function () {
  "use strict";

  var mount = document.getElementById("data-explorer");
  var manifestNode = document.getElementById("data-manifest");
  if (!mount || !manifestNode) return;

  var manifest;
  try {
    manifest = JSON.parse(manifestNode.textContent);
  } catch (err) {
    return;
  }
  if (!manifest.envs || !manifest.envs.length) return;

  /* --- small helpers ------------------------------------------------------ */
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }
  function fmt(ms) {
    if (ms == null) return "\u2014";
    return ms >= 1000 ? (ms / 1000).toFixed(2) + " s" : Math.round(ms) + " ms";
  }
  /* The harness stores microseconds; work in ms everywhere else. */
  function normalizeTrials(data) {
    if (data && data.trials) {
      data.trials.forEach(function (cycle) {
        Object.keys(cycle).forEach(function (stage) {
          if (typeof cycle[stage] === "number") cycle[stage] = cycle[stage] / 1000;
        });
      });
    }
    return data;
  }
  function niceStep(max) {
    var steps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000];
    for (var i = 0; i < steps.length; i++) {
      if (max / steps[i] <= 6.5) return steps[i];
    }
    return 10000;
  }
  function pct(t, max) {
    return Math.min(100, Math.max(0, (t / max) * 100));
  }

  /* --- cycle classification (mirrors build.py) ---------------------------- */
  var RFID_MARKERS = [
    "rfid_start_result",
    "stop_for_nfc_requested",
    "stop_requested",
    "arbiter_wait_camera"
  ];
  var SPAN_PRIORITY = {
    launch: ["fast_ready", "started", "preview_painted", "camera_open"],
    entry: ["first_frame", "first_analysis_frame", "camera_open", "started"],
    rfid: ["rfid_start_result"]
  };
  var KIND_LABELS = {
    launch: "Launch prewarm",
    entry: "Scan entry",
    rfid: "RFID handoff"
  };

  function cycleKind(cycle) {
    var keys = Object.keys(cycle);
    function has(name) {
      return keys.indexOf(name) !== -1;
    }
    if (RFID_MARKERS.some(has)) return "rfid";
    if (has("controller_created")) return "launch";
    var hasCamera = has("first_frame") || has("camera_open");
    var hasWarmup = keys.some(function (key) {
      return key.indexOf("warmup") === 0;
    });
    return !hasCamera && hasWarmup ? "launch" : "entry";
  }
  function spanMs(cycle, kind) {
    var priority = SPAN_PRIORITY[kind];
    for (var i = 0; i < priority.length; i++) {
      if (cycle[priority[i]] != null) return cycle[priority[i]];
    }
    return null;
  }

  /* --- state and data loading --------------------------------------------- */
  var state = { env: null, app: null, cycle: 0 };
  var stagesCache = {};

  function envById(id) {
    for (var i = 0; i < manifest.envs.length; i++) {
      if (manifest.envs[i].id === id) return manifest.envs[i];
    }
    return null;
  }
  function appById(env, id) {
    for (var i = 0; i < env.apps.length; i++) {
      if (env.apps[i].id === id) return env.apps[i];
    }
    return null;
  }

  (function readParams() {
    var params = new URLSearchParams(window.location.search);
    var env = envById(params.get("env")) || manifest.envs[0];
    var app = appById(env, params.get("app")) || env.apps[0];
    var cycle = parseInt(params.get("cycle"), 10);
    state.env = env;
    state.app = app;
    state.cycle = isNaN(cycle) ? 0 : cycle;
  })();

  function syncUrl() {
    var query =
      "?env=" + encodeURIComponent(state.env.id) +
      "&app=" + encodeURIComponent(state.app.id) +
      "&cycle=" + state.cycle;
    history.replaceState(null, "", window.location.pathname + query);
  }

  function loadStages(callback) {
    var url = "./" + state.app.files.stages;
    if (stagesCache[url]) {
      callback(stagesCache[url], null);
      return;
    }
    fetch(url)
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        stagesCache[url] = normalizeTrials(data);
        callback(stagesCache[url], null);
      })
      .catch(function (err) {
        callback(null, err);
      });
  }

  /* --- rendering ----------------------------------------------------------- */
  var root = el("div", "dx-root");
  var controls = el("div", "dx-controls");
  var cyclesWrap = el("div", "dx-cycles");
  var detail = el("div", "dx-detail");
  root.appendChild(controls);
  root.appendChild(cyclesWrap);
  root.appendChild(detail);

  mount.innerHTML = "";
  mount.appendChild(root);

  function renderControls() {
    controls.innerHTML = "";
    controls.appendChild(
      group("Environment", manifest.envs, function (env) {
        return {
          label: env.id,
          active: env === state.env,
          pick: function () {
            state.env = env;
            state.app = env.apps[0];
            state.cycle = 0;
            render();
          }
        };
      })
    );
    controls.appendChild(
      group("App", state.env.apps, function (app) {
        return {
          label: app.id,
          active: app === state.app,
          pick: function () {
            state.app = app;
            state.cycle = 0;
            render();
          }
        };
      })
    );
  }

  function group(label, items, toOption) {
    var wrap = el("div", "dx-group");
    wrap.appendChild(el("span", "dx-group-label", label));
    var chips = el("div", "dx-chips");
    items.forEach(function (item) {
      var option = toOption(item);
      var btn = el("button", "dx-chip", option.label);
      btn.type = "button";
      btn.setAttribute("aria-pressed", option.active ? "true" : "false");
      if (option.active) btn.classList.add("is-active");
      btn.addEventListener("click", option.pick);
      chips.appendChild(btn);
    });
    wrap.appendChild(chips);
    return wrap;
  }

  function renderCycles(stages) {
    cyclesWrap.innerHTML = "";
    var max = 1;
    stages.trials.forEach(function (cycle) {
      Object.keys(cycle).forEach(function (key) {
        if (cycle[key] > max) max = cycle[key];
      });
    });
    stages.trials.forEach(function (cycle, index) {
      var kind = cycleKind(cycle);
      var btn = el("button", "dx-cycle");
      btn.type = "button";
      if (index === state.cycle) btn.classList.add("is-active");
      btn.appendChild(el("span", "dx-cycle-num", "c" + index));
      btn.appendChild(el("span", "dx-kind dx-kind-" + kind, KIND_LABELS[kind]));
      var mini = el("span", "dx-mini");
      var timed = Object.keys(cycle).filter(function (stage) {
        return stage !== "tab_tap" && cycle[stage] != null;
      });
      timed.forEach(function (stage) {
        var tick = el("span", "dx-mini-tick");
        tick.style.left = pct(cycle[stage], max) + "%";
        mini.appendChild(tick);
      });
      btn.appendChild(mini);
      var key = spanMs(cycle, kind);
      btn.appendChild(el("span", "dx-cycle-key", fmt(key)));
      btn.addEventListener("click", function () {
        state.cycle = index;
        selectCycle(stages);
      });
      cyclesWrap.appendChild(btn);
    });
  }

  function renderDetail(stages) {
    detail.innerHTML = "";
    var cycle = stages.trials[state.cycle];
    if (!cycle) {
      detail.appendChild(el("p", "dx-error", "This cycle does not exist in the dataset."));
      return;
    }
    var kind = cycleKind(cycle);
    var query = "?env=" + state.env.id + "&app=" + state.app.id;
    var head = el("div", "dx-detail-head");
    var title = el("h3", "dx-detail-title");
    title.appendChild(el("span", "dx-kind dx-kind-" + kind, KIND_LABELS[kind]));
    title.appendChild(el("span", "dx-detail-cycle", "cycle " + state.cycle + " in " + state.app.id + " \u00b7 " + state.env.id));
    head.appendChild(title);
    var key = spanMs(cycle, kind);
    var sub = el("span", "dx-detail-sub");
    sub.appendChild(el("span", null, "tab tap \u2192 " + kindSpanName(kind) + " "));
    sub.appendChild(el("strong", null, fmt(key)));
    sub.appendChild(el("span", null, " \u00b7 " + timedStages(cycle).length + " stages \u00b7 "));
    var permalink = el("a", "dx-permalink", "permalink");
    permalink.href = query + "&cycle=" + state.cycle;
    permalink.addEventListener("click", function (event) {
      event.preventDefault();
      syncUrl();
    });
    sub.appendChild(permalink);
    head.appendChild(sub);
    detail.appendChild(head);

    var max = 1;
    timedStages(cycle).forEach(function (item) {
      if (item.t > max) max = item.t;
    });
    max = max * 1.06;

    var track = el("div", "dx-track");
    var step = niceStep(max);
    for (var t = 0; t <= max; t += step) {
      var tick = el("div", "dx-tick");
      tick.style.left = pct(t, max) + "%";
      track.appendChild(tick);
      var label = el("span", "dx-tick-label", fmt(t));
      label.style.left = pct(t, max) + "%";
      if (t === 0) label.classList.add("is-start");
      track.appendChild(label);
    }
    timedStages(cycle).forEach(function (item, index) {
      var mark = el("div", "dx-mark");
      mark.style.left = pct(item.t, max) + "%";
      mark.classList.add(index % 2 ? "is-above" : "is-below");
      if (pct(item.t, max) < 7) mark.classList.add("is-start");
      if (pct(item.t, max) > 93) mark.classList.add("is-end");
      mark.appendChild(el("span", "dx-mark-dot"));
      mark.appendChild(el("span", "dx-mark-label", item.stage));
      mark.title = item.stage + " \u00b7 " + fmt(item.t);
      track.appendChild(mark);
    });
    detail.appendChild(track);

    var wrap = el("div", "table-wrap");
    var table = el("table", "dx-table");
    var thead = el("thead");
    var headRow = el("tr");
    ["stage", "ms from tap", "\u0394 previous"].forEach(function (labelText) {
      headRow.appendChild(el("th", null, labelText));
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    var tbody = el("tbody");
    var items = timedStages(cycle);
    var prev = 0;
    items.forEach(function (item) {
      var row = el("tr");
      row.appendChild(el("td", null, item.stage));
      row.appendChild(el("td", "num", fmt(item.t)));
      var delta = item.t - prev;
      var deltaCell = el("td", "num dx-delta", (delta > 0 ? "+" : "") + fmt(delta));
      if (delta >= 500) deltaCell.classList.add("is-wait");
      row.appendChild(deltaCell);
      tbody.appendChild(row);
      prev = item.t;
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    detail.appendChild(wrap);
  }

  function kindSpanName(kind) {
    if (kind === "launch") return "ready";
    if (kind === "entry") return "first frame";
    return "RFID started";
  }

  function timedStages(cycle) {
    var items = [];
    Object.keys(cycle).forEach(function (stage) {
      if (stage === "tab_tap" || cycle[stage] == null) return;
      items.push({ stage: stage, t: cycle[stage] });
    });
    items.sort(function (a, b) {
      return a.t - b.t;
    });
    return items;
  }

  function selectCycle(stages) {
    renderCycles(stages);
    renderDetail(stages);
    syncUrl();
  }

  function render() {
    renderControls();
    detail.innerHTML = "";
    cyclesWrap.innerHTML = "";
    var loading = el("p", "dx-note", "Loading\u2026");
    detail.appendChild(loading);
    loadStages(function (data, err) {
      if (err || !data || !data.trials) {
        detail.innerHTML = "";
        detail.appendChild(
          el("p", "dx-error", "Could not load the dataset for this app (" + (err ? err.message : "bad data") + ").")
        );
        return;
      }
      if (state.cycle >= data.trials.length) state.cycle = 0;
      renderCycles(data);
      renderDetail(data);
      syncUrl();
    });
  }

  render();
})();
