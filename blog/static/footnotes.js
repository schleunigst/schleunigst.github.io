/* footnotes.js -- popover footnotes.
   Markup (emitted by build.py):
     <span class="fn">
       <button class="fn-mark" aria-describedby="fnpop-1" aria-expanded="false">[1]</button>
       <span class="fn-pop" role="tooltip" id="fnpop-1">... <a href="#fn-1">note</a></span>
     </span>
   Hover and keyboard focus open the popover via CSS; this script adds
   click/tap pinning, outside-click close, and Escape to close. */
(function () {
  "use strict";

  function closeAll(except) {
    document.querySelectorAll(".fn.fn-open").forEach(function (fn) {
      if (fn === except) return;
      fn.classList.remove("fn-open");
      var mark = fn.querySelector(".fn-mark");
      if (mark) mark.setAttribute("aria-expanded", "false");
    });
  }

  document.addEventListener("click", function (event) {
    var mark = event.target.closest(".fn-mark");
    if (mark) {
      var fn = mark.parentElement;
      var open = fn.classList.toggle("fn-open");
      mark.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) closeAll(fn);
      return;
    }
    if (!event.target.closest(".fn-pop")) closeAll(null);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    closeAll(null);
    var active = document.activeElement;
    if (active && active.classList.contains("fn-mark")) active.blur();
  });
})();
