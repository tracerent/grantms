/**
 * Dashboard: apply grant, toggle favorite, update status, search, stats
 */
(function() {
    function initDashboard() {
        document.querySelectorAll('.apply-grant').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var grantId = this.dataset.grantId;
                fetch('/apply-grant', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ grant_id: grantId })
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        alert('Grant application started!');
                        location.reload();
                    }
                })
                .catch(function(e) { console.error(e); });
            });
        });

        document.querySelectorAll('.toggle-favorite').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var grantId = this.dataset.grantId;
                var self = this;
                fetch('/toggle-favorite', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ grant_id: grantId })
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        self.textContent = self.textContent === '★' ? '☆' : '★';
                    }
                })
                .catch(function(e) { console.error(e); });
            });
        });

        document.querySelectorAll('.status-update').forEach(function(select) {
            select.addEventListener('change', function() {
                var grantId = this.dataset.grantId;
                var status = this.value;
                fetch('/update-grant-status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ grant_id: grantId, status: status })
                })
                .then(function(r) { return r.json(); })
                .catch(function(e) { console.error(e); });
            });
        });

        var searchEl = document.getElementById('grantSearch');
        if (searchEl) {
            searchEl.addEventListener('keyup', function(e) {
                var query = e.target.value.toLowerCase();
                document.querySelectorAll('.grant-item').forEach(function(item) {
                    var title = (item.dataset.title || '').toLowerCase();
                    var desc = (item.dataset.desc || '').toLowerCase();
                    item.style.display = (title.indexOf(query) !== -1 || desc.indexOf(query) !== -1) ? '' : 'none';
                });
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }
})();
