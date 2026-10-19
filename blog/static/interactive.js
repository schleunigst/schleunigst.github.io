/* interactive.js -- interactive figures for entry pages.
   Figures opt in with data-ix="startup|ranking|arbiter" and a static
   <img class="ix-fallback">; this script replaces the fallback with a
   live version. Data lives here, keyed by figure kind (one entry today;
   split per-entry if the site grows). See README "Interactive figures". */
(function () {
  "use strict";

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --- small helpers ------------------------------------------------------ */
  function el(tag, cls) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    return node;
  }
  function fmtTime(t) {
    return t >= 2000 ? (t / 1000).toFixed(2) + " s" : Math.round(t) + " ms";
  }
  function pct(t, max) {
    return Math.min(100, Math.max(0, (t / max) * 100));
  }
  function niceStep(max) {
    var steps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000];
    for (var i = 0; i < steps.length; i++) {
      if (max / steps[i] <= 6.5) return steps[i];
    }
    return 10000;
  }
  function buildControls(items, onPick) {
    var wrap = el("div", "ix-controls");
    wrap.setAttribute("role", "group");
    var buttons = items.map(function (item) {
      var btn = el("button", "ix-btn");
      btn.type = "button";
      btn.textContent = item.label;
      btn.setAttribute("aria-pressed", item.active ? "true" : "false");
      if (item.active) btn.classList.add("is-active");
      btn.addEventListener("click", function () {
        onPick(item.key);
      });
      wrap.appendChild(btn);
      return { key: item.key, el: btn };
    });
    return {
      el: wrap,
      setActive: function (key) {
        buttons.forEach(function (b) {
          var on = b.key === key;
          b.el.classList.toggle("is-active", on);
          b.el.setAttribute("aria-pressed", on ? "true" : "false");
        });
      }
    };
  }
  function makeMarker(ev, max) {
    var marker = el("div", "ix-marker");
    if (ev.above) marker.classList.add("ix-above");
    else marker.classList.add("ix-below");
    var x = pct(ev.t, max);
    if (x < 7) marker.classList.add("ix-edge-l");
    if (x > 93) marker.classList.add("ix-edge-r");
    marker.style.left = x + "%";
    marker.tabIndex = 0;
    marker.setAttribute("role", "img");
    marker.setAttribute("aria-label", ev.label + " at " + fmtTime(ev.t) + ". " + ev.tip);
    var label = el("span", "ix-mlabel");
    label.textContent = ev.label;
    var tip = el("span", "ix-tip");
    tip.textContent = ev.tip;
    marker.appendChild(label);
    marker.appendChild(tip);
    return marker;
  }
  function makeBand(spec, max) {
    var band = el("div", "ix-band");
    band.style.left = pct(spec.from, max) + "%";
    band.style.width = (pct(spec.to, max) - pct(spec.from, max)) + "%";
    var label = el("span", "ix-mlabel");
    label.textContent = spec.label;
    band.appendChild(label);
    return band;
  }
  function startWhenVisible(fig, start) {
    if (!("IntersectionObserver" in window)) return;
    var seen = false;
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!seen && entry.isIntersecting) {
            seen = true;
            start();
            observer.disconnect();
          }
        });
      },
      { threshold: 0.45 }
    );
    observer.observe(fig);
  }

  /* --- startup replay: tap Scan, watch the camera come up ----------------- */
  var STARTUP = {
    order: ["a1", "p4", "p1"],
    modes: {
      a1: {
        label: "A1 vanilla \u00b7 cold",
        max: 6200,
        events: [
          { t: 0, label: "tap Scan", above: true,
            tip: "tab_tap \u2014 the scan page starts building." },
          { t: 21, label: "page mounted", above: false,
            tip: "scan_page_mounted at 21 ms; mobile_scanner's start() is requested moments later." },
          { t: 5760, label: "started + device open", above: true,
            tip: "start() completes at 5,760 ms (started) and the device is open at 5,769 ms (camera_open) \u2014 5.74 s of CameraX initialization and camera binding. The first visible frame is not instrumented in this app." }
        ],
        phases: [
          { to: 21, status: "building the scan page" },
          { to: 5760, status: "initializing CameraX and binding the camera \u2014 5.74 s of stack work" },
          { to: 6200, status: "device open; live frames follow (not instrumented here)" }
        ],
        end: "cold first entry: the camera does not exist until \u2248 5.8 s"
      },
      p4: {
        label: "P4 camera2 + ML Kit \u00b7 warm",
        max: 620,
        events: [
          { t: 0, label: "tap Scan", above: true,
            tip: "tab_tap; openCamera() follows at \u2248 3 ms (c2_open_requested)." },
          { t: 15.5, label: "texture repaints last frame", above: false,
            tip: "preview_painted at 15.5 ms \u2014 a frozen frame from the persistent texture, not live." },
          { t: 32.2, label: "device open", above: true,
            tip: "c2_opened \u2014 32 ms. On the emulator, driving camera2 directly opens the device fast." },
          { t: 111.5, label: "session configured", above: false,
            tip: "session_configured \u2014 112 ms. On the S24 FE this step ran bimodal (\u2248 340 ms vs \u2248 730 ms)." },
          { t: 150, label: "analysis + live frame", above: true,
            tip: "first_analysis_frame at 147 ms and first_frame at 153 ms: barcode scanning goes live at the same moment as the picture." }
        ],
        phases: [
          { to: 32, status: "opening the camera device" },
          { to: 112, status: "configuring the preview session" },
          { to: 153, status: "waiting for the first live frame" }
        ],
        end: "live preview with barcode analysis at \u2248 0.15 s"
      },
      p1: {
        label: "P1 prewarm \u00b7 warm",
        max: 620,
        events: [
          { t: 0, label: "tap Scan", above: true,
            tip: "tab_tap; warmup_already_bound at 0.2 ms \u2014 the camera is already open and streaming." },
          { t: 15, label: "page mounted + texture painted", above: false,
            tip: "scan_page_mounted \u2248 15 ms; preview_painted 12\u201334 ms \u2014 the pane shows a frozen frame from the prewarmed texture." },
          { band: [206, 524], t: 365, label: "live frames resume \u2014 206\u2013524 ms", above: true,
            tip: "first_frame 206\u2013524 ms (median 487): the gap between the frozen texture and live frames." }
        ],
        phases: [
          { to: 15, status: "mounting the scan page" },
          { to: 206, status: "frozen frame in the pane \u2014 never black" },
          { to: 524, status: "live frames resume" }
        ],
        end: "a frame by \u2248 15 ms; live by 0.5 s \u2014 the pane is never black"
      }
    }
  };

  function initStartup(fig) {
    var root = el("div", "ix-root");
    var stage = el("div", "ix-stage");
    var events = el("div", "ix-events");
    var playhead = el("div", "ix-playhead");
    var readout = el("div", "ix-readout");
    var clock = el("span", "ix-clock");
    clock.textContent = "0 ms";
    var status = el("span", "ix-status");
    var actions = el("div", "ix-actions");
    var playBtn = el("button", "ix-play");
    playBtn.type = "button";
    playBtn.textContent = "\u25b6 Play";
    var hint = el("span", "ix-hint");
    hint.textContent = "hover or focus a marker for the exact number";

    stage.appendChild(el("div", "ix-track"));
    stage.appendChild(events);
    stage.appendChild(playhead);
    readout.appendChild(clock);
    readout.appendChild(status);
    actions.appendChild(playBtn);
    actions.appendChild(hint);

    var controls = buildControls(
      STARTUP.order.map(function (key) {
        return { key: key, label: STARTUP.modes[key].label, active: key === "a1" };
      }),
      function (key) {
        mode = key;
        controls.setActive(key);
        render();
        play();
      }
    );
    root.appendChild(controls.el);
    root.appendChild(stage);
    root.appendChild(readout);
    root.appendChild(actions);

    var mode = "a1";
    var max = STARTUP.modes[mode].max;
    var t = 0;
    var raf = null;
    var playing = false;
    var t0 = 0;
    var markers = [];
    var bands = [];

    function render() {
      cancelAnimationFrame(raf);
      raf = null;
      playing = false;
      max = STARTUP.modes[mode].max;
      t = 0;
      events.innerHTML = "";
      markers = [];
      bands = [];
      playBtn.textContent = "\u25b6 Play";

      var step = niceStep(max);
      for (var v = 0; v <= max; v += step) {
        var tick = el("div", "ix-tick");
        var x = pct(v, max);
        tick.style.left = x + "%";
        if (x > 97) tick.style.marginLeft = "-1px";
        var tl = el("span");
        tl.textContent = v === 0 ? "0" : max >= 2000 ? v / 1000 + " s" : v + " ms";
        tick.appendChild(tl);
        events.appendChild(tick);
      }
      STARTUP.modes[mode].events.forEach(function (ev) {
        var node;
        if (ev.band) {
          node = makeBand(ev, max);
          bands.push({ node: node, from: ev.band[0] });
        } else {
          node = makeMarker(ev, max);
          markers.push({ node: node, t: ev.t });
        }
        events.appendChild(node);
      });
      paint();
    }

    function paint() {
      playhead.style.left = pct(t, max) + "%";
      clock.textContent = fmtTime(Math.min(t, max));
      var phases = STARTUP.modes[mode].phases;
      var text = STARTUP.modes[mode].end;
      for (var i = 0; i < phases.length; i++) {
        if (t < phases[i].to) {
          text = phases[i].status;
          break;
        }
      }
      if (t >= max) text = STARTUP.modes[mode].end;
      status.textContent = text;
      markers.forEach(function (m) {
        m.node.classList.toggle("is-on", t >= m.t);
      });
      bands.forEach(function (b) {
        b.node.classList.toggle("is-on", t >= b.from);
      });
    }

    function step(now) {
      t = ((now - t0) / animationMs()) * max;
      if (t >= max) {
        t = max;
        paint();
        playing = false;
        raf = null;
        playBtn.textContent = "\u21bb Replay";
        return;
      }
      paint();
      raf = requestAnimationFrame(step);
    }

    function animationMs() {
      return Math.max(1600, Math.min(3200, max * 0.5));
    }

    function play() {
      if (playing || reduceMotion) return;
      if (t >= max) t = 0;
      playing = true;
      playBtn.textContent = "\u275a\u275a Pause";
      t0 = performance.now() - (t / max) * animationMs();
      raf = requestAnimationFrame(step);
    }

    function pause() {
      if (!playing) return;
      cancelAnimationFrame(raf);
      raf = null;
      playing = false;
      playBtn.textContent = "\u25b6 Play";
    }

    playBtn.addEventListener("click", function () {
      if (playing) pause();
      else play();
    });

    fig.insertBefore(root, fig.querySelector("figcaption"));
    render();
    if (reduceMotion) {
      t = max;
      paint();
      playBtn.hidden = true;
    } else {
      startWhenVisible(fig, play);
    }
  }

  /* --- ranking inversion: swap emulator and phone -------------------------- */
  var RANKING = {
    max: 1500,
    order: ["emulator", "phone"],
    envs: {
      emulator: {
        label: "Emulator",
        color: "#28627b",
        headline: "On the emulator: P4 wins at 153 ms \u2014 and CameraX (P1, P3) trails at 368 ms.",
        values: { P1: 368, P2: 179, P3: 368, P4: 153 }
      },
      phone: {
        label: "Galaxy S24 FE",
        color: "#ac6538",
        headline: "On the phone: P1 wins at 685 ms \u2014 and P4, the emulator champion, is last at 1426 ms.",
        values: { P1: 685, P2: 916, P3: 834, P4: 1426 }
      }
    },
    apps: [
      { key: "P1", name: "P1 prewarm", engine: "CameraX" },
      { key: "P2", name: "P2 camera2", engine: "camera2-direct" },
      { key: "P3", name: "P3 ML Kit", engine: "CameraX + ML Kit" },
      { key: "P4", name: "P4 c2 + ML Kit", engine: "camera2-direct + ML Kit" }
    ]
  };

  function rankOf(values, key) {
    var sorted = Object.keys(values)
      .map(function (k) {
        return values[k];
      })
      .sort(function (a, b) {
        return a - b;
      });
    var v = values[key];
    var rank = sorted.indexOf(v) + 1;
    var tie = sorted.lastIndexOf(v) > sorted.indexOf(v);
    return "\u2116" + rank + (tie ? "=" : "");
  }

  function initRanking(fig) {
    var root = el("div", "ix-root");
    var env = "emulator";
    var headline = el("p", "ix-headline");
    headline.setAttribute("aria-live", "polite");
    var rows = el("div", "ix-rows");

    var rowNodes = RANKING.apps.map(function (app) {
      var row = el("div", "ix-row");
      var label = el("div", "ix-row-label");
      label.textContent = app.name;
      var sub = el("span");
      sub.textContent = app.engine;
      label.appendChild(sub);
      var barwrap = el("div", "ix-barwrap");
      var ghost = el("div", "ix-bar-ghost");
      var main = el("div", "ix-bar ix-bar-main");
      barwrap.appendChild(ghost);
      barwrap.appendChild(main);
      var value = el("div", "ix-value");
      var badge = el("div", "ix-badge");
      row.appendChild(label);
      row.appendChild(barwrap);
      row.appendChild(value);
      row.appendChild(badge);
      rows.appendChild(row);
      return { app: app, ghost: ghost, main: main, value: value, badge: badge };
    });

    function update() {
      var current = RANKING.envs[env];
      var otherKey = RANKING.order[0] === env ? RANKING.order[1] : RANKING.order[0];
      var other = RANKING.envs[otherKey];
      headline.textContent = current.headline;
      rowNodes.forEach(function (r) {
        var v = current.values[r.app.key];
        var ov = other.values[r.app.key];
        r.main.style.width = pct(v, RANKING.max) + "%";
        r.main.style.background = current.color;
        r.ghost.style.width = pct(ov, RANKING.max) + "%";
        r.value.textContent = v + " ms";
        r.value.style.color = current.color;
        r.badge.textContent = rankOf(current.values, r.app.key);
      });
    }

    var controls = buildControls(
      RANKING.order.map(function (key) {
        return { key: key, label: RANKING.envs[key].label, active: key === "emulator" };
      }),
      function (key) {
        env = key;
        controls.setActive(key);
        update();
      }
    );

    root.appendChild(controls.el);
    root.appendChild(headline);
    root.appendChild(rows);
    fig.insertBefore(root, fig.querySelector("figcaption"));
    update();
  }

  /* --- arbiter race: leaving Scan for RFID --------------------------------- */
  var ARBITER = {
    max: 1600,
    lanes: [
      {
        key: "old",
        label: "A1 / A2 \u00b7 mobile_scanner",
        statuses: [
          { to: 1287, text: "waiting for the camera to actually release \u2014 the stop() ack came back 1.28 s early" },
          { to: 1477, text: "camera free; starting the NFC session" },
          { to: 1600, text: "card readable \u2014 1.48 s after the tap" }
        ],
        events: [
          { t: 5, label: "stop() acks", above: true,
            tip: "the plugin acknowledges the stop in 3\u201384 ms \u2014 and it is not true yet." },
          { t: 1287, label: "camera released", above: false,
            tip: "the OS camera-availability callback fires \u2014 1,287 ms after the tab tap (phone median)." },
          { t: 1477, label: "RFID ok", above: true,
            tip: "the NFC session starts \u2014 1,477 ms after the tap." }
        ],
        band: { from: 188, to: 1287, label: "\u2248 1.1 s of camera dead time", reveal: 384 }
      },
      {
        key: "new",
        label: "P1\u2013P4 \u00b7 plugin",
        statuses: [
          { to: 188, text: "unbinding the camera (the texture stays warm)" },
          { to: 384, text: "camera free \u2014 1.09 s earlier than the old path" },
          { to: 1600, text: "card readable \u2014 0.38 s after the tap" }
        ],
        events: [
          { t: 5, label: "stop() acks", above: true,
            tip: "same ack, same timing \u2014 this agreement never changed." },
          { t: 188, label: "camera released", above: false,
            tip: "availability callback \u2014 160\u2013220 ms after the tap on the phone." },
          { t: 384, label: "RFID ok", above: true,
            tip: "NFC session starts \u2014 356\u2013394 ms on the phone." }
        ]
      }
    ]
  };

  function initArbiter(fig) {
    var root = el("div", "ix-root");
    var race = el("div", "ix-race");
    var player = el("div", "ix-player");
    var actions = el("div", "ix-actions");
    var playBtn = el("button", "ix-play");
    playBtn.type = "button";
    playBtn.textContent = "\u25b6 Play the handoff";
    var clock = el("span", "ix-clock");
    clock.textContent = "0 ms";
    var hint = el("span", "ix-hint");
    hint.textContent = "hover or focus a marker for the exact number";
    actions.appendChild(playBtn);
    actions.appendChild(clock);
    actions.appendChild(hint);

    var laneNodes = ARBITER.lanes.map(function (lane) {
      var wrap = el("div", "ix-lane" + (lane.key === "new" ? " is-new" : ""));
      var label = el("div", "ix-lane-label");
      label.appendChild(el("span", "ix-lane-dot"));
      label.appendChild(document.createTextNode(lane.label));
      var stage = el("div", "ix-lane-stage");
      stage.appendChild(el("div", "ix-track"));
      var markers = [];
      lane.events.forEach(function (ev) {
        var m = makeMarker(ev, ARBITER.max);
        stage.appendChild(m);
        markers.push({ node: m, t: ev.t });
      });
      var bandNode = null;
      if (lane.band) {
        bandNode = makeBand(lane.band, ARBITER.max);
        stage.appendChild(bandNode);
      }
      var status = el("div", "ix-lane-status");
      wrap.appendChild(label);
      wrap.appendChild(stage);
      wrap.appendChild(status);
      race.appendChild(wrap);
      return { def: lane, markers: markers, band: bandNode, status: status };
    });
    race.appendChild(player);

    var t = 0;
    var raf = null;
    var playing = false;
    var t0 = 0;
    var DURATION = 2600;

    function paint() {
      player.style.left = pct(t, ARBITER.max) + "%";
      clock.textContent = fmtTime(Math.min(t, ARBITER.max));
      laneNodes.forEach(function (lane) {
        lane.markers.forEach(function (m) {
          m.node.classList.toggle("is-on", t >= m.t);
        });
        if (lane.band) {
          lane.band.classList.toggle("is-on", t >= lane.def.band.reveal);
        }
        var text = lane.def.statuses[lane.def.statuses.length - 1].text;
        for (var i = 0; i < lane.def.statuses.length; i++) {
          if (t < lane.def.statuses[i].to) {
            text = lane.def.statuses[i].text;
            break;
          }
        }
        lane.status.textContent = text;
        lane.status.classList.toggle("is-done", t >= lane.def.events[lane.def.events.length - 1].t);
      });
    }

    function step(now) {
      t = ((now - t0) / DURATION) * ARBITER.max;
      if (t >= ARBITER.max) {
        t = ARBITER.max;
        paint();
        playing = false;
        raf = null;
        playBtn.textContent = "\u21bb Replay";
        return;
      }
      paint();
      raf = requestAnimationFrame(step);
    }

    function play() {
      if (playing || reduceMotion) return;
      if (t >= ARBITER.max) t = 0;
      playing = true;
      playBtn.textContent = "\u275a\u275a Pause";
      t0 = performance.now() - (t / ARBITER.max) * DURATION;
      raf = requestAnimationFrame(step);
    }

    playBtn.addEventListener("click", function () {
      if (playing) {
        cancelAnimationFrame(raf);
        raf = null;
        playing = false;
        playBtn.textContent = "\u25b6 Play";
      } else {
        play();
      }
    });

    root.appendChild(race);
    root.appendChild(actions);
    fig.insertBefore(root, fig.querySelector("figcaption"));
    paint();
    if (reduceMotion) {
      t = ARBITER.max;
      paint();
      playBtn.hidden = true;
    } else {
      startWhenVisible(fig, play);
    }
  }

  /* --- bootstrap ----------------------------------------------------------- */
  Array.prototype.slice
    .call(document.querySelectorAll("figure[data-ix]"))
    .forEach(function (fig) {
      var img = fig.querySelector("img.ix-fallback");
      if (!img) return;
      var kind = fig.getAttribute("data-ix");
      if (kind === "startup") initStartup(fig);
      else if (kind === "ranking") initRanking(fig);
      else if (kind === "arbiter") initArbiter(fig);
      else return;
      img.parentNode.removeChild(img);
    });
})();
