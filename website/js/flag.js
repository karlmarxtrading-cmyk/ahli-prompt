/* Jago Prompt — penanda JS aktif sebelum render pertama (mencegah menu mobile bergeser).
   Dicabut lagi bila main.js gagal dimuat, sehingga navigasi tanpa-JS tetap tampil.
   Berkas terpisah, bukan inline, agar Content-Security-Policy script-src 'self' dapat diterapkan. */
(function () {
  "use strict";
  var doc = document.documentElement;
  doc.classList.add("js");
  window.addEventListener("error", function (event) {
    var el = event && event.target;
    if (el && el.tagName === "SCRIPT" && /(^|\/)main\.js(\?|$)/.test(el.getAttribute("src") || "")) {
      doc.classList.remove("js");
    }
  }, true);
})();
