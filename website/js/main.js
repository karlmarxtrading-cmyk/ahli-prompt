/* Jago Prompt — progressive enhancement, tanpa dependensi atau permintaan jaringan. */
(function () {
  "use strict";

  var doc = document.documentElement;
  var motionQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var reduceMotion = Boolean(motionQuery && motionQuery.matches);
  doc.classList.add("js");

  /* ---------- Tahun di footer ---------- */
  var yearEl = document.querySelector("[data-year]");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* ---------- Menu mobile: disclosure, bukan dialog ---------- */
  var header = document.querySelector("[data-header]");
  var toggle = document.querySelector("[data-menu-toggle]");
  var nav = document.querySelector("[data-nav]");
  var mobileQuery = window.matchMedia ? window.matchMedia("(max-width: 960px)") : null;

  function isMobile() { return mobileQuery ? mobileQuery.matches : window.innerWidth <= 960; }
  function focusWithoutScroll(el) {
    if (!el) return;
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
  }
  function menuIsOpen() { return Boolean(toggle && toggle.getAttribute("aria-expanded") === "true"); }
  function setMenu(open, restoreFocus) {
    if (!toggle || !nav) return;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Tutup menu" : "Buka menu");
    nav.classList.toggle("is-open", open);
    if (restoreFocus && isMobile()) focusWithoutScroll(toggle);
  }
  function focusSection(target) {
    if (!target) return;
    var addedTabindex = !target.hasAttribute("tabindex");
    if (addedTabindex) target.setAttribute("tabindex", "-1");
    focusWithoutScroll(target);
    if (addedTabindex) {
      target.addEventListener("blur", function removeTemporaryTabindex() {
        target.removeAttribute("tabindex");
        target.removeEventListener("blur", removeTemporaryTabindex);
      });
    }
  }
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = !menuIsOpen();
      setMenu(open);
      if (open) {
        void nav.offsetWidth; /* terapkan gaya 'terbuka' dahulu; elemen visibility:hidden tidak dapat menerima fokus */
        focusWithoutScroll(nav.querySelector("a"));
      }
    });
    nav.addEventListener("click", function (e) {
      var link = e.target.closest("a");
      if (!link) return;
      var wasOpen = menuIsOpen() && isMobile();
      setMenu(false);
      if (wasOpen) {
        var href = link.getAttribute("href") || "";
        var target = href.charAt(0) === "#" ? document.getElementById(href.slice(1)) : null;
        if (target) focusSection(target);
        else focusWithoutScroll(toggle);
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menuIsOpen()) {
        e.preventDefault();
        setMenu(false, true);
      }
    });
    document.addEventListener("click", function (e) {
      if (menuIsOpen() && header && !header.contains(e.target)) {
        setMenu(false, nav.contains(document.activeElement));
      }
    });
    document.addEventListener("focusin", function (e) {
      if (menuIsOpen() && header && !header.contains(e.target)) setMenu(false);
    });
    window.addEventListener("resize", function () {
      if (!isMobile()) setMenu(false);
      else if (!menuIsOpen() && nav.contains(document.activeElement)) focusWithoutScroll(toggle);
    });
  }

  /* ---------- Header, kembali ke atas, dan navigasi aktif ---------- */
  var toTop = document.querySelector("[data-to-top]");
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav-link"));
  var sections = links.map(function (link) {
    var href = link.getAttribute("href") || "";
    return { link: link, target: href.charAt(0) === "#" ? document.getElementById(href.slice(1)) : null };
  }).filter(function (item) { return Boolean(item.target); });
  var scrollScheduled = false;
  function updateScrollState() {
    scrollScheduled = false;
    var y = window.scrollY || window.pageYOffset || 0;
    if (header) header.classList.toggle("is-scrolled", y > 8);
    if (toTop) toTop.classList.toggle("is-visible", y > 700);
    if (!sections.length) return;
    var threshold = (header ? header.offsetHeight : 0) + Math.min(window.innerHeight * 0.24, 200);
    /* Pilih section yang paling dekat di atas ambang berdasarkan POSISI halaman, bukan urutan tautan:
       urutan menu (Visual Brand sebelum Konten Affiliate) berbeda dari urutan section. */
    var active = sections[0];
    var activeTop = -Infinity;
    sections.forEach(function (item) {
      var top = item.target.getBoundingClientRect().top;
      if (top <= threshold && top >= activeTop) { active = item; activeTop = top; }
    });
    sections.forEach(function (item) {
      var current = item === active;
      item.link.classList.toggle("is-active", current);
      if (current) item.link.setAttribute("aria-current", "location");
      else item.link.removeAttribute("aria-current");
    });
  }
  function requestScrollUpdate() {
    if (scrollScheduled) return;
    scrollScheduled = true;
    if (window.requestAnimationFrame) window.requestAnimationFrame(updateScrollState);
    else updateScrollState();
  }
  window.addEventListener("scroll", requestScrollUpdate, { passive: true });
  window.addEventListener("resize", requestScrollUpdate);
  window.addEventListener("load", requestScrollUpdate);
  updateScrollState();

  /* ---------- Reveal satu kali; semua informasi tetap tersedia tanpa JS ---------- */
  var reveals = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var revealObserver = null;
  function revealAll() {
    if (revealObserver) revealObserver.disconnect();
    reveals.forEach(function (el) { el.classList.add("is-visible"); });
  }
  if (!reduceMotion && "IntersectionObserver" in window) {
    revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -4% 0px", threshold: 0 });
    reveals.forEach(function (el, i) {
      el.style.transitionDelay = (i % 4) * 50 + "ms";
      revealObserver.observe(el);
    });
  } else revealAll();

  /* Hasil hero hadir sejak awal. Tidak ada loop ketik yang menyembunyikan gambar/prompt. */
  var demo = document.querySelector("[data-demo]");
  if (demo) {
    demo.classList.remove("is-anim", "is-typing");
    demo.classList.add("show-result", "show-prompt");
  }

  /* ---------- Semua video: kontrol native, pemulihan terpisah, tanpa autoplay ---------- */
  var videos = Array.prototype.slice.call(document.querySelectorAll("[data-video]"));
  videos.forEach(function (video) {
    var unit = video.closest("[data-media-unit]") || video.parentElement;
    var status = unit.querySelector("[data-video-status]");
    var retry = unit.querySelector("[data-video-retry]");
    var box = unit.querySelector(".video-status-box");
    function errorState(failed) {
      if (status) status.textContent = failed ? "Video belum dapat diputar. Coba lagi atau buka file videonya." : "";
      if (box) box.classList.toggle("has-error", failed);
      if (retry) retry.hidden = !failed;
    }
    video.addEventListener("error", function () { errorState(true); });
    Array.prototype.forEach.call(video.querySelectorAll("source"), function (source) {
      source.addEventListener("error", function () { errorState(true); });
    });
    video.addEventListener("playing", function () {
      errorState(false);
      videos.forEach(function (other) { if (other !== video && !other.paused) other.pause(); });
    });
    video.addEventListener("loadeddata", function () { errorState(false); });
    if (retry) retry.addEventListener("click", function () {
      errorState(false);
      try {
        video.load();
        var promise = video.play();
        if (promise && promise.catch) promise.catch(function (err) {
          if (!err || err.name !== "NotAllowedError") errorState(true);
        });
      } catch (e) { errorState(true); }
    });
  });
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) videos.forEach(function (video) { video.pause(); });
  });
  window.addEventListener("pagehide", function () {
    videos.forEach(function (video) { video.pause(); });
  });

  /* ---------- Storyboard: statis sampai pengguna memilih Putar ---------- */
  var board = document.querySelector("[data-storyboard]");
  var play = document.querySelector("[data-storyboard-toggle]");
  var head = document.querySelector("[data-timeline-head]");
  var status = document.querySelector("[data-storyboard-status]");
  var frames = board ? Array.prototype.slice.call(board.querySelectorAll(".sb-frame")) : [];
  var sceneButtons = Array.prototype.slice.call(document.querySelectorAll("[data-scene-select]"));
  var durations = frames.map(function (frame, index) {
    var value = Number(frame.getAttribute("data-duration"));
    return value > 0 ? value : ([2000, 3000, 3000, 2000][index] || 2500);
  });
  var total = durations.reduce(function (sum, value) { return sum + value; }, 0);
  var current = 0;
  var timer = null;
  var playing = false;
  var inView = true;

  function setStatus(message) { if (status) status.textContent = message; }
  function updateControls() {
    if (board) board.classList.toggle("is-playing", playing);
    if (!play) return;
    play.hidden = reduceMotion || !frames.length;
    play.setAttribute("aria-pressed", String(playing));
    play.textContent = playing ? "Hentikan contoh alur" : "Putar contoh alur";
  }
  function showScene(index, animate) {
    current = index;
    frames.forEach(function (frame, i) {
      frame.classList.toggle("is-current", i === index);
      if (i === index) frame.setAttribute("aria-current", "step");
      else frame.removeAttribute("aria-current");
    });
    sceneButtons.forEach(function (button) {
      button.setAttribute("aria-pressed", String(Number(button.getAttribute("data-scene-select")) === index));
    });
    if (head && total) {
      var elapsed = durations.slice(0, index).reduce(function (sum, value) { return sum + value; }, 0);
      head.style.transition = "none";
      head.style.left = (elapsed / total * 100) + "%";
      if (animate && !reduceMotion) {
        void head.offsetWidth;
        head.style.transition = "left " + durations[index] + "ms linear";
        head.style.left = "calc(" + ((elapsed + durations[index]) / total * 100) + "% - 2px)";
      }
    }
  }
  function stopPlayback(message) {
    if (timer !== null) { window.clearTimeout(timer); timer = null; }
    if (head && playing) {
      var position = window.getComputedStyle(head).left;
      head.style.transition = "none";
      var trackWidth = head.parentElement ? head.parentElement.clientWidth : 0;
      head.style.left = trackWidth ? (parseFloat(position) / trackWidth * 100) + "%" : position;
    }
    playing = false;
    updateControls();
    if (message) setStatus(message);
  }
  function advance() {
    if (!playing || document.hidden || !inView || reduceMotion) {
      stopPlayback("Contoh alur dihentikan. Semua adegan tetap dapat dibaca.");
      return;
    }
    showScene(current, true);
    timer = window.setTimeout(function () {
      timer = null;
      if (current + 1 < frames.length) {
        current += 1;
        advance();
      } else {
        stopPlayback("Contoh alur selesai. Pilih Putar untuk melihatnya kembali.");
      }
    }, durations[current]);
  }
  if (board && frames.length) {
    if (!board.id) board.id = "storyboard-preview";
    if (play) {
      play.setAttribute("aria-controls", board.id);
      play.addEventListener("click", function () {
        if (playing) {
          stopPlayback("Contoh alur dihentikan. Semua adegan tetap dapat dibaca.");
          return;
        }
        if (reduceMotion || document.hidden) return;
        if (!inView) {
          board.scrollIntoView({ block: "nearest", behavior: "auto" });
          var bounds = board.getBoundingClientRect();
          inView = bounds.bottom > 0 && bounds.top < window.innerHeight;
        }
        current = 0;
        playing = true;
        updateControls();
        setStatus("Memutar contoh urutan empat adegan selama 10 detik. Ini bukan video hasil generasi.");
        advance();
      });
    }
    sceneButtons.forEach(function (button) {
      var index = Number(button.getAttribute("data-scene-select"));
      if (!Number.isInteger(index) || index < 0 || index >= frames.length) return;
      button.hidden = false;
      button.addEventListener("click", function () {
        stopPlayback();
        showScene(index, false);
        setStatus("Adegan " + (index + 1) + " dari " + frames.length + " dipilih.");
      });
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          inView = entry.isIntersecting;
          if (!inView && playing) stopPlayback("Contoh alur dihentikan saat keluar layar.");
        });
      }, { threshold: 0 }).observe(board);
    }
    document.addEventListener("visibilitychange", function () {
      if (document.hidden && playing) stopPlayback("Contoh alur dihentikan saat tab tidak aktif.");
    });
    window.addEventListener("pagehide", function () { stopPlayback(); });
    showScene(0, false);
    updateControls();
    if (head) head.hidden = reduceMotion;
  }

  /* Pengaturan sistem dapat berubah ketika halaman masih terbuka. */
  function onMotionChange(event) {
    reduceMotion = event.matches;
    if (reduceMotion) {
      revealAll();
      stopPlayback("Animasi dinonaktifkan sesuai pengaturan perangkat. Semua adegan tetap dapat dibaca.");
    }
    if (head) head.hidden = reduceMotion;
    updateControls();
  }
  if (motionQuery) {
    if (motionQuery.addEventListener) motionQuery.addEventListener("change", onMotionChange);
    else if (motionQuery.addListener) motionQuery.addListener(onMotionChange);
  }
})();
