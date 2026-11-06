/* triage.js -- one interactive figure: accept or reject machine-proposed edges.
   Self-contained; touches only figures carrying data-ix="triage", and only
   after a static <img class="ix-fallback"> is present. No dependencies, no
   build step, no network. */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";

  function el(tag, cls) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    return node;
  }
  function svgEl(tag, attrs) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, k)) node.setAttribute(k, attrs[k]);
    }
    return node;
  }

  var TRIAGE = {
    w: 640,
    h: 214,
    clusters: [
      { id: "capture", label: "capture", x: 150, colour: "#28627b" },
      { id: "sync", label: "sync", x: 490, colour: "#ac6538" }
    ],
    nodes: [
      { id: "i1", label: "one gesture", cluster: "capture", x: 150, y: 62 },
      { id: "i2", label: "share sheet", cluster: "capture", x: 72, y: 158 },
      { id: "i3", label: "widget link", cluster: "capture", x: 228, y: 158 },
      { id: "i4", label: "one writer", cluster: "sync", x: 490, y: 62 },
      { id: "i5", label: "HLC order", cluster: "sync", x: 412, y: 158 },
      { id: "i6", label: "event union", cluster: "sync", x: 568, y: 158 }
    ],
    proposals: [
      {
        id: "p1", from: "i1", to: "i2", type: "refines", conf: "0.82",
        prov: "agent:omp",
        why: "A share-sheet entry is a narrower instance of the one-gesture rule. Same failure mode, less surface."
      },
      {
        id: "p2", from: "i3", to: "i1", type: "supports", conf: "0.71",
        prov: "extractor:bge-m3@1.2",
        why: "Embedding distance 0.19 and shared vocabulary (\u201cone gesture\u201d). A model's guess, offered as one."
      },
      {
        id: "p3", from: "i4", to: "i6", type: "refines", conf: "0.88",
        prov: "agent:omp",
        why: "HLC supplies the ordering that a union of events leaves undefined. Without it, \u201clatest\u201d is not a fact."
      }
    ]
  };

  function init(fig) {
    var byId = {};
    var state = {};
    var edges = {};

    var root = el("div", "ix-triage");
    var svg = svgEl("svg", {
      viewBox: "0 0 " + TRIAGE.w + " " + TRIAGE.h,
      "class": "ix-tgraph",
      role: "img",
      "aria-label": "Six ideas in two clusters. Dashed edges are machine proposals; they become solid only when accepted."
    });

    var defs = svgEl("defs");
    var marker = svgEl("marker", {
      id: "ix-tarr", viewBox: "0 0 10 10", refX: "9", refY: "5",
      markerWidth: "6", markerHeight: "6", orient: "auto"
    });
    marker.appendChild(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", "class": "ix-tarr" }));
    defs.appendChild(marker);
    svg.appendChild(defs);

    var gCluster = svgEl("g");
    var gEdge = svgEl("g");
    var gNode = svgEl("g");
    svg.appendChild(gCluster);
    svg.appendChild(gEdge);
    svg.appendChild(gNode);

    TRIAGE.clusters.forEach(function (c) {
      var label = svgEl("text", {
        x: c.x, y: 22, "text-anchor": "middle", "class": "ix-tcluster"
      });
      label.setAttribute("fill", c.colour);
      label.textContent = c.label;
      gCluster.appendChild(label);
    });

    TRIAGE.nodes.forEach(function (n) {
      byId[n.id] = n;
      var g = svgEl("g", { "class": "ix-tnode is-" + n.cluster });
      g.appendChild(svgEl("rect", {
        x: n.x - 52, y: n.y - 16, width: 104, height: 32, rx: 8
      }));
      var t = svgEl("text", { x: n.x, y: n.y + 4, "text-anchor": "middle" });
      t.textContent = n.label;
      g.appendChild(t);
      gNode.appendChild(g);
    });

    function endpoints(a, b) {
      var dx = b.x - a.x;
      var dy = b.y - a.y;
      var t = Math.min(
        52 / Math.max(Math.abs(dx), 0.001),
        16 / Math.max(Math.abs(dy), 0.001)
      );
      return {
        x1: a.x + dx * t, y1: a.y + dy * t,
        x2: b.x - dx * t, y2: b.y - dy * t
      };
    }

    function drawEdge(p) {
      var e = endpoints(byId[p.from], byId[p.to]);
      var g = svgEl("g", { "class": "ix-tedge is-proposed" });
      g.appendChild(svgEl("line", {
        x1: e.x1, y1: e.y1, x2: e.x2, y2: e.y2, "marker-end": "url(#ix-tarr)"
      }));
      var label = svgEl("text", {
        x: (e.x1 + e.x2) / 2, y: (e.y1 + e.y2) / 2 - 6, "text-anchor": "middle"
      });
      label.textContent = p.type + " " + p.conf;
      g.appendChild(label);
      gEdge.appendChild(g);
      edges[p.id] = g;
    }

    var tally = el("p", "ix-tstat");
    tally.setAttribute("aria-live", "polite");
    var cards = el("div", "ix-tcards");
    var log = el("div", "ix-tlog");
    log.setAttribute("aria-live", "polite");
    var actions = el("div", "ix-tactions");
    var reset = el("button", "ix-tbtn ix-treset");
    reset.type = "button";
    reset.textContent = "Reset queue";
    var hint = el("span", "ix-thint");
    hint.textContent = "Nothing is deleted. A rejection is an event too.";
    actions.appendChild(reset);
    actions.appendChild(hint);

    function refresh() {
      var accepted = 0;
      var dismissed = 0;
      TRIAGE.proposals.forEach(function (p) {
        if (state[p.id] === "accepted") accepted++;
        if (state[p.id] === "dismissed") dismissed++;
      });
      var open = TRIAGE.proposals.length - accepted - dismissed;
      tally.textContent =
        (open === 0 ? "queue empty" : open + " awaiting review") +
        " \u00b7 " + accepted + " accepted \u00b7 " + dismissed + " dismissed";
    }

    function addLog(text, cls) {
      var line = el("div", "ix-tlogline");
      if (cls) line.className += " " + cls;
      line.textContent = text;
      log.appendChild(line);
      while (log.children.length > 5) log.removeChild(log.firstChild);
    }

    function decide(p, verdict) {
      if (state[p.id]) return;
      state[p.id] = verdict;
      var card = cards.querySelector('[data-proposal="' + p.id + '"]');
      var buttons = card.querySelector(".ix-tbtns");
      if (verdict === "accepted") {
        card.className += " is-accepted";
        buttons.textContent = "accepted \u00b7 edge.asserted";
        edges[p.id].setAttribute("class", "ix-tedge is-on");
        addLog("edge.asserted  " + p.from + " \u2192 " + p.to + "  " + p.type, "is-add");
      } else {
        card.className += " is-dismissed";
        buttons.textContent = "dismissed \u00b7 proposal.rejected";
        gEdge.removeChild(edges[p.id]);
        addLog("proposal.rejected  " + p.id + "  kept in the log", "is-drop");
      }
      refresh();
      var next = cards.querySelector(
        ".ix-tcard:not(.is-accepted):not(.is-dismissed) .ix-taccept"
      );
      if (next) next.focus();
    }

    function buildCards() {
      cards.textContent = "";
      TRIAGE.proposals.forEach(function (p) {
        var card = el("div", "ix-tcard");
        card.setAttribute("data-proposal", p.id);
        var head = el("div", "ix-thead");
        var route = el("span", "ix-troute");
        route.textContent = p.from + " \u2192 " + p.to;
        var type = el("span", "ix-ttype");
        type.textContent = p.type;
        var conf = el("span", "ix-tconf");
        conf.textContent = "\u03c3 " + p.conf;
        var prov = el("span", "ix-tprov");
        prov.textContent = p.prov;
        head.appendChild(route);
        head.appendChild(type);
        head.appendChild(conf);
        head.appendChild(prov);
        var why = el("p", "ix-twhy");
        why.textContent = p.why;
        var btns = el("div", "ix-tbtns");
        var yes = el("button", "ix-tbtn ix-taccept");
        yes.type = "button";
        yes.textContent = "Accept";
        yes.setAttribute("aria-label",
          "Accept " + p.type + " from " + p.from + " to " + p.to);
        var no = el("button", "ix-tbtn ix-treject");
        no.type = "button";
        no.textContent = "Reject";
        no.setAttribute("aria-label",
          "Reject proposal " + p.id);
        yes.addEventListener("click", function () { decide(p, "accepted"); });
        no.addEventListener("click", function () { decide(p, "dismissed"); });
        btns.appendChild(yes);
        btns.appendChild(no);
        card.appendChild(head);
        card.appendChild(why);
        card.appendChild(btns);
        cards.appendChild(card);
      });
    }

    reset.addEventListener("click", function () {
      state = {};
      edges = {};
      gEdge.textContent = "";
      log.textContent = "";
      TRIAGE.proposals.forEach(drawEdge);
      buildCards();
      refresh();
      reset.blur();
    });

    TRIAGE.proposals.forEach(drawEdge);
    buildCards();
    refresh();

    root.appendChild(svg);
    root.appendChild(tally);
    root.appendChild(cards);
    root.appendChild(log);
    root.appendChild(actions);
    fig.insertBefore(root, fig.querySelector("figcaption"));
  }

  Array.prototype.slice
    .call(document.querySelectorAll('figure[data-ix="triage"]'))
    .forEach(function (fig) {
      var img = fig.querySelector("img.ix-fallback");
      if (!img) return;
      init(fig);
      img.parentNode.removeChild(img);
    });
})();
