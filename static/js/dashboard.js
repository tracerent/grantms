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

        // Refresh Home tab content when user switches to Home tab
        var homeTab = document.getElementById('home-tab');
        if (homeTab) {
            homeTab.addEventListener('shown.bs.tab', function() {
                fetch('/api/dashboard-home')
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.error) return;
                        var total = data.total_value != null ? data.total_value : 0;
                        var valueEl = document.getElementById('home-value-amount');
                        if (valueEl) valueEl.textContent = '$' + Math.round(total).toLocaleString();

                        var matchesCount = document.getElementById('home-matches-count');
                        if (matchesCount) matchesCount.textContent = '[' + (data.all_grants ? data.all_grants.length : 0) + ']';
                        var portfolioCount = document.getElementById('home-portfolio-count');
                        if (portfolioCount) portfolioCount.textContent = '[' + (data.user_grants ? data.user_grants.length : 0) + ']';

                        var matchesUl = document.getElementById('home-matches-ul');
                        if (matchesUl) {
                            var grants = data.all_grants || [];
                            if (grants.length === 0) {
                                matchesUl.innerHTML = '<li class="list-group-item text-muted text-center py-4">No grants in the list yet. Go to <strong>List Building</strong> to view and filter grants.</li>';
                            } else {
                                matchesUl.innerHTML = grants.map(function(g) {
                                    var amt = g.funding_amount != null ? Math.round(g.funding_amount).toLocaleString() : '0';
                                    var title = (g.title || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                                    return '<li class="list-group-item d-flex justify-content-between align-items-center"><span class="text-truncate flex-grow-1 me-2" title="' + title + '">' + title + '</span><span class="text-muted">$' + amt + '</span></li>';
                                }).join('');
                            }
                        }

                        var portfolioUl = document.getElementById('home-portfolio-ul');
                        if (portfolioUl) {
                            var list = data.user_grants || [];
                            var statusClass = { 'Approved': 'portfolio-status-approved', 'In Progress': 'portfolio-status-in-progress', 'Rejected': 'portfolio-status-rejected', 'Applied': 'portfolio-status-submitted', 'Awaiting Review': 'portfolio-status-submitted', 'Submitted': 'portfolio-status-submitted' };
                            if (list.length === 0) {
                                portfolioUl.innerHTML = '<li class="list-group-item text-muted text-center py-4">No grant selected. Use <strong>List Building</strong> to star grants and add them to your portfolio.</li>';
                            } else {
                                portfolioUl.innerHTML = list.map(function(g) {
                                    var title = (g.title || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                                    var status = g.status || 'Added';
                                    var cls = statusClass[status] || 'portfolio-status-added';
                                    var label = status === 'Approved' ? 'Approved' : status === 'In Progress' ? 'In Progress' : status === 'Rejected' ? 'Rejected' : (status === 'Applied' || status === 'Awaiting Review' || status === 'Submitted') ? 'Submitted' : 'Added';
                                    return '<li class="list-group-item d-flex justify-content-between align-items-center"><span class="text-truncate flex-grow-1 me-2" title="' + title + '">' + title + '</span><span class="portfolio-status ' + cls + '">' + label + '</span></li>';
                                }).join('');
                            }
                        }
                    })
                    .catch(function(e) { console.error(e); });
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }
})();
