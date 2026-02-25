/**
 * List Building: sort, search, filter, pagination, accordion list, add to portfolio (quarter modal).
 */
(function() {
    var GRANTS_PER_PAGE = 10;
    var grants = [];
    var portfolioGrantIds = [];
    var portfolioInfoByGrantId = {}; // grant_id -> { year, quarter }
    var favoriteIds = [];
    var filtered = [];
    var currentPage = 1;
    var sortValue = 'name-asc';
    var searchQuery = '';
    var activeFilters = {}; // e.g. { status: 'Open', funding_for: 'Hiring' }

    function getQuarterOptions() {
        var now = new Date();
        var y = now.getFullYear();
        var m = now.getMonth(); // 0-11 -> month 1-12
        var currentQ = Math.floor(m / 3) + 1; // 1-4
        var monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        var quarters = [];
        for (var j = 0; j < 4; j++) {
            var q = currentQ + j;
            var yr = y;
            if (q > 4) { q -= 4; yr += 1; }
            var startMonth = (q - 1) * 3 + 1;
            var endMonth = startMonth + 2;
            var label = yr + ' Q' + q + ' (' + monthNames[startMonth - 1] + ' - ' + monthNames[endMonth - 1] + ')';
            quarters.push({ value: yr + ' Q' + q, label: label });
        }
        return quarters;
    }

    function applyFiltersAndSort() {
        filtered = grants.slice();

        // Search (title, description, agency)
        if (searchQuery) {
            var q = searchQuery.toLowerCase();
            filtered = filtered.filter(function(g) {
                var title = (g.title || '').toLowerCase();
                var desc = (g.description || '').toLowerCase();
                var agency = (g.agency || '').toLowerCase();
                return title.indexOf(q) !== -1 || desc.indexOf(q) !== -1 || agency.indexOf(q) !== -1;
            });
        }

        // Active filters (Status, Funding For - map to grant fields; status we may not have, use category for funding_for)
        if (activeFilters.status && activeFilters.status !== '') {
            // If grants had a 'status' field we'd filter; for now we don't have Open/Closed in DB, so skip or treat all as Open
            // filtered = filtered.filter(function(g) { return (g.status || '') === activeFilters.status; });
        }
        if (activeFilters.funding_for && activeFilters.funding_for !== '') {
            filtered = filtered.filter(function(g) {
                var cat = (g.category || '').toLowerCase();
                var want = activeFilters.funding_for.toLowerCase();
                return cat.indexOf(want) !== -1 || cat === want;
            });
        }

        // Sort
        if (sortValue === 'name-asc') {
            filtered.sort(function(a, b) { return (a.title || '').localeCompare(b.title || ''); });
        } else if (sortValue === 'name-desc') {
            filtered.sort(function(a, b) { return (b.title || '').localeCompare(a.title || ''); });
        } else if (sortValue === 'date-desc') {
            filtered.sort(function(a, b) {
                var da = parseGrantDate(a.deadline);
                var db = parseGrantDate(b.deadline);
                return db - da;
            });
        } else if (sortValue === 'date-asc') {
            filtered.sort(function(a, b) {
                var da = parseGrantDate(a.deadline);
                var db = parseGrantDate(b.deadline);
                return da - db;
            });
        }

        return filtered.length;
    }

    function parseGrantDate(s) {
        if (!s) return 0;
        var d = new Date(s);
        return isNaN(d.getTime()) ? 0 : d.getTime();
    }

    function totalPages() {
        return Math.max(1, Math.ceil(filtered.length / GRANTS_PER_PAGE));
    }

    function pageSlice() {
        var start = (currentPage - 1) * GRANTS_PER_PAGE;
        return filtered.slice(start, start + GRANTS_PER_PAGE);
    }

    function formatAmount(amount) {
        if (amount == null || amount === '') return 'N/A';
        var n = parseFloat(amount);
        if (isNaN(n)) return 'N/A';
        return 'C$ ' + n.toLocaleString('en-CA', { maximumFractionDigits: 0 });
    }

    function formatDeadline(deadline) {
        return deadline && String(deadline).trim() ? String(deadline).trim() : 'N/A';
    }

    function renderCount() {
        var el = document.getElementById('lb-grant-count');
        if (el) el.textContent = filtered.length + ' grant' + (filtered.length !== 1 ? 's' : '') + ' found';
    }

    function renderPagination() {
        var total = totalPages();
        var prevBtn = document.querySelector('.lb-page-prev');
        var nextBtn = document.querySelector('.lb-page-next');
        var linksEl = document.getElementById('lb-page-links');
        var indEl = document.getElementById('lb-page-indicator');
        if (prevBtn) prevBtn.disabled = currentPage <= 1;
        if (nextBtn) nextBtn.disabled = currentPage >= total;

        if (linksEl) {
            linksEl.innerHTML = '';
            var show = 5;
            var start = Math.max(1, currentPage - 2);
            var end = Math.min(total, start + show - 1);
            if (end - start + 1 < show) start = Math.max(1, end - show + 1);
            if (start > 1) {
                var a1 = document.createElement('button');
                a1.type = 'button';
                a1.className = 'btn btn-sm btn-outline-secondary lb-page-num';
                a1.dataset.page = '1';
                a1.textContent = '1';
                linksEl.appendChild(a1);
                if (start > 2) {
                    var dot = document.createElement('span');
                    dot.className = 'px-1 text-muted';
                    dot.textContent = '…';
                    linksEl.appendChild(dot);
                }
            }
            for (var i = start; i <= end; i++) {
                var a = document.createElement('button');
                a.type = 'button';
                a.className = 'btn btn-sm ' + (i === currentPage ? 'btn-primary' : 'btn-outline-secondary') + ' lb-page-num';
                a.dataset.page = String(i);
                a.textContent = String(i);
                linksEl.appendChild(a);
            }
            if (end < total) {
                if (end < total - 1) {
                    var dot2 = document.createElement('span');
                    dot2.className = 'px-1 text-muted';
                    dot2.textContent = '…';
                    linksEl.appendChild(dot2);
                }
                var aLast = document.createElement('button');
                aLast.type = 'button';
                aLast.className = 'btn btn-sm btn-outline-secondary lb-page-num';
                aLast.dataset.page = String(total);
                aLast.textContent = String(total);
                linksEl.appendChild(aLast);
            }
        }
        if (indEl) indEl.textContent = 'Page ' + currentPage + (total > 1 ? ' of ' + total : '');
    }

    function renderActiveFilterChips() {
        var el = document.getElementById('lb-active-filters');
        if (!el) return;
        el.innerHTML = '';
        var labels = { status: 'Status', funding_for: 'Funding For' };
        Object.keys(activeFilters).forEach(function(key) {
            var val = activeFilters[key];
            if (!val) return;
            var chip = document.createElement('span');
            chip.className = 'badge bg-light text-dark border d-inline-flex align-items-center gap-1';
            chip.innerHTML = (labels[key] || key) + ': ' + val + ' <button type="button" class="btn-close btn-close-sm" style="font-size:0.6rem" data-filter-key="' + key + '" aria-label="Remove"></button>';
            el.appendChild(chip);
        });
    }

    function getPortfolioYearQuarter(grantId) {
        var info = portfolioInfoByGrantId[Number(grantId)];
        if (!info || info.year == null || info.quarter == null) return null;
        return info.year + ' Q' + info.quarter;
    }

    function renderGrantList() {
        var listEl = document.getElementById('lb-grant-list');
        if (!listEl) return;
        var slice = pageSlice();
        listEl.innerHTML = '';

        slice.forEach(function(grant, index) {
            var accId = 'lb-acc-' + grant.id + '-' + index;
            var collapseId = 'lb-collapse-' + grant.id + '-' + index;
            var inPortfolio = isInPortfolio(grant.id);
            var selectedForRow = '';
            if (inPortfolio) {
                var yq = getPortfolioYearQuarter(grant.id);
                if (yq) {
                    selectedForRow = '<dt class="col-sm-4">Selected for</dt><dd class="col-sm-8">' + escapeHtml(yq) + '</dd>';
                }
            }

            var item = document.createElement('div');
            item.className = 'accordion-item lb-accordion-item';
            item.setAttribute('data-grant-id', grant.id);
            item.title = 'Click to view summary';

            item.innerHTML =
                '<div class="accordion-header d-flex align-items-stretch">' +
                '  <div id="' + accId + '" class="accordion-button collapsed lb-accordion-btn py-3 d-flex align-items-center w-100" type="button" data-bs-toggle="collapse" data-bs-target="#' + collapseId + '" aria-expanded="false" aria-controls="' + collapseId + '" style="box-shadow:none; background:transparent; cursor:pointer">' +
                '    <div class="d-flex flex-column text-start flex-grow-1 me-2">' +
                '      <span class="lb-grant-name">' + escapeHtml(grant.title || 'Untitled') + '</span>' +
                '      <span class="small text-muted mt-1">Closes: ' + escapeHtml(formatDeadline(grant.deadline)) + ' &nbsp;<i class="bi bi-currency-dollar"></i> ' + formatAmount(grant.funding_amount) + '</span>' +
                '    </div>' +
                '    <span class="accordion-collapse-chevron flex-shrink-0 me-2"><i class="bi bi-chevron-down"></i></span>' +
                '  </div>' +
                '  <div class="d-flex align-items-center pe-3 flex-shrink-0">' +
                '    <button type="button" class="btn btn-link btn-sm p-0 lb-star-btn text-warning" data-grant-id="' + grant.id + '" aria-label="Add to portfolio">' +
                (inPortfolio ? '<i class="bi bi-star-fill"></i>' : '<i class="bi bi-star"></i>') +
                '    </button>' +
                '  </div>' +
                '</div>' +
                '<div id="' + collapseId + '" class="accordion-collapse collapse" data-bs-parent="#lb-grant-list" aria-labelledby="' + accId + '">' +
                '  <div class="accordion-body lb-accordion-body pt-0">' +
                '    <div class="lb-grant-detail">' +
                '      <h6 class="text-uppercase text-muted small mb-3">Grant Details</h6>' +
                '      <dl class="row small mb-0">' +
                (selectedForRow ? selectedForRow : '') +
                '        <dt class="col-sm-4">Deadline</dt><dd class="col-sm-8">' + escapeHtml(formatDeadline(grant.deadline)) + '</dd>' +
                '        <dt class="col-sm-4">Funding amount</dt><dd class="col-sm-8">' + formatAmount(grant.funding_amount) + '</dd>' +
                '        <dt class="col-sm-4">Description</dt><dd class="col-sm-8">' + escapeHtml((grant.description || '—').slice(0, 500)) + (grant.description && grant.description.length > 500 ? '…' : '') + '</dd>' +
                '        <dt class="col-sm-4">Funding Organization</dt><dd class="col-sm-8">' + escapeHtml(grant.agency || '—') + '</dd>' +
                '        <dt class="col-sm-4">Type of Support</dt><dd class="col-sm-8">' + escapeHtml(grant.category || '—') + '</dd>' +
                '        <dt class="col-sm-4">Sector</dt><dd class="col-sm-8">' + escapeHtml(grant.category || '—') + '</dd>' +
                '        <dt class="col-sm-4">Province</dt><dd class="col-sm-8">' + escapeHtml(grant.location || '—') + '</dd>' +
                '        <dt class="col-sm-4">Stage of Project</dt><dd class="col-sm-8">—</dd>' +
                '        <dt class="col-sm-4">Status</dt><dd class="col-sm-8">—</dd>' +
                '        <dt class="col-sm-4">Annual Revenue Required</dt><dd class="col-sm-8">—</dd>' +
                '        <dt class="col-sm-4">Contact</dt><dd class="col-sm-8">—</dd>' +
                '        <dt class="col-sm-4">Eligibility</dt><dd class="col-sm-8">' + escapeHtml((grant.eligibility || '—').slice(0, 300)) + (grant.eligibility && grant.eligibility.length > 300 ? '…' : '') + '</dd>' +
                '      </dl>' +
                (grant.url ? '<a href="' + escapeAttr(grant.url) + '" target="_blank" rel="noopener" class="btn btn-primary btn-sm mt-3">Official link</a>' : '') +
                '    </div>' +
                '  </div>' +
                '</div>';
            listEl.appendChild(item);
        });

        // Re-attach star and accordion behavior
        listEl.querySelectorAll('.lb-star-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                var gid = parseInt(this.dataset.grantId, 10);
                if (isInPortfolio(gid)) {
                    removeFromPortfolio(gid);
                    return;
                }
                openQuarterModal(gid);
            });
        });

        listEl.querySelectorAll('.lb-accordion-item').forEach(function(row) {
            row.querySelector('.lb-accordion-btn')?.addEventListener('click', function() {
                row.classList.toggle('lb-accordion-open');
            });
        });
    }

    function escapeHtml(s) {
        if (!s) return '';
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }
    function escapeAttr(s) {
        if (!s) return '';
        return String(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    var quarterModalGrantId = null;

    function openQuarterModal(grantId) {
        quarterModalGrantId = grantId;
        var optsEl = document.getElementById('quarter-options');
        if (!optsEl) return;
        optsEl.innerHTML = '';
        getQuarterOptions().forEach(function(q) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-primary';
            btn.textContent = q.label;
            btn.dataset.quarter = q.value;
            optsEl.appendChild(btn);
        });
        var modal = new (window.bootstrap && window.bootstrap.Modal)(document.getElementById('quarterModal'));
        modal.show();
    }

    function removeFromPortfolio(grantId) {
        fetch('/remove-grant-from-portfolio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grant_id: grantId })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                var id = Number(grantId);
                portfolioGrantIds = portfolioGrantIds.filter(function(pid) { return pid !== id; });
                delete portfolioInfoByGrantId[id];
                favoriteIds = favoriteIds.filter(function(fid) { return Number(fid) !== id; });
                renderGrantList();
            } else if (data.error) {
                alert(data.error);
            }
        })
        .catch(function(e) { console.error(e); });
    }

    function parseQuarterString(quarterStr) {
        if (!quarterStr || typeof quarterStr !== 'string') return null;
        var m = quarterStr.trim().match(/^(\d{4})\s*[Qq]\s*([1-4])$/);
        return m ? { year: parseInt(m[1], 10), quarter: parseInt(m[2], 10) } : null;
    }

    function addToPortfolio(grantId, quarterStr) {
        fetch('/add-grant-to-portfolio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grant_id: grantId, quarter: quarterStr })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.redirect && data.open_subscriptions) {
                window.location = (data.redirect || '').replace(/\?.*$/, '') + '#account-subscriptions';
                return;
            }
            if (data.success) {
                var modalEl = document.getElementById('quarterModal');
                if (modalEl) (window.bootstrap && window.bootstrap.Modal.getInstance(modalEl))?.hide();
                quarterModalGrantId = null;
                var id = Number(grantId);
                if (!isInPortfolio(grantId)) portfolioGrantIds.push(id);
                var yq = parseQuarterString(quarterStr);
                if (yq) portfolioInfoByGrantId[id] = yq;
                if (favoriteIds.indexOf(id) === -1) favoriteIds.push(id);
                renderGrantList();
            } else if (data.error) {
                alert(data.error);
            }
        })
        .catch(function(e) { console.error(e); });
    }

    function isInPortfolio(grantId) {
        var id = Number(grantId);
        return portfolioGrantIds.some(function(pid) { return Number(pid) === id; });
    }

    function run() {
        grants = window.LB_GRANTS || [];
        portfolioGrantIds = (window.LB_PORTFOLIO_GRANT_IDS || []).map(function(id) { return Number(id); });
        portfolioInfoByGrantId = {};
        (window.LB_PORTFOLIO_INFO || []).forEach(function(p) {
            if (p && p.id != null) portfolioInfoByGrantId[Number(p.id)] = { year: p.year, quarter: p.quarter };
        });
        favoriteIds = (window.LB_FAVORITE_IDS || []).map(function(id) { return Number(id); });

        sortValue = document.getElementById('lb-sort')?.value || 'name-asc';
        searchQuery = (document.getElementById('lb-search')?.value || '').trim().toLowerCase();
        var count = applyFiltersAndSort();
        var total = totalPages();
        if (currentPage > total) currentPage = Math.max(1, total);

        renderCount();
        renderPagination();
        renderActiveFilterChips();
        renderGrantList();
    }

    function applySavedFilters() {
        var saved = window.LB_SAVED_FILTERS || {};
        if (saved.status !== undefined && saved.status !== null) {
            activeFilters.status = String(saved.status);
            var selStatus = document.getElementById('filter-status');
            if (selStatus) selStatus.value = activeFilters.status;
        }
        if (saved.funding_for !== undefined && saved.funding_for !== null) {
            activeFilters.funding_for = String(saved.funding_for);
            var selFF = document.getElementById('filter-funding-for');
            if (selFF) selFF.value = activeFilters.funding_for;
        }
    }

    function saveFiltersToServer() {
        fetch('/api/save-list-filters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: activeFilters.status || '', funding_for: activeFilters.funding_for || '' })
        }).catch(function(e) { console.error(e); });
    }

    function init() {
        applySavedFilters();

        document.getElementById('lb-sort')?.addEventListener('change', function() {
            sortValue = this.value;
            currentPage = 1;
            run();
        });

        var searchEl = document.getElementById('lb-search');
        if (searchEl) {
            searchEl.addEventListener('input', function() {
                searchQuery = this.value.trim().toLowerCase();
                currentPage = 1;
                run();
            });
        }

        document.getElementById('lb-filter-btn')?.addEventListener('click', function() {
            var panel = document.getElementById('lb-filter-panel');
            if (panel) panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        });

        document.getElementById('lb-filter-apply')?.addEventListener('click', function() {
            activeFilters.status = document.getElementById('filter-status')?.value || '';
            activeFilters.funding_for = document.getElementById('filter-funding-for')?.value || '';
            document.getElementById('lb-filter-panel').style.display = 'none';
            currentPage = 1;
            saveFiltersToServer();
            run();
        });

        document.getElementById('lb-filter-clear')?.addEventListener('click', function() {
            document.getElementById('filter-status').value = '';
            document.getElementById('filter-funding-for').value = '';
            activeFilters = {};
            currentPage = 1;
            saveFiltersToServer();
            run();
            renderActiveFilterChips();
        });

        document.getElementById('lb-active-filters')?.addEventListener('click', function(e) {
            var btn = e.target.closest('button[data-filter-key]');
            if (!btn) return;
            var key = btn.getAttribute('data-filter-key');
            if (key) {
                activeFilters[key] = '';
                if (key === 'status') document.getElementById('filter-status').value = '';
                if (key === 'funding_for') document.getElementById('filter-funding-for').value = '';
                currentPage = 1;
                saveFiltersToServer();
                run();
            }
        });

        document.querySelector('.lb-page-prev')?.addEventListener('click', function() {
            if (currentPage > 1) { currentPage--; run(); }
        });
        document.querySelector('.lb-page-next')?.addEventListener('click', function() {
            if (currentPage < totalPages()) { currentPage++; run(); }
        });
        document.getElementById('lb-pagination')?.addEventListener('click', function(e) {
            var btn = e.target.closest('.lb-page-num');
            if (btn && btn.dataset.page) {
                currentPage = parseInt(btn.dataset.page, 10);
                run();
            }
        });

        document.getElementById('quarter-options')?.addEventListener('click', function(e) {
            var btn = e.target.closest('button[data-quarter]');
            if (btn && quarterModalGrantId) {
                addToPortfolio(quarterModalGrantId, btn.dataset.quarter);
            }
        });

        run();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
