/**
 * Sign-in page: OAuth form submit (Google/Microsoft/Apple) - reads auth base from data attribute
 */
(function() {
    function initOAuthButtons() {
        var form = document.getElementById('oauth-form');
        if (!form) return;

        var authBase = form.getAttribute('data-auth-base') || '';
        document.querySelectorAll('.oauth-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var provider = this.getAttribute('data-provider');
                if (provider && authBase) {
                    var cnEl = document.getElementById('company_name');
                    var nameEl = document.getElementById('name');
                    var cnInput = form.querySelector('input[name="company_name"]');
                    var nameInput = form.querySelector('input[name="name"]');
                    if (cnEl && cnInput) cnInput.value = cnEl.value ? cnEl.value.trim() : '';
                    if (nameEl && nameInput) nameInput.value = nameEl.value ? nameEl.value.trim() : '';
                    if (cnInput && nameInput && (cnInput.value === '' || nameInput.value === '')) {
                        alert('Please enter Company name and Your name at the top first.');
                        return;
                    }
                    form.action = authBase + provider + '/login';
                    form.submit();
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initOAuthButtons);
    } else {
        initOAuthButtons();
    }
})();
