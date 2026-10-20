/* Show/hide password. Works for any number of fields: <button class="toggle-password" data-target="#id"> */
(function () {
    'use strict';
    document.querySelectorAll('.toggle-password').forEach(function (btn) {
        var input = document.querySelector(btn.getAttribute('data-target'));
        if (!input) return;
        var icon = btn.querySelector('i');

        btn.addEventListener('click', function () {
            var reveal = input.type === 'password';
            input.type = reveal ? 'text' : 'password';
            btn.setAttribute('aria-pressed', String(reveal));
            btn.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
            if (icon) icon.className = reveal ? 'bi bi-eye-slash-fill' : 'bi bi-eye-fill';
            input.focus();
        });
    });
})();
