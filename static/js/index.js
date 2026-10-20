/* DevCircle site-wide behaviour: theme, back-to-top, alerts, cart stepper, double-submit guard */
(function () {
    'use strict';
    var root = document.documentElement;

    /* ---- dark / light theme (saved choice is applied early in base.html) ---- */
    var toggle = document.getElementById('theme-toggle');
    function syncToggle() {
        if (!toggle) return;
        var dark = root.getAttribute('data-bs-theme') === 'dark';
        var icon = toggle.querySelector('i');
        if (icon) icon.className = dark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        toggle.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    }
    if (toggle) {
        toggle.addEventListener('click', function () {
            var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-bs-theme', next);
            try { localStorage.setItem('theme', next); } catch (e) { /* private mode */ }
            syncToggle();
        });
        syncToggle();
    }

    /* ---- back to top ---- */
    var topBtn = document.getElementById('back-to-top');
    if (topBtn) {
        window.addEventListener('scroll', function () { topBtn.hidden = window.scrollY < 500; }, { passive: true });
        topBtn.addEventListener('click', function () {
            var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
        });
    }

    /* ---- auto-dismiss flash messages ---- */
    document.querySelectorAll('.alert-dismissible').forEach(function (el) {
        setTimeout(function () {
            if (window.bootstrap && document.body.contains(el)) window.bootstrap.Alert.getOrCreateInstance(el).close();
        }, 7000);
    });

    /* ---- stop double submits (double charges, duplicate cart rows) ---- */
    function lock(form) {
        form.querySelectorAll('button[type="submit"]').forEach(function (btn) {
            btn.disabled = true;
            btn.setAttribute('data-original', btn.innerHTML);
            if (!btn.classList.contains('pcard-add')) {
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Please wait';
            }
        });
    }
    function unlock(form) {
        form.querySelectorAll('button[type="submit"]').forEach(function (btn) {
            btn.disabled = false;
            if (btn.hasAttribute('data-original')) btn.innerHTML = btn.getAttribute('data-original');
        });
    }
    document.querySelectorAll('form[data-once]').forEach(function (form) {
        form.addEventListener('submit', function () {
            if (!form.checkValidity()) return;
            setTimeout(function () { lock(form); }, 0);
        });
    });
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) document.querySelectorAll('form[data-once]').forEach(unlock);
    });

    /* ---- cart quantity stepper: +/- buttons save automatically ---- */
    document.querySelectorAll('form[data-autosubmit]').forEach(function (form) {
        var input = form.querySelector('input[name="quant"]');
        var timer = null;
        function clamp() {
            var min = Number(input.min) || 1, max = Number(input.max) || 50;
            var v = parseInt(input.value, 10);
            if (isNaN(v) || v < min) v = min;
            if (v > max) v = max;
            input.value = v;
        }
        function queueSave() {
            clearTimeout(timer);
            timer = setTimeout(function () { if (form.requestSubmit) form.requestSubmit(); else form.submit(); }, 650);
        }
        form.querySelectorAll('[data-step]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                input.value = (parseInt(input.value, 10) || 1) + Number(btn.getAttribute('data-step'));
                clamp();
                queueSave();
            });
        });
        input.addEventListener('change', function () { clamp(); queueSave(); });
    });
})();
