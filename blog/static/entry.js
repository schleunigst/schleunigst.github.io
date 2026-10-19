/* entry.js -- small enhancements for entry pages.
   - reading progress bar
   - roadmap "active section" state while scrolling
   - smooth anchor scrolling (respects prefers-reduced-motion)
   - click-to-keep figures: add class="fig-keep" to a <figure> */
(function () {
  "use strict";

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --- reading progress -------------------------------------------------- */
  var bar = document.getElementById("reading-progress");
  if (bar) {
    var update = function () {
      var doc = document.documentElement;
      var max = doc.scrollHeight - doc.clientHeight;
      bar.style.width = max > 0 ? (doc.scrollTop / max) * 100 + "%" : "0";
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
  }

  /* --- roadmap active state ---------------------------------------------- */
  var cards = Array.prototype.slice.call(
    document.querySelectorAll(".roadmap .rm-card")
  );
  var headings = Array.prototype.slice.call(
    document.querySelectorAll("article.entry h2[id]")
  );
  if (cards.length && headings.length && "IntersectionObserver" in window) {
    var byId = {};
    cards.forEach(function (card) {
      var hash = card.getAttribute("href") || "";
      if (hash.charAt(0) === "#") byId[hash.slice(1)] = card;
    });
    var setActive = function (id) {
      cards.forEach(function (card) {
        card.classList.toggle("is-active", card === byId[id]);
      });
    };
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) setActive(entry.target.id);
        });
      },
      { rootMargin: "0px 0px -70% 0px", threshold: 0 }
    );
    headings.forEach(function (h) {
      if (byId[h.id]) observer.observe(h);
    });
  }

  /* --- smooth anchor scrolling ------------------------------------------- */
  document.addEventListener("click", function (event) {
    if (reduceMotion) return;
    var link = event.target.closest('a[href^="#"]');
    if (!link) return;
    var id = decodeURIComponent(link.getAttribute("href").slice(1));
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    if (window.history && window.history.pushState) {
      window.history.pushState(null, "", "#" + id);
    }
  });

  /* --- click-to-keep figures --------------------------------------------- */
  Array.prototype.slice.call(document.querySelectorAll(".fig-keep")).forEach(
    function (figure) {
      figure.setAttribute("tabindex", "0");
      figure.setAttribute("role", "group");
      var toggle = function () {
        figure.classList.toggle("is-kept");
      };
      figure.addEventListener("click", toggle);
      figure.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggle();
        }
      });
    }
  );
})();
