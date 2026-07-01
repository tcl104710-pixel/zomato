/**
 * Zomato AI Restaurant Recommender — Frontend Application
 *
 * Handles:
 *  - Populating dropdowns from /api/meta endpoints
 *  - Collecting user preferences and submitting to /api/recommend
 *  - Rendering recommendation cards with stars, budgets, and AI explanations
 *  - Loading states, error handling, and keyboard navigation
 */

(() => {
    'use strict';

    // ── Configuration ────────────────────────────────────────────
    const IS_PROD = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
    const API_BASE = IS_PROD 
        ? 'https://zomato-production-eeb1.up.railway.app' 
        : window.location.origin;

    // ── DOM References ───────────────────────────────────────────
    const $  = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        form:             $('#recommendation-form'),
        locationSelect:   $('#location-select'),
        budgetSelect:     $('#budget-select'),
        cuisineSelect:    $('#cuisine-select'),
        minRating:        $('#min-rating'),
        ratingDisplay:    $('#rating-display'),
        additionalPrefs:  $('#additional-prefs'),
        submitBtn:        $('#recommend-btn'),
        loadingOverlay:   $('#loading-overlay'),
        errorToast:       $('#error-toast'),
        errorMessage:     $('#error-message'),
        errorClose:       $('#error-close'),
        resultsSection:   $('#results-section'),
        filtersBar:       $('#filters-bar'),
        aiSummary:        $('#ai-summary'),
        relaxationNotice: $('#relaxation-notice'),
        resultsContainer: $('#results-container'),
        emptyState:       $('#empty-state'),
        emptyMessage:     $('#empty-state-message'),
        tryAgainBtn:      $('#try-again-btn'),
    };


    // ── State ────────────────────────────────────────────────────
    let isLoading = false;
    let errorTimer = null;


    // ── Init ─────────────────────────────────────────────────────
    function init() {
        fetchLocations();
        fetchCuisines();
        bindEvents();
    }


    // ── Event Binding ────────────────────────────────────────────
    function bindEvents() {
        dom.form.addEventListener('submit', handleSubmit);

        dom.minRating.addEventListener('input', () => {
            dom.ratingDisplay.textContent = parseFloat(dom.minRating.value).toFixed(1);
        });

        dom.errorClose.addEventListener('click', hideError);

        dom.tryAgainBtn.addEventListener('click', () => {
            hideResults();
            dom.form.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });

        // Keyboard: Enter on form (not textarea) triggers submit
        dom.form.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                dom.form.requestSubmit();
            }
        });
    }


    // ── API: Fetch Locations ─────────────────────────────────────
    async function fetchLocations() {
        try {
            const res = await fetch(`${API_BASE}/api/meta/locations`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            dom.locationSelect.innerHTML = '<option value="" disabled selected>Select a location</option>';
            data.locations.forEach((loc) => {
                const opt = document.createElement('option');
                opt.value = loc;
                opt.textContent = loc;
                dom.locationSelect.appendChild(opt);
            });
        } catch (err) {
            console.error('Failed to fetch locations:', err);
            dom.locationSelect.innerHTML = '<option value="" disabled selected>Failed to load</option>';
            showError('Could not load locations. Is the server running?');
        }
    }


    // ── API: Fetch Cuisines ──────────────────────────────────────
    async function fetchCuisines() {
        try {
            const res = await fetch(`${API_BASE}/api/meta/cuisines`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            // Keep the "Any cuisine" default
            const firstOpt = dom.cuisineSelect.querySelector('option');
            dom.cuisineSelect.innerHTML = '';
            dom.cuisineSelect.appendChild(firstOpt);

            data.cuisines.forEach((c) => {
                const opt = document.createElement('option');
                opt.value = c;
                // Title-case display
                opt.textContent = c.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                dom.cuisineSelect.appendChild(opt);
            });
        } catch (err) {
            console.error('Failed to fetch cuisines:', err);
        }
    }


    // ── Form Submit Handler ──────────────────────────────────────
    async function handleSubmit(e) {
        e.preventDefault();

        if (isLoading) return;

        const location = dom.locationSelect.value;
        if (!location) {
            showError('Please select a location.');
            dom.locationSelect.focus();
            return;
        }

        const payload = {
            location: location,
            budget: dom.budgetSelect.value,
            cuisine: dom.cuisineSelect.value || null,
            min_rating: parseFloat(dom.minRating.value),
            additional_preferences: dom.additionalPrefs.value.trim() || null,
        };

        showLoading();
        hideResults();
        hideError();

        try {
            const res = await fetch(`${API_BASE}/api/recommend`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                if (res.status === 422 && errData.detail) {
                    const msg = errData.detail.map(d => d.msg).join('; ');
                    throw new Error(`Validation error: ${msg}`);
                }
                throw new Error(errData.detail || `Server error (${res.status})`);
            }

            const data = await res.json();
            hideLoading();
            renderResults(data, payload);

        } catch (err) {
            hideLoading();
            console.error('Recommendation request failed:', err);
            showError(err.message || 'Failed to get recommendations. Please try again.');
        }
    }


    // ── Render Results ───────────────────────────────────────────
    function renderResults(data, payload) {
        if (!data.recommendations || data.recommendations.length === 0) {
            showEmptyState(data);
            return;
        }

        // Filters bar
        renderFiltersBar(data.filters_applied, data.total_matches);

        // AI Summary
        renderSummary(data.summary);

        // Relaxation notice
        if (data.relaxation_notice) {
            dom.relaxationNotice.textContent = data.relaxation_notice;
            dom.relaxationNotice.hidden = false;
        } else {
            dom.relaxationNotice.hidden = true;
        }

        // Cards
        dom.resultsContainer.innerHTML = '';
        data.recommendations.forEach((rec) => {
            dom.resultsContainer.appendChild(renderCard(rec));
        });

        dom.resultsSection.hidden = false;
        dom.emptyState.hidden = true;

        // Smooth scroll to results
        setTimeout(() => {
            dom.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }


    // ── Render Filters Bar ───────────────────────────────────────
    function renderFiltersBar(filters, totalMatches) {
        dom.filtersBar.innerHTML = '';

        const label = document.createElement('span');
        label.className = 'results__filter-tag results__filter-tag--label';
        label.textContent = `${totalMatches} match${totalMatches !== 1 ? 'es' : ''} ·`;
        dom.filtersBar.appendChild(label);

        if (filters.location) addTag(filters.location, '📍');
        if (filters.budget) addTag(budgetLabel(filters.budget), '💰');
        if (filters.cuisine) addTag(titleCase(filters.cuisine), '🍽️');
        if (filters.min_rating != null) addTag(`≥ ${filters.min_rating}★`, '⭐');

        function addTag(text, icon) {
            const tag = document.createElement('span');
            tag.className = 'results__filter-tag';
            tag.textContent = `${icon} ${text}`;
            dom.filtersBar.appendChild(tag);
        }
    }


    // ── Render AI Summary ────────────────────────────────────────
    function renderSummary(summaryText) {
        dom.aiSummary.innerHTML = `
            <div class="results__summary-label">
                <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"/></svg>
                AI Summary
            </div>
            <p>${escapeHtml(summaryText)}</p>
        `;
    }


    // ── Render Single Card ───────────────────────────────────────
    function renderCard(rec) {
        const card = document.createElement('article');
        card.className = 'card';

        const cost = rec.estimated_cost_for_two;
        const budgetTier = cost <= 500 ? 'low' : cost <= 1500 ? 'medium' : 'high';
        const budgetSymbols = cost <= 500 ? '₹' : cost <= 1500 ? '₹₹' : '₹₹₹';

        const explanationId = `explanation-${rec.rank}`;

        const primaryCuisine = rec.cuisine ? rec.cuisine.split(',')[0].trim().toLowerCase() : 'food';
        const imageUrl = `https://loremflickr.com/600/340/${encodeURIComponent(primaryCuisine)},food/all?lock=${rec.rank}`;
        const fallbackUrl = 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80';

        card.innerHTML = `
            <div class="card__image-container">
                <img src="${imageUrl}" alt="${escapeHtml(rec.restaurant_name)}" class="card__image" loading="lazy" onerror="this.onerror=null; this.src='${fallbackUrl}';">
                <div class="card__badge">${rec.rank === 1 ? '🥇 Top Match' : 'Recommended'}</div>
                <div class="card__rank ${rec.rank === 1 ? 'card__rank--1' : ''}">#${rec.rank}</div>
            </div>
            <div class="card__body">
                <div class="card__header">
                    <h3 class="card__name">${escapeHtml(rec.restaurant_name)}</h3>
                    <div class="card__meta">
                        <span class="card__meta-item">
                            ${renderStars(rec.rating)}
                            <span class="card__rating-num">${rec.rating.toFixed(1)}</span>
                        </span>
                        <span class="card__meta-item card__budget card__budget--${budgetTier}" title="Estimated cost for two: ₹${cost.toFixed(0)}">
                            ${budgetSymbols} ~₹${formatCost(cost)}
                        </span>
                        <span class="card__meta-item">
                            ${formatCuisines(rec.cuisine)}
                        </span>
                    </div>
                </div>

                <div class="card__explanation">
                    <div class="card__explanation-label"
                         role="button"
                         tabindex="0"
                         aria-expanded="true"
                         aria-controls="${explanationId}"
                         onclick="this.setAttribute('aria-expanded', this.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'); document.getElementById('${explanationId}').dataset.collapsed = this.getAttribute('aria-expanded') === 'false';">
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"/></svg>
                        Why this restaurant?
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" style="margin-left:auto"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
                    </div>
                    <p class="card__explanation-text" id="${explanationId}" data-collapsed="false">
                        ${escapeHtml(rec.explanation)}
                    </p>
                </div>
            </div>
        `;

        return card;
    }


    // ── Star Rating Renderer ─────────────────────────────────────
    function renderStars(rating) {
        const fullStars = Math.floor(rating);
        const hasHalf = (rating % 1) >= 0.3;
        const emptyStars = 5 - fullStars - (hasHalf ? 1 : 0);
        let html = '<span class="card__stars" title="' + rating.toFixed(1) + ' out of 5">';

        const starSvg = `<svg class="card__star card__star--filled" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>`;
        const halfSvg = `<svg class="card__star card__star--half" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>`;
        const emptySvg = `<svg class="card__star card__star--empty" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>`;

        for (let i = 0; i < fullStars; i++) html += starSvg;
        if (hasHalf) html += halfSvg;
        for (let i = 0; i < emptyStars; i++) html += emptySvg;

        html += '</span>';
        return html;
    }


    // ── Format Helpers ───────────────────────────────────────────
    function formatCost(cost) {
        return cost >= 1000 ? (cost / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : cost.toFixed(0);
    }

    function formatCuisines(cuisineStr) {
        if (!cuisineStr) return '';
        const cuisines = cuisineStr.split(',').map(c => c.trim()).filter(Boolean);
        return cuisines.map(c =>
            `<span class="card__cuisine-tag">${escapeHtml(titleCase(c))}</span>`
        ).join(' ');
    }

    function titleCase(str) {
        return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    }

    function budgetLabel(budget) {
        const labels = { low: 'Low (≤₹500)', medium: 'Medium (₹501–1500)', high: 'High (₹1501+)' };
        return labels[budget] || budget;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }


    // ── Loading State ────────────────────────────────────────────
    function showLoading() {
        isLoading = true;
        dom.loadingOverlay.hidden = false;
        dom.submitBtn.disabled = true;
        dom.submitBtn.classList.add('form__submit--loading');
        dom.submitBtn.querySelector('span').textContent = 'Finding restaurants...';
    }

    function hideLoading() {
        isLoading = false;
        dom.loadingOverlay.hidden = true;
        dom.submitBtn.disabled = false;
        dom.submitBtn.classList.remove('form__submit--loading');
        dom.submitBtn.querySelector('span').textContent = 'Get Recommendations';
    }


    // ── Error Toast ──────────────────────────────────────────────
    function showError(msg) {
        dom.errorMessage.textContent = msg;
        dom.errorToast.hidden = false;
        // Force reflow for transition
        dom.errorToast.offsetHeight;
        dom.errorToast.dataset.visible = 'true';

        // Auto-dismiss after 6 seconds
        clearTimeout(errorTimer);
        errorTimer = setTimeout(hideError, 6000);
    }

    function hideError() {
        clearTimeout(errorTimer);
        dom.errorToast.dataset.visible = 'false';
        setTimeout(() => { dom.errorToast.hidden = true; }, 400);
    }


    // ── Results Visibility ───────────────────────────────────────
    function hideResults() {
        dom.resultsSection.hidden = true;
        dom.emptyState.hidden = true;
    }

    function showEmptyState(data) {
        dom.emptyState.hidden = false;
        dom.resultsSection.hidden = true;

        let msg = 'Try adjusting your filters — a wider budget, different cuisine, or lower rating might help.';
        if (data && data.relaxation_notice) {
            msg = data.relaxation_notice;
        }
        dom.emptyMessage.textContent = msg;
    }


    // ── Bootstrap ────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
