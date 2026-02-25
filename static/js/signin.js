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
                    var fnEl = document.getElementById('first_name');
                    var lnEl = document.getElementById('last_name');
                    var cnInput = form.querySelector('input[name="company_name"]');
                    var nameInput = form.querySelector('input[name="name"]');
                    if (cnEl && cnInput) cnInput.value = cnEl.value ? cnEl.value.trim() : '';
                    var firstName = fnEl && fnEl.value ? fnEl.value.trim() : '';
                    var lastName = lnEl && lnEl.value ? lnEl.value.trim() : '';
                    if (nameInput) nameInput.value = (firstName + ' ' + lastName).trim() || '';
                    if (cnInput && (cnInput.value === '' || !firstName)) {
                        alert('Please enter Company name and First name at the top first.');
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
