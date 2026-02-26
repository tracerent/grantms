/**
 * Dashboard: apply grant, toggle favorite, update status, search, stats.
 * Tabs/sections are synced to URL hash so refresh and back button return to the same section.
 */
(function() {
    var HASH_HOME = 'home';
    var HASH_ACCOUNT_SUBSCRIPTIONS = 'account-subscriptions';

    function applyDashboardStateFromHash(hash) {
        hash = (hash || '').replace(/^#/, '').trim();
        var scrollToId = null;
        if (hash === 'subscription-upgrade-plan') {
            scrollToId = hash;
            hash = HASH_ACCOUNT_SUBSCRIPTIONS;
        }
        if (hash === '' || hash === HASH_HOME) {
            var homeTab = document.getElementById('home-tab');
            if (homeTab && !homeTab.classList.contains('active')) homeTab.click();
            return;
        }
        if (hash === 'list-building') {
            var lbTab = document.getElementById('list-building-tab');
            if (lbTab) lbTab.click();
            return;
        }
        if (hash === 'saved-grants') {
            var sgTab = document.getElementById('saved-grants-tab');
            if (sgTab) sgTab.click();
            return;
        }
        if (hash === 'store-contacts') {
            var scTab = document.getElementById('store-contacts-tab');
            if (scTab) scTab.click();
            return;
        }
        if (hash === 'add-grants') {
            var agTab = document.getElementById('add-grants-tab');
            if (agTab) agTab.click();
            return;
        }
        if (hash === 'application') {
            var appTab = document.getElementById('application-tab');
            if (appTab) appTab.click();
            return;
        }
        if (hash === 'account-profile' || hash === 'account-team' || hash === HASH_ACCOUNT_SUBSCRIPTIONS) {
            var trigger = document.getElementById('account-tab-trigger');
            if (trigger) trigger.click();
            var view = hash === 'account-profile' ? 'profile' : hash === 'account-team' ? 'add-user' : 'subscriptions';
            setTimeout(function() {
                document.querySelectorAll('.account-subview').forEach(function(el) { el.classList.add('d-none'); });
                var show = document.getElementById('account-view-' + view);
                if (show) show.classList.remove('d-none');
                if (scrollToId) {
                    var target = document.getElementById(scrollToId);
                    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 50);
        }
    }

    function dashboardRedirectToSubscriptions() {
        var path = window.location.pathname || '/dashboard';
        window.location = path + '#' + HASH_ACCOUNT_SUBSCRIPTIONS;
    }

    function getPaymentMethodBrandIcon(brand) {
        var b = (brand || '').toLowerCase();
        if (b === 'visa') return 'fab fa-cc-visa';
        if (b === 'mastercard') return 'fab fa-cc-mastercard';
        if (b === 'amex' || b === 'american express') return 'fab fa-cc-amex';
        if (b === 'discover') return 'fab fa-cc-discover';
        if (b === 'diners club') return 'fab fa-cc-diners-club';
        if (b === 'jcb') return 'fab fa-cc-jcb';
        return 'bi bi-credit-card';
    }

    function appendPaymentMethodCard(pm) {
        var container = document.getElementById('payment-methods-section-inner');
        if (!container) return;
        var grid = container.querySelector('.payment-methods-grid');
        var emptyState = container.querySelector('.subscription-empty-state');
        var pmId = pm.payment_method_id;
        var last4 = (pm.last4 || '****').toString().slice(-4);
        var expStr = (pm.expiry_month && pm.expiry_year)
            ? (String(pm.expiry_month).padStart(2, '0') + '/' + String(pm.expiry_year).slice(-2))
            : '—';
        var brand = pm.brand || 'Card';
        var brandEsc = brand.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        var iconClass = getPaymentMethodBrandIcon(brand);
        var colHtml = '<div class="col-6 col-md-4 col-lg-3" data-payment-method-id="' + pmId + '">' +
            '<div class="payment-method-card">' +
            '<label class="payment-method-default-label" title="Set as default payment method">' +
            '<input type="checkbox" class="payment-method-set-default" data-method-id="' + pmId + '" aria-label="Default payment method">' +
            '<span class="payment-method-default-text">Set autopay method</span></label>' +
            '<div class="payment-method-card-row">' +
            '<span class="payment-method-card-last4">•••• ' + last4 + '</span>' +
            '<span class="payment-method-card-expiry">' + expStr + '</span>' +
            '</div><div class="payment-method-card-row">' +
            '<span class="payment-method-card-brand">' +
            '<i class="' + iconClass + ' payment-card-brand-icon" aria-hidden="true"></i>' +
            '<span class="payment-method-card-brand-name">' + brandEsc + '</span></span>' +
            '<button type="button" class="btn btn-gradient-yellow btn-sm subscription-remove-method" data-method-id="' + pmId + '">Remove</button>' +
            '</div></div></div>';
        if (emptyState) {
            var row = document.createElement('div');
            row.className = 'row g-3 payment-methods-grid';
            row.innerHTML = colHtml;
            container.replaceChild(row, emptyState);
        } else if (grid) {
            var col = document.createElement('div');
            col.innerHTML = colHtml;
            grid.appendChild(col.firstElementChild);
        }
    }

    function initDashboard() {
        // Add Grants: request a new grant (submit to requested_grants)
        var requestGrantForm = document.getElementById('request-grant-form');
        if (requestGrantForm) {
            requestGrantForm.addEventListener('submit', function(e) {
                e.preventDefault();
                var msgEl = document.getElementById('request-grant-message');
                var submitBtn = document.getElementById('request-grant-submit');
                var fundingOrg = (document.getElementById('request-grant-funding-org') && document.getElementById('request-grant-funding-org').value) ? document.getElementById('request-grant-funding-org').value.trim() : '';
                var programName = (document.getElementById('request-grant-program-name') && document.getElementById('request-grant-program-name').value) ? document.getElementById('request-grant-program-name').value.trim() : '';
                var description = (document.getElementById('request-grant-description') && document.getElementById('request-grant-description').value) ? document.getElementById('request-grant-description').value.trim() : '';
                var link = (document.getElementById('request-grant-link') && document.getElementById('request-grant-link').value) ? document.getElementById('request-grant-link').value.trim() : '';
                if (!msgEl) return;
                msgEl.classList.add('d-none');
                msgEl.classList.remove('alert-success', 'alert-danger');
                if (!fundingOrg || !programName || !link) {
                    msgEl.textContent = 'Please fill in Funding Organization, Program Name, and Link to Grant.';
                    msgEl.classList.add('alert', 'alert-danger');
                    msgEl.classList.remove('d-none');
                    return;
                }
                if (submitBtn) submitBtn.disabled = true;
                fetch('/api/dashboard/request-grant', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        funding_organization: fundingOrg,
                        program_name: programName,
                        funding_description: description || undefined,
                        link_to_grant: link
                    })
                })
                    .then(function(r) { return r.json().then(function(data) { return { status: r.status, data: data }; }); })
                    .then(function(res) {
                        if (res.data.error) {
                            msgEl.textContent = res.data.error;
                            msgEl.classList.add('alert', 'alert-danger');
                        } else {
                            msgEl.textContent = 'Request submitted. Our team will review and add the grant when approved.';
                            msgEl.classList.add('alert', 'alert-success');
                            requestGrantForm.reset();
                        }
                        msgEl.classList.remove('d-none');
                    })
                    .catch(function(err) {
                        console.error(err);
                        msgEl.textContent = 'Could not submit request. Please try again.';
                        msgEl.classList.add('alert', 'alert-danger');
                        msgEl.classList.remove('d-none');
                    })
                    .finally(function() {
                        if (submitBtn) submitBtn.disabled = false;
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
                        if (portfolioCount) portfolioCount.textContent = '[' + (data.company_grants ? data.company_grants.length : 0) + ']';

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
                            var list = data.company_grants || [];
                            var statusClass = { 'Approved': 'portfolio-status-approved', 'In Progress': 'portfolio-status-in-progress', 'Rejected': 'portfolio-status-rejected', 'Applied': 'portfolio-status-submitted', 'Awaiting Review': 'portfolio-status-submitted', 'Submitted': 'portfolio-status-submitted' };
                            if (list.length === 0) {
                                portfolioUl.innerHTML = '<li class="list-group-item text-muted text-center py-4">No grants saved yet. Use <strong>List Building</strong> to save grants.</li>';
                            } else {
                                portfolioUl.innerHTML = list.map(function(g) {
                                    var title = (g.title || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                                    var status = g.status || 'Saved';
                                    var cls = statusClass[status] || 'portfolio-status-added';
                                    var label = (status === 'Approved') ? 'Approved' : (status === 'In Progress') ? 'In Progress' : (status === 'Rejected') ? 'Rejected' : (status === 'Applied' || status === 'Awaiting Review' || status === 'Submitted') ? 'Submitted' : 'Saved';
                                    return '<li class="list-group-item d-flex justify-content-between align-items-center"><span class="text-truncate flex-grow-1 me-2" title="' + title + '">' + title + '</span><span class="portfolio-status ' + cls + '">' + label + '</span></li>';
                                }).join('');
                            }
                        }
                    })
                        .catch(function(e) { console.error(e); });
            });
        }

        // Account dropdown: show account tab and subview; update URL hash
        document.querySelectorAll('.account-dropdown-item').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                var view = this.getAttribute('data-account-view') || 'profile';
                var hash = this.getAttribute('data-dashboard-hash') || 'account-profile';
                if (typeof history.replaceState === 'function') {
                    history.replaceState(null, '', window.location.pathname + '#' + hash);
                } else {
                    window.location.hash = hash;
                }
                var trigger = document.getElementById('account-tab-trigger');
                if (trigger) trigger.click();
                setTimeout(function() {
                    document.querySelectorAll('.account-subview').forEach(function(el) { el.classList.add('d-none'); });
                    var show = document.getElementById('account-view-' + view);
                    if (show) show.classList.remove('d-none');
                }, 50);
            });
        });

        // Account edit: toggle view / edit mode
        document.querySelectorAll('.account-edit-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var section = this.getAttribute('data-section');
                var viewEl = document.getElementById(section + '-view');
                var editEl = document.getElementById(section + '-edit');
                if (viewEl && editEl) {
                    viewEl.classList.add('d-none');
                    editEl.classList.remove('d-none');
                }
            });
        });
        document.querySelectorAll('.account-cancel-edit').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var section = this.getAttribute('data-section');
                var viewEl = document.getElementById(section + '-view');
                var editEl = document.getElementById(section + '-edit');
                if (viewEl && editEl) {
                    viewEl.classList.remove('d-none');
                    editEl.classList.add('d-none');
                }
            });
        });

        // Personal info form submit
        var formPersonal = document.getElementById('form-personal');
        if (formPersonal) {
            formPersonal.addEventListener('submit', function(e) {
                e.preventDefault();
                var fd = new FormData(formPersonal);
                var payload = {
                    first_name: (fd.get('first_name') || '').trim(),
                    last_name: (fd.get('last_name') || '').trim(),
                    email: (fd.get('email') || '').trim(),
                    job_title: (fd.get('job_title') || '').trim()
                };
                fetch('/api/account/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }
                    document.querySelectorAll('#personal-view [data-field]').forEach(function(el) {
                        var field = el.getAttribute('data-field');
                        var val = payload[field] || '—';
                        if (el.tagName === 'P' || el.classList.contains('account-val')) el.textContent = val;
                    });
                    document.getElementById('personal-edit').classList.add('d-none');
                    document.getElementById('personal-view').classList.remove('d-none');
                    // Refresh header name if present
                    var welcome = document.querySelector('.dashboard-header h1');
                    if (welcome) welcome.textContent = 'Welcome, ' + (payload.first_name || payload.last_name || payload.email || 'User') + '!';
                })
                .catch(function(err) { console.error(err); alert('Failed to save'); });
            });
        }

        // Company info form submit
        var formCompany = document.getElementById('form-company');
        if (formCompany) {
            formCompany.addEventListener('submit', function(e) {
                e.preventDefault();
                var fd = new FormData(formCompany);
                var payload = {};
                ['legal_entity_name', 'operating_name', 'company_name', 'provincial_corporate_access_number',
                 'workers_compensation_number', 'business_number', 'business_phone_number', 'address',
                 'date_of_incorporation', 'postal_code', 'years_in_operation', 'founder_name', 'website', 'founder_title'].forEach(function(k) {
                    var v = fd.get(k);
                    payload[k] = v != null ? String(v).trim() : '';
                });
                var y = fd.get('years_in_operation');
                if (y !== null && y !== '') payload.years_in_operation = parseInt(y, 10);
                fetch('/api/account/company', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }
                    // Update view mode values (same order as in template)
                    var viewEl = document.getElementById('company-view');
                    if (viewEl) {
                        var vals = viewEl.querySelectorAll('.account-val');
                        var keys = ['legal_entity_name', 'operating_name', 'company_name', 'provincial_corporate_access_number',
                            'workers_compensation_number', 'business_number', 'business_phone_number',
                            'date_of_incorporation', 'years_in_operation', 'founder_name', 'founder_title',
                            'address', 'postal_code', 'website'];
                        keys.forEach(function(k, i) {
                            if (vals[i]) vals[i].textContent = (payload[k] != null && payload[k] !== '') ? payload[k] : '—';
                        });
                    }
                    document.getElementById('company-edit').classList.add('d-none');
                    document.getElementById('company-view').classList.remove('d-none');
                })
                .catch(function(err) { console.error(err); alert('Failed to save'); });
            });
        }

        // Add team member form (delegated so it works after fragment refresh)
        var accountViewAddUser = document.getElementById('account-view-add-user');
        if (accountViewAddUser) {
            accountViewAddUser.addEventListener('submit', function(e) {
                var form = e.target;
                if (form.id !== 'form-add-member') return;
                e.preventDefault();
                var fd = new FormData(form);
                var payload = {
                    first_name: (fd.get('first_name') || '').trim(),
                    last_name: (fd.get('last_name') || '').trim(),
                    email: (fd.get('email') || '').trim(),
                    job_title: (fd.get('job_title') || '').trim(),
                    password: (fd.get('password') || '').trim()
                };
                if (!payload.email) {
                    alert('Email is required');
                    return;
                }
                if (!payload.password) {
                    alert('Password is required');
                    return;
                }
                if (payload.password.length < 6) {
                    alert('Password must be at least 6 characters');
                    return;
                }
                var btn = form.querySelector('#btn-add-member');
                if (btn) btn.disabled = true;
                fetch('/api/account/team/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        alert(data.error);
                        if (btn) btn.disabled = false;
                        return;
                    }
                    form.reset();
                    location.reload();
                })
                .catch(function(err) {
                    console.error(err);
                    alert('Failed to add member');
                    if (btn) btn.disabled = false;
                });
            });
        }

        // Activate / Deactivate team member (delegated so it works after fragment refresh)
        if (accountViewAddUser) {
            accountViewAddUser.addEventListener('click', function(e) {
                var btn = e.target && e.target.closest('.team-toggle-active');
                if (!btn) return;
                if (btn.disabled) return;
                var userId = btn.getAttribute('data-user-id');
                if (!userId) return;
                btn.disabled = true;
                fetch('/api/account/team/toggle-active', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: parseInt(userId, 10) })
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        alert(data.error);
                        btn.disabled = false;
                        return;
                    }
                    location.reload();
                })
                .catch(function(err) {
                    console.error(err);
                    alert('Failed to update status');
                    btn.disabled = false;
                });
            });
        }

        // Apply tab/section from URL hash on load; support ?open=account-subscriptions for legacy links
        var params = new URLSearchParams(window.location.search);
        var initialHash = (window.location.hash || '').replace(/^#/, '');
        if (params.get('open') === 'account-subscriptions' && !initialHash) {
            initialHash = HASH_ACCOUNT_SUBSCRIPTIONS;
            if (typeof history.replaceState === 'function') {
                history.replaceState(null, '', window.location.pathname + '#' + initialHash);
            } else {
                window.location.hash = initialHash;
            }
        }

        // When user uses back/forward or hash changes, sync the visible tab
        window.addEventListener('hashchange', function() {
            applyDashboardStateFromHash(window.location.hash);
        });

        // Upgrade plan links in dismissable alerts: handle in JS so Account > Subscriptions opens (hash alone may not scroll to a valid id)
        document.addEventListener('click', function(e) {
            var a = e.target && e.target.closest('a[href*="#account-subscriptions"]');
            if (!a) return;
            e.preventDefault();
            applyDashboardStateFromHash(HASH_ACCOUNT_SUBSCRIPTIONS);
            var path = window.location.pathname || '/dashboard';
            if (typeof history.replaceState === 'function') {
                history.replaceState(null, '', path + '#account-subscriptions');
            } else {
                window.location.hash = 'account-subscriptions';
            }
        });

        // When a main tab is shown (not account dropdown), update URL hash so refresh/back works
        document.querySelectorAll('[data-dashboard-hash]').forEach(function(el) {
            var hash = el.getAttribute('data-dashboard-hash');
            if (!hash) return;
            if (el.classList.contains('account-dropdown-item')) return;
            var tabId = el.id;
            if (tabId && el.getAttribute('data-bs-toggle') === 'tab') {
                el.addEventListener('shown.bs.tab', function(e) {
                    if (typeof history.replaceState === 'function') {
                        history.replaceState(null, '', window.location.pathname + (hash ? '#' + hash : ''));
                    } else {
                        window.location.hash = hash || HASH_HOME;
                    }
                    if (hash === 'saved-grants' && typeof refreshSavedGrants === 'function') {
                        refreshSavedGrants();
                    }
                    if (hash === 'store-contacts' && typeof refreshContactsTab === 'function') {
                        refreshContactsTab();
                    }
                });
            }
        });

        // Apply tab/section from URL hash on load *after* tab listeners are attached so refresh with #store-contacts loads data
        applyDashboardStateFromHash(initialHash || HASH_HOME);
        var appliedHash = (initialHash || HASH_HOME).trim();
        if (appliedHash === 'store-contacts') {
            setTimeout(function() {
                if (typeof refreshContactsTab === 'function') refreshContactsTab();
            }, 0);
        }
        if (appliedHash === 'saved-grants') {
            setTimeout(function() {
                if (typeof refreshSavedGrants === 'function') refreshSavedGrants();
            }, 0);
        }

        // Saved Grants: Edit -> set status In Progress, redirect to grant detail page
        document.addEventListener('click', function(e) {
            var editBtn = e.target && e.target.closest('.timeline-grant-edit');
            if (!editBtn) return;
            e.preventDefault();
            var grantId = editBtn.getAttribute('data-grant-id');
            if (!grantId) return;
            fetch('/update-grant-status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ grant_id: parseInt(grantId, 10), status: 'In Progress' })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) { alert(data.error); return; }
                    window.location.href = '/dashboard/grant/' + grantId;
                })
                .catch(function(err) { console.error(err); alert('Failed to update status'); });
        });

        // Saved Grants: Apply -> show confirm modal (with progress %), then set Submitted and redirect
        window._grantApplyPendingId = null;
        document.addEventListener('click', function(e) {
            var applyBtn = e.target && e.target.closest('.timeline-grant-apply');
            if (!applyBtn) return;
            e.preventDefault();
            var grantId = applyBtn.getAttribute('data-grant-id');
            if (!grantId) return;
            window._grantApplyPendingId = grantId;
            var msgEl = document.getElementById('grant-apply-confirm-message');
            if (msgEl) msgEl.textContent = 'Do you want to mark this grant as Submitted?';
            fetch('/api/dashboard/grant/' + grantId + '/progress', { credentials: 'same-origin' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var pct = (data && data.progress_percent != null) ? data.progress_percent : 0;
                    if (msgEl) {
                        if (pct < 100) {
                            msgEl.textContent = 'Progress is at ' + pct + '%. Do you confirm submission?';
                        } else {
                            msgEl.textContent = 'Do you want to mark this grant as Submitted?';
                        }
                    }
                })
                .catch(function() {})
                .then(function() {
                    var modal = document.getElementById('grantApplyConfirmModal');
                    if (modal && typeof bootstrap !== 'undefined') {
                        var m = new bootstrap.Modal(modal);
                        m.show();
                    }
                });
        });
        var btnConfirmGrantApply = document.getElementById('btn-confirm-grant-apply');
        if (btnConfirmGrantApply) {
            btnConfirmGrantApply.addEventListener('click', function() {
                var grantId = window._grantApplyPendingId;
                if (!grantId) return;
                fetch('/update-grant-status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ grant_id: parseInt(grantId, 10), status: 'Submitted' })
                })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.error) { alert(data.error); return; }
                        window._grantApplyPendingId = null;
                        var modalEl = document.getElementById('grantApplyConfirmModal');
                        if (modalEl && typeof bootstrap !== 'undefined') {
                            var m = bootstrap.Modal.getInstance(modalEl);
                            if (m) m.hide();
                        }
                        window.location.href = '/dashboard/grant/' + grantId;
                    })
                    .catch(function(err) { console.error(err); alert('Failed to update status'); });
            });
        }

        function escapeHtml(s) {
            if (s == null || s === undefined) return '';
            var t = String(s);
            return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function buildTimelineGrantItem(g) {
            var title = escapeHtml(g.title || '—');
            var amount = (g.funding_amount != null && !isNaN(g.funding_amount)) ? Number(g.funding_amount).toLocaleString('en-US', { maximumFractionDigits: 0 }) : '0';
            var deadline = escapeHtml(g.deadline || '—');
            var planned = (g.planned && String(g.planned).trim()) ? escapeHtml(g.planned) : '';
            var id = parseInt(g.id, 10) || 0;
            var metaAmount = '<span class="timeline-grant-meta-item timeline-grant-meta-amount"><i class="bi bi-currency-dollar" aria-hidden="true"></i><span>$' + amount + '</span></span>';
            var metaCloses = '<span class="timeline-grant-meta-item"><i class="bi bi-calendar3" aria-hidden="true"></i><span>Closes ' + deadline + '</span></span>';
            var metaPlanned = planned ? '<span class="timeline-grant-meta-planned"><i class="bi bi-calendar-check" aria-hidden="true"></i><span>Planned ' + planned + '</span></span>' : '';
            var metaHtml = '<div class="timeline-grant-meta">' + metaAmount + metaCloses + metaPlanned + '</div>';
            return '<li class="account-list-item timeline-grant-item d-flex justify-content-between align-items-start">' +
                '<div class="flex-grow-1 min-w-0">' +
                '<div class="fw-bold text-truncate" title="' + title + '">' + title + '</div>' +
                metaHtml +
                '</div>' +
                '<div class="d-flex gap-1 ms-2 flex-shrink-0 align-items-center">' +
                '<button type="button" class="btn btn-link btn-sm p-0 border-0 account-edit-btn text-secondary timeline-grant-edit" data-grant-id="' + id + '" title="Edit" aria-label="Edit"><i class="bi bi-pencil"></i></button>' +
                '<button type="button" class="btn btn-gradient-yellow btn-sm timeline-grant-apply" data-grant-id="' + id + '" title="Apply">Apply</button>' +
                '</div></li>';
        }

        function refreshSavedGrants() {
            var nextList = document.getElementById('timeline-next-6-list');
            var afterList = document.getElementById('timeline-after-6-list');
            if (!nextList || !afterList) return;
            fetch('/api/dashboard/saved-grants')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) return;
                    var next = data.timeline_next_6 || [];
                    var after = data.timeline_after_6 || [];
                    nextList.innerHTML = next.length
                        ? next.map(buildTimelineGrantItem).join('')
                        : '<li class="account-list-item text-muted small">No grants in the next 6 months.</li>';
                    afterList.innerHTML = after.length
                        ? after.map(buildTimelineGrantItem).join('')
                        : '<li class="account-list-item text-muted small">No grants after this period.</li>';
                })
                .catch(function(e) { console.error(e); });
        }

        // --- Contacts tab ---
        var contactsSelectedCategory = '';
        var contactsSearchTimeout = null;

        function refreshContactsTab() {
            loadContactsCategoryCounts();
            loadContactsList();
        }

        function loadContactsCategoryCounts() {
            fetch('/api/dashboard/contacts/category-counts', { credentials: 'same-origin' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) { alert(data.error); return; }
                    var total = data.total != null ? data.total : 0;
                    var counts = data.counts || {};
                    var allEl = document.getElementById('contacts-count-all');
                    if (allEl) allEl.textContent = total;
                    document.querySelectorAll('[data-count-category]').forEach(function(el) {
                        var cat = el.getAttribute('data-count-category');
                        el.textContent = counts[cat] != null ? counts[cat] : 0;
                    });
                })
                .catch(function(e) { console.error(e); alert('Could not load category counts.'); });
        }

        function loadContactsList() {
            var category = contactsSelectedCategory || '';
            var searchEl = document.getElementById('contacts-search');
            var search = (searchEl && searchEl.value) ? searchEl.value.trim() : '';
            var url = '/api/dashboard/contacts?category=' + encodeURIComponent(category) + '&search=' + encodeURIComponent(search);
            fetch(url, { credentials: 'same-origin' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) { alert(data.error); return; }
                    var contacts = data.contacts || [];
                    var tbody = document.getElementById('contacts-tbody');
                    var emptyEl = document.getElementById('contacts-empty');
                    var tableWrap = document.getElementById('contacts-table-wrap');
                    var titleEl = document.getElementById('contacts-panel-title');
                    if (titleEl) titleEl.textContent = category ? category : 'All Contacts';
                    if (!tbody) return;
                    function esc(s) { return (s == null || s === undefined) ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
                    if (contacts.length === 0) {
                        tbody.innerHTML = '';
                        if (emptyEl) { emptyEl.classList.remove('d-none'); }
                        if (tableWrap) { tableWrap.classList.add('d-none'); }
                    } else {
                        if (emptyEl) { emptyEl.classList.add('d-none'); }
                        if (tableWrap) { tableWrap.classList.remove('d-none'); }
                        tbody.innerHTML = contacts.map(function(c) {
                            var id = parseInt(c.id, 10) || 0;
                            var org = esc(c.organization);
                            var name = esc(c.contact_name);
                            var email = esc(c.email);
                            var phone = esc(c.phone);
                            var role = esc(c.role);
                            return '<tr data-contact-id="' + id + '">' +
                                '<td>' + org + '</td><td>' + name + '</td><td>' + email + '</td><td>' + phone + '</td><td>' + role + '</td>' +
                                '<td class="text-end">' +
                                '<button type="button" class="btn btn-link btn-sm p-0 me-2 contact-edit" data-contact-id="' + id + '" title="Edit" aria-label="Edit"><i class="bi bi-pencil"></i></button>' +
                                '<button type="button" class="btn btn-link btn-sm p-0 text-danger contact-delete" data-contact-id="' + id + '" title="Delete" aria-label="Delete"><i class="bi bi-trash"></i></button>' +
                                '</td></tr>';
                        }).join('');
                    }
                })
                .catch(function(e) { console.error(e); alert('Could not load contacts.'); });
        }

        function setContactsCategoryActive(category) {
            document.querySelectorAll('#contacts-category-list .contacts-category-item').forEach(function(el) {
                var cat = el.getAttribute('data-category') || '';
                if (cat === category) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });
        }

        document.querySelectorAll('#contacts-category-list .contacts-category-item').forEach(function(el) {
            el.style.cursor = 'pointer';
            el.addEventListener('click', function() {
                var cat = el.getAttribute('data-category') || '';
                if (contactsSelectedCategory === cat) {
                    contactsSelectedCategory = '';
                } else {
                    contactsSelectedCategory = cat;
                }
                setContactsCategoryActive(contactsSelectedCategory);
                loadContactsList();
            });
        });

        var contactsSearchEl = document.getElementById('contacts-search');
        if (contactsSearchEl) {
            contactsSearchEl.addEventListener('input', function() {
                if (contactsSearchTimeout) clearTimeout(contactsSearchTimeout);
                contactsSearchTimeout = setTimeout(function() {
                    loadContactsList();
                }, 250);
            });
        }

        var contactsAddBtn = document.getElementById('contacts-add-btn');
        if (contactsAddBtn) {
            contactsAddBtn.addEventListener('click', function() {
                document.getElementById('contactModalLabel').textContent = 'Add Contact';
                document.getElementById('contact-form-id').value = '';
                document.getElementById('contact-category').value = '';
                document.getElementById('contact-organization').value = '';
                document.getElementById('contact-name').value = '';
                document.getElementById('contact-email').value = '';
                document.getElementById('contact-phone').value = '';
                document.getElementById('contact-role').value = '';
                var modal = document.getElementById('contactModal');
                if (modal && window.bootstrap) {
                    var m = new window.bootstrap.Modal(modal);
                    m.show();
                }
            });
        }

        document.getElementById('contact-form-save').addEventListener('click', function() {
            var idEl = document.getElementById('contact-form-id');
            var id = (idEl && idEl.value) ? idEl.value.trim() : '';
            var category = document.getElementById('contact-category').value;
            if (!category) { alert('Please select a category.'); return; }
            var payload = {
                category: category,
                organization: document.getElementById('contact-organization').value,
                contact_name: document.getElementById('contact-name').value,
                email: document.getElementById('contact-email').value,
                phone: document.getElementById('contact-phone').value,
                role: document.getElementById('contact-role').value
            };
            var url = '/api/dashboard/contacts';
            var method = 'POST';
            if (id) {
                url += '/' + id;
                method = 'PUT';
            }
            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                credentials: 'same-origin'
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { alert(data.error); return; }
                var modal = document.getElementById('contactModal');
                if (modal && window.bootstrap) {
                    var m = window.bootstrap.Modal.getInstance(modal);
                    if (m) m.hide();
                }
                refreshContactsTab();
            })
            .catch(function(e) { console.error(e); alert('Could not save contact.'); });
        });

        document.addEventListener('click', function(e) {
            var editBtn = e.target && e.target.closest('.contact-edit');
            if (editBtn) {
                e.preventDefault();
                var id = editBtn.getAttribute('data-contact-id');
                if (!id) return;
                var url = '/api/dashboard/contacts?category=' + encodeURIComponent(contactsSelectedCategory) + '&search=';
                fetch(url)
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        var contacts = data.contacts || [];
                        var c = contacts.find(function(x) { return String(x.id) === String(id); });
                        if (c) openContactEditModal(c);
                    });
                return;
            }
            var delBtn = e.target && e.target.closest('.contact-delete');
            if (delBtn) {
                e.preventDefault();
                var id = delBtn.getAttribute('data-contact-id');
                if (!id) return;
                window._contactDeletePendingId = id;
                var modal = document.getElementById('contactDeleteModal');
                if (modal && window.bootstrap) {
                    var m = new window.bootstrap.Modal(modal);
                    m.show();
                }
            }
        });

        var btnConfirmContactDelete = document.getElementById('btn-confirm-contact-delete');
        if (btnConfirmContactDelete) {
            btnConfirmContactDelete.addEventListener('click', function() {
                var id = window._contactDeletePendingId;
                if (!id) return;
                window._contactDeletePendingId = null;
                var modal = document.getElementById('contactDeleteModal');
                if (modal && window.bootstrap) {
                    var m = window.bootstrap.Modal.getInstance(modal);
                    if (m) m.hide();
                }
                fetch('/api/dashboard/contacts/' + id, { method: 'DELETE', credentials: 'same-origin' })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.error) { alert(data.error); return; }
                        refreshContactsTab();
                    })
                    .catch(function(e) { console.error(e); alert('Could not delete contact.'); });
            });
        }

        function openContactEditModal(c) {
            document.getElementById('contactModalLabel').textContent = 'Edit contact';
            document.getElementById('contact-form-id').value = c.id || '';
            document.getElementById('contact-category').value = c.category || '';
            document.getElementById('contact-organization').value = c.organization || '';
            document.getElementById('contact-name').value = c.contact_name || '';
            document.getElementById('contact-email').value = c.email || '';
            document.getElementById('contact-phone').value = c.phone || '';
            document.getElementById('contact-role').value = c.role || '';
            var modal = document.getElementById('contactModal');
            if (modal && window.bootstrap) {
                var m = new window.bootstrap.Modal(modal);
                m.show();
            }
        }

        // When "Add payment method" button is clicked, set modal context first (capture phase) so "Save for future" is hidden
        document.querySelectorAll('[data-bs-target="#addPaymentMethodModal"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var modal = document.getElementById('addPaymentMethodModal');
                if (modal) modal.setAttribute('data-payment-context', this.getAttribute('data-payment-context') || 'add_method');
            }, true);
        });

        var addPaymentMethodModal = document.getElementById('addPaymentMethodModal');
        if (addPaymentMethodModal) {
            addPaymentMethodModal.addEventListener('shown.bs.modal', function() {
                var context = this.getAttribute('data-payment-context') || 'add_method';
                var saveWrap = document.getElementById('payment-save-for-future-wrap');
                var btn = document.getElementById('btn-process-payment');
                if (context === 'add_method') {
                    if (saveWrap) saveWrap.classList.add('d-none');
                    if (btn) btn.textContent = 'Add payment method';
                } else {
                    if (saveWrap) saveWrap.classList.remove('d-none');
                    if (btn) btn.textContent = 'Process Payment';
                }
            });
        }

        var btnProcessPayment = document.getElementById('btn-process-payment');
        if (btnProcessPayment) {
            btnProcessPayment.addEventListener('click', function() {
                var form = document.getElementById('form-add-payment-method');
                if (!form) return;
                var modal = document.getElementById('addPaymentMethodModal');
                var context = (modal && modal.getAttribute('data-payment-context')) || 'add_method';
                var fd = new FormData(form);
                var payload = {
                    payment_type: fd.get('payment_type') || '',
                    card_number: (fd.get('card_number') || '').trim(),
                    expiry: (fd.get('expiry') || '').trim(),
                    cvc: (fd.get('cvc') || '').trim(),
                    save_for_future: context === 'add_method' ? true : (document.getElementById('payment-save-for-future')?.checked || false)
                };
                fetch('/api/account/payment-methods/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var modal = document.getElementById('addPaymentMethodModal');
                    if (modal && window.bootstrap) {
                        var bsModal = window.bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    }
                    if (data && data.error) {
                        alert(data.error);
                        return;
                    }
                    // Upgrade flow: payment accepted by default; save card if requested, then upgrade via fetch and refresh fragment
                    if (context === 'switch_plan') {
                        if (data && data.success && data.saved && data.payment_method) {
                            appendPaymentMethodCard(data.payment_method);
                            if (typeof window.SUBSCRIPTION_PAYMENT_METHODS !== 'undefined') {
                                window.SUBSCRIPTION_PAYMENT_METHODS.push(data.payment_method);
                            }
                        }
                        form.reset();
                        var formUpgrade = document.getElementById('form-subscription-upgrade');
                        var inputPlanId = formUpgrade && document.getElementById('input-subscription-id');
                        if (!formUpgrade || !inputPlanId || !inputPlanId.value) return;
                        var fd = new FormData();
                        fd.append('subscription_id', inputPlanId.value);
                        var csrf = formUpgrade.querySelector('input[name=csrf_token]');
                        if (csrf && csrf.value) fd.append('csrf_token', csrf.value);
                        fetch(formUpgrade.action || '/api/account/subscription/upgrade', {
                            method: 'POST',
                            headers: { 'X-Requested-With': 'XMLHttpRequest' },
                            body: fd
                        })
                        .then(function(r) { return r.json().then(function(data) { return { ok: r.ok, data: data }; }); })
                        .then(function(result) {
                            if (result.ok && result.data && result.data.success) {
                                refreshAccountSubscriptionsFragment(result.data.message || 'Your plan has been updated.');
                            } else {
                                alert(result.data && result.data.error ? result.data.error : 'Upgrade failed.');
                            }
                        })
                        .catch(function(e) {
                            console.error(e);
                            alert('Could not upgrade plan.');
                        });
                        return;
                    }
                    if (data && data.success && data.saved && data.payment_method) {
                        appendPaymentMethodCard(data.payment_method);
                        if (typeof window.SUBSCRIPTION_PAYMENT_METHODS !== 'undefined') {
                            window.SUBSCRIPTION_PAYMENT_METHODS.push(data.payment_method);
                        }
                        form.reset();
                        alert(data.message || 'Payment method saved.');
                        return;
                    }
                    alert(data && data.message ? data.message : 'Payment processing is not implemented yet.');
                })
                .catch(function(e) {
                    console.error(e);
                    alert('Could not save payment method.');
                });
            });
        }

        // Switch plan: show payment modal (add details vs use existing / add new). Use delegation so it works after fragment replace.
        var paymentMethods = (typeof window.SUBSCRIPTION_PAYMENT_METHODS !== 'undefined') ? window.SUBSCRIPTION_PAYMENT_METHODS : [];
        var switchPlanModal = document.getElementById('switchPlanPaymentModal');
        var switchPlanNoPayment = document.getElementById('switch-plan-prompt-no-payment');
        var switchPlanHasPayment = document.getElementById('switch-plan-prompt-has-payment');
        var planNameSpan = document.getElementById('switch-plan-modal-plan-name');

        document.addEventListener('click', function(e) {
            var btn = e.target && e.target.closest('.btn-switch-plan');
            if (!btn) return;
            var planId = btn.getAttribute('data-plan-id');
            var planName = btn.getAttribute('data-plan-name') || 'plan';
            var inputPlanId = document.getElementById('input-subscription-id');
            if (inputPlanId) inputPlanId.value = planId || '';
            if (planNameSpan) planNameSpan.textContent = planName;
            if (switchPlanNoPayment) switchPlanNoPayment.classList.add('d-none');
            if (switchPlanHasPayment) switchPlanHasPayment.classList.add('d-none');
            var hasPaymentMethods = document.querySelectorAll('.payment-method-card').length > 0;
            if (hasPaymentMethods) {
                if (switchPlanHasPayment) switchPlanHasPayment.classList.remove('d-none');
            } else {
                if (switchPlanNoPayment) switchPlanNoPayment.classList.remove('d-none');
            }
            if (switchPlanModal && window.bootstrap) {
                var m = new window.bootstrap.Modal(switchPlanModal);
                m.show();
            }
        });

        function refreshAccountSubscriptionsFragment(successMessage) {
            var url = '/api/dashboard/account-subscriptions-fragment?t=' + Date.now();
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, cache: 'no-store' })
                .then(function(r) {
                    if (!r.ok) return Promise.reject(new Error('Could not refresh'));
                    return r.json();
                })
                .then(function(data) {
                    var accountContainer = document.getElementById('account-view-subscriptions');
                    if (accountContainer && data.account) {
                        accountContainer.innerHTML = data.account;
                        if (successMessage) {
                            var alertEl = document.createElement('div');
                            alertEl.className = 'alert alert-success alert-dismissible fade show mb-3';
                            alertEl.setAttribute('role', 'alert');
                            alertEl.innerHTML = successMessage + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
                            accountContainer.insertBefore(alertEl, accountContainer.firstChild);
                            setTimeout(function() {
                                if (alertEl.parentNode) {
                                    var bsAlert = alertEl.classList.contains('show') && window.bootstrap && window.bootstrap.Alert;
                                    if (bsAlert) try { new window.bootstrap.Alert(alertEl).close(); } catch (err) {}
                                    else alertEl.remove();
                                }
                            }, 4000);
                        }
                    }
                    var bannerWrap = document.getElementById('dashboard-subscription-banner-wrap');
                    if (bannerWrap && data.banner !== undefined) {
                        bannerWrap.innerHTML = data.banner;
                    }
                    var accountTeamContainer = document.getElementById('account-view-add-user');
                    if (accountTeamContainer && data.account_team) {
                        accountTeamContainer.innerHTML = data.account_team;
                    }
                })
                .catch(function(err) {
                    console.error(err);
                    if (successMessage) alert(successMessage);
                });
        }

        var btnAddDetails = document.getElementById('switch-plan-btn-add-details');
        if (btnAddDetails) {
            btnAddDetails.addEventListener('click', function() {
                if (switchPlanModal && window.bootstrap) {
                    var m = window.bootstrap.Modal.getInstance(switchPlanModal);
                    if (m) m.hide();
                }
                var addModal = document.getElementById('addPaymentMethodModal');
                if (addModal) addModal.setAttribute('data-payment-context', 'switch_plan');
                if (addModal && window.bootstrap) {
                    var addM = new window.bootstrap.Modal(addModal);
                    addM.show();
                }
            });
        }

        var btnUseExisting = document.getElementById('switch-plan-btn-use-existing');
        if (btnUseExisting) {
            btnUseExisting.addEventListener('click', function() {
                if (switchPlanModal && window.bootstrap) {
                    var m = window.bootstrap.Modal.getInstance(switchPlanModal);
                    if (m) m.hide();
                }
                var formUpgrade = document.getElementById('form-subscription-upgrade');
                var inputPlanId = formUpgrade && document.getElementById('input-subscription-id');
                if (!formUpgrade || !inputPlanId || !inputPlanId.value) return;
                var fd = new FormData();
                fd.append('subscription_id', inputPlanId.value);
                var csrf = formUpgrade.querySelector('input[name=csrf_token]');
                if (csrf && csrf.value) fd.append('csrf_token', csrf.value);
                fetch(formUpgrade.action || '/api/account/subscription/upgrade', {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: fd
                })
                .then(function(r) { return r.json().then(function(data) { return { ok: r.ok, data: data }; }); })
                .then(function(result) {
                    if (result.ok && result.data && result.data.success) {
                        refreshAccountSubscriptionsFragment(result.data.message || 'Your plan has been updated.');
                    } else {
                        alert(result.data && result.data.error ? result.data.error : 'Upgrade failed.');
                    }
                })
                .catch(function(e) {
                    console.error(e);
                    alert('Could not upgrade plan.');
                });
            });
        }

        var btnAddNew = document.getElementById('switch-plan-btn-add-new');
        if (btnAddNew) {
            btnAddNew.addEventListener('click', function() {
                if (switchPlanModal && window.bootstrap) {
                    var m = window.bootstrap.Modal.getInstance(switchPlanModal);
                    if (m) m.hide();
                }
                var addModal = document.getElementById('addPaymentMethodModal');
                if (addModal) addModal.setAttribute('data-payment-context', 'switch_plan');
                if (addModal && window.bootstrap) {
                    var addM = new window.bootstrap.Modal(addModal);
                    addM.show();
                }
            });
        }

        // Invoice download (placeholder: to be implemented)
        document.querySelectorAll('.invoice-download-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var id = this.getAttribute('data-invoice-id');
                if (id) { /* TODO: call download endpoint when implemented */ }
                alert('Invoice download will be available soon.');
            });
        });

        // Update profile form: submit via AJAX so page does not reload
        var formUpdateProfile = document.getElementById('form-update-profile');
        if (formUpdateProfile) {
            formUpdateProfile.addEventListener('submit', function(e) {
                e.preventDefault();
                var form = this;
                var modal = form.closest('.modal');
                var fd = new FormData(form);
                fetch(form.action || '/update-profile', {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: fd
                })
                .then(function(r) { return r.json().then(function(data) { return { ok: r.ok, data: data }; }); })
                .then(function(result) {
                    if (result.ok && result.data && result.data.success) {
                        if (modal && window.bootstrap) {
                            var m = window.bootstrap.Modal.getInstance(modal);
                            if (m) m.hide();
                        }
                        alert(result.data.message || 'Profile updated.');
                    } else {
                        alert(result.data && result.data.error ? result.data.error : 'Could not update profile.');
                    }
                })
                .catch(function(err) {
                    console.error(err);
                    alert('Could not update profile.');
                });
            });
        }

        // Set or clear default payment method — use delegation so dynamically added cards work
        document.addEventListener('change', function(e) {
            if (!e.target || !e.target.classList.contains('payment-method-set-default')) return;
            var methodId = e.target.getAttribute('data-method-id');
            var self = e.target;
            if (e.target.checked) {
                if (!methodId) return;
                fetch('/api/account/payment-methods/set-default', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ payment_method_id: parseInt(methodId, 10) })
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof refreshAccountSubscriptionsFragment === 'function') {
                            refreshAccountSubscriptionsFragment();
                        } else {
                            var wrap = document.getElementById('next-billing-date-wrap');
                            if (wrap) wrap.classList.remove('d-none');
                            document.querySelectorAll('.payment-method-set-default').forEach(function(cb) {
                                if (cb !== self) cb.checked = false;
                            });
                        }
                    } else if (data && data.error) {
                        alert(data.error);
                        self.checked = false;
                    }
                })
                .catch(function(e) {
                    console.error(e);
                    self.checked = false;
                });
            } else {
                fetch('/api/account/payment-methods/clear-default', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof refreshAccountSubscriptionsFragment === 'function') {
                            refreshAccountSubscriptionsFragment();
                        }
                        // When no fragment refresh: next-billing-date-wrap stays visible with "AutoPay not enabled"
                    } else if (data && data.error) {
                        alert(data.error);
                        self.checked = true;
                    }
                })
                .catch(function(e) {
                    console.error(e);
                    self.checked = true;
                });
            }
        });

        // Remove payment method — show confirmation modal (styled like add payment method), then remove on confirm
        var removePaymentMethodPending = null;
        document.addEventListener('click', function(e) {
            var btn = e.target && e.target.closest('.subscription-remove-method');
            if (!btn) return;
            e.preventDefault();
            var id = btn.getAttribute('data-method-id');
            if (!id) return;
            var cardCol = btn.closest('.payment-methods-grid .col-6') || btn.closest('[class*="col-"]');
            var card = cardCol && cardCol.querySelector('.payment-method-card');
            var label = 'this payment method';
            if (card) {
                var brandEl = card.querySelector('.payment-method-card-brand-name');
                var last4El = card.querySelector('.payment-method-card-last4');
                if (brandEl && last4El) label = (brandEl.textContent || '').trim() + ' ' + (last4El.textContent || '').trim();
                else if (last4El) label = last4El.textContent || label;
            }
            removePaymentMethodPending = { method_id: id, cardCol: cardCol, label: label };
            var msgEl = document.getElementById('remove-payment-method-message');
            if (msgEl) msgEl.textContent = 'Are you sure you want to remove ' + label + '?';
            var modal = document.getElementById('removePaymentMethodModal');
            if (modal && window.bootstrap) {
                var m = new window.bootstrap.Modal(modal);
                m.show();
            }
        });

        var btnConfirmRemove = document.getElementById('btn-confirm-remove-payment-method');
        if (btnConfirmRemove) {
            btnConfirmRemove.addEventListener('click', function() {
                if (!removePaymentMethodPending) return;
                var id = removePaymentMethodPending.method_id;
                var cardCol = removePaymentMethodPending.cardCol;
                var grid = document.querySelector('.payment-methods-grid');
                var modal = document.getElementById('removePaymentMethodModal');
                if (modal && window.bootstrap) {
                    var m = window.bootstrap.Modal.getInstance(modal);
                    if (m) m.hide();
                }
                removePaymentMethodPending = null;
                fetch('/api/account/payment-methods/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ method_id: parseInt(id, 10) })
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (typeof refreshAccountSubscriptionsFragment === 'function') {
                            refreshAccountSubscriptionsFragment('Payment method removed.');
                        } else {
                            if (cardCol && cardCol.parentNode) {
                                cardCol.remove();
                                if (grid && grid.children.length === 0) {
                                    var emptyHtml = '<div class="subscription-empty-state">' +
                                        '<i class="bi bi-credit-card subscription-empty-icon"></i>' +
                                        '<p class="subscription-empty-text mb-0">No payment methods added.</p></div>';
                                    if (grid.parentNode) {
                                        var wrap = document.createElement('div');
                                        wrap.innerHTML = emptyHtml;
                                        grid.parentNode.replaceChild(wrap.firstElementChild, grid);
                                    }
                                }
                            }
                        }
                    } else if (data && data.error) {
                        alert(data.error);
                    }
                })
                .catch(function(e) {
                    console.error(e);
                    alert('Could not remove payment method.');
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
