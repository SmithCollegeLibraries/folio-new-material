/* ─────────────────────────────────────────────────────────────────────
   FOLIO New Materials — client app
   Reads embedded JSON from <script type="application/json" id="items-data">
   and builds both grid and table views.  Filters, sorts, and view toggle
   operate on the rendered DOM (avoids re-rendering on each interaction).
   ───────────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var STORAGE_KEY = 'folio-new-materials:view';

  // ── Load embedded data ──────────────────────────────────────────────
  var dataEl = document.getElementById('items-data');
  if (!dataEl) {
    console.error('[folio] items-data block missing');
    return;
  }

  var data;
  try {
    data = JSON.parse(dataEl.textContent);
  } catch (err) {
    console.error('[folio] failed to parse items data', err);
    return;
  }
  var items = data.items || [];

  // ── DOM helpers ─────────────────────────────────────────────────────
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      for (var key in attrs) {
        if (key === 'class')      node.className = attrs[key];
        else if (key === 'data')  Object.assign(node.dataset, attrs[key]);
        else if (key === 'style') node.setAttribute('style', attrs[key]);
        else if (key.indexOf('aria-') === 0 || key === 'role')
                                  node.setAttribute(key, attrs[key]);
        else                      node[key] = attrs[key];
      }
    }
    if (children) {
      for (var i = 0; i < children.length; i++) {
        var c = children[i];
        if (c == null || c === false) continue;
        node.appendChild(typeof c === 'string'
          ? document.createTextNode(c)
          : c);
      }
    }
    return node;
  }

  function dataAttrs(item) {
    return {
      data: {
        type:    item.type_uuid || '',
        subject: item.subject_group || '',
        title:   (item.title || '').toLowerCase(),
        author:  (item.author || '').toLowerCase(),
        date:    item.receipt_date || ''
      }
    };
  }

  // ── Build a single grid card ────────────────────────────────────────
  function buildCard(item, index) {
    var coverChild = item.cover_url
      ? el('img', {
          class:   'card-cover',
          src:     item.cover_url,
          alt:     'Cover of ' + item.title,
          loading: 'lazy'
        })
      : el('div', {
          class: 'card-placeholder',
          style: '--placeholder-color: ' + (item.placeholder_color || '#5a6c7d') + ';',
          'aria-hidden': 'true'
        }, [
          el('span', { class: 'ph-type'  }, [item.type_label || 'Item']),
          el('span', { class: 'ph-title' }, [item.title || ''])
        ]);

    var titleNode = item.eds_url
      ? el('a', { href: item.eds_url, target: '_blank', rel: 'noopener noreferrer' }, [item.title || ''])
      : document.createTextNode(item.title || '');

    var bodyChildren = [
      el('h2', { class: 'card-title', id: 'grid-title-' + index }, [titleNode])
    ];
    if (item.author) {
      bodyChildren.push(el('p', { class: 'card-author' }, [item.author]));
    }
    if (item.publisher || item.year) {
      var pubText = (item.publisher || '') +
                    (item.publisher && item.year ? ', ' : '') +
                    (item.year || '');
      bodyChildren.push(el('p', { class: 'card-publisher' }, [pubText]));
    }
    if (item.call_number) {
      bodyChildren.push(el('p', { class: 'card-callno' }, [item.call_number]));
    }

    var metaChildren = [
      el('span', { class: 'badge' }, [item.type_label || 'Other'])
    ];
    if (item.subject_group) {
      metaChildren.push(el('span', { class: 'badge badge-subject' }, [item.subject_group]));
    }
    if (item.receipt_date) {
      metaChildren.push(el('span', { class: 'card-received', title: 'Received' }, [
        el('span', { class: 'sr-only' }, ['Received: ']),
        item.receipt_date
      ]));
    }
    bodyChildren.push(el('div', { class: 'card-meta' }, metaChildren));

    var article = el('article', { 'aria-labelledby': 'grid-title-' + index }, [
      el('div', { class: 'card-cover-wrap' }, [coverChild]),
      el('div', { class: 'card-body' }, bodyChildren)
    ]);

    var attrs = dataAttrs(item);
    attrs.class = 'material-card filterable-item';
    return el('li', attrs, [article]);
  }

  // ── Build a single table row ────────────────────────────────────────
  function buildRow(item, hasSubject) {
    var coverChild = item.cover_url
      ? el('img', { src: item.cover_url, alt: '', loading: 'lazy' })
      : el('div', {
          class: 'ph-mini',
          style: '--placeholder-color: ' + (item.placeholder_color || '#5a6c7d') + ';',
          'aria-hidden': 'true'
        });

    var titleChildren = [];
    if (item.eds_url) {
      titleChildren.push(el('a', {
        class:  'row-title',
        href:   item.eds_url,
        target: '_blank',
        rel:    'noopener noreferrer'
      }, [item.title || '']));
    } else {
      titleChildren.push(el('span', { class: 'row-title' }, [item.title || '']));
    }
    if (item.publisher || item.year) {
      var meta = (item.publisher || '') +
                 (item.publisher && item.year ? ', ' : '') +
                 (item.year || '');
      titleChildren.push(el('div', { class: 'col-meta' }, [meta]));
    }

    var cells = [
      el('td', { class: 'col-cover' }, [coverChild]),
      el('td', null, titleChildren),
      el('td', { class: 'col-meta' }, [item.author || '']),
      el('td', { class: 'col-meta' }, [item.type_label || ''])
    ];
    if (hasSubject) {
      cells.push(el('td', { class: 'col-meta' }, [item.subject_group || '']));
    }
    cells.push(
      el('td', { class: 'col-meta' }, [item.call_number || '']),
      el('td', { class: 'col-meta col-date' }, [item.receipt_date || ''])
    );

    var attrs = dataAttrs(item);
    attrs.class = 'material-row filterable-item';
    return el('tr', attrs, cells);
  }

  // ── Render both views ───────────────────────────────────────────────
  var grid       = document.getElementById('materials-grid');
  var tableWrap  = document.getElementById('materials-table-wrap');
  var tableBody  = tableWrap ? tableWrap.querySelector('tbody') : null;
  var hasSubject = !!document.getElementById('subject-filter');

  if (grid) {
    items.forEach(function (item, i) { grid.appendChild(buildCard(item, i)); });
  }
  if (tableBody) {
    items.forEach(function (item) { tableBody.appendChild(buildRow(item, hasSubject)); });
  }

  var cards = grid ? [].slice.call(grid.querySelectorAll('.material-card')) : [];
  var rows  = tableBody ? [].slice.call(tableBody.querySelectorAll('.material-row')) : [];

  // ── View toggle ─────────────────────────────────────────────────────
  var viewButtons = document.querySelectorAll('.view-toggle button');
  function setView(view) {
    if (view !== 'grid' && view !== 'table') view = 'grid';
    if (grid)      grid.hidden      = view !== 'grid';
    if (tableWrap) tableWrap.hidden = view !== 'table';
    viewButtons.forEach(function (btn) {
      btn.setAttribute('aria-pressed', btn.dataset.view === view ? 'true' : 'false');
    });
    try { localStorage.setItem(STORAGE_KEY, view); } catch (e) { /* ignore */ }
  }
  viewButtons.forEach(function (btn) {
    btn.addEventListener('click', function () { setView(btn.dataset.view); });
  });
  try {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved) setView(saved);
  } catch (e) { /* ignore */ }

  // ── Filtering ───────────────────────────────────────────────────────
  var searchInput   = document.getElementById('search-input');
  var formatSelect  = document.getElementById('format-filter');
  var subjectSelect = document.getElementById('subject-filter');
  var sortSelect    = document.getElementById('sort-select');
  var clearBtn      = document.getElementById('clear-filters');
  var chipsHost     = document.getElementById('active-filters');
  var counter       = document.getElementById('results-count');
  var noResults     = document.getElementById('no-results');

  function getState() {
    return {
      search:  (searchInput && searchInput.value || '').trim().toLowerCase(),
      format:  formatSelect ? formatSelect.value : 'all',
      subject: subjectSelect ? subjectSelect.value : 'all'
    };
  }

  function matches(node, state) {
    if (state.format !== 'all'  && node.dataset.type !== state.format)   return false;
    if (state.subject !== 'all' && node.dataset.subject !== state.subject) return false;
    if (state.search) {
      var hay = node.dataset.title + ' ' + node.dataset.author;
      if (hay.indexOf(state.search) === -1) return false;
    }
    return true;
  }

  function renderChips(state) {
    if (!chipsHost) return;
    chipsHost.textContent = '';
    var any = false;

    function addChip(label, onClear) {
      any = true;
      var btn = el('button', {
        type: 'button',
        'aria-label': 'Remove filter ' + label
      }, ['×']);
      btn.addEventListener('click', onClear);
      var chip = el('span', { class: 'filter-chip' }, [label + ' ', btn]);
      chipsHost.appendChild(chip);
    }

    if (state.format !== 'all' && formatSelect) {
      var opt = formatSelect.options[formatSelect.selectedIndex];
      addChip('Format: ' + opt.text.replace(/\s*\(\d+\)$/, ''), function () {
        formatSelect.value = 'all'; applyFilters();
      });
    }
    if (subjectSelect && state.subject !== 'all') {
      var s = subjectSelect.options[subjectSelect.selectedIndex];
      addChip('Subject: ' + s.text.replace(/\s*\(\d+\)$/, ''), function () {
        subjectSelect.value = 'all'; applyFilters();
      });
    }
    if (state.search) {
      addChip('Search: "' + state.search + '"', function () {
        searchInput.value = ''; applyFilters();
      });
    }
    if (clearBtn) clearBtn.hidden = !any;
  }

  function applyFilters() {
    var state = getState();
    var visible = 0;
    cards.forEach(function (node) {
      var show = matches(node, state);
      node.hidden = !show;
      if (show) visible++;
    });
    rows.forEach(function (node) {
      node.hidden = !matches(node, state);
    });
    if (counter) {
      counter.textContent = 'Showing ' + visible + ' item' + (visible !== 1 ? 's' : '');
    }
    if (noResults) noResults.hidden = visible > 0;
    renderChips(state);
  }

  function clearAll() {
    if (searchInput)   searchInput.value = '';
    if (formatSelect)  formatSelect.value = 'all';
    if (subjectSelect) subjectSelect.value = 'all';
    applyFilters();
  }

  // ── Sorting ─────────────────────────────────────────────────────────
  function cmp(a, b, mode) {
    if (mode === 'newest')    return (b.dataset.date || '').localeCompare(a.dataset.date || '');
    if (mode === 'oldest')    return (a.dataset.date || '').localeCompare(b.dataset.date || '');
    if (mode === 'title-asc') return (a.dataset.title || '').localeCompare(b.dataset.title || '');
    if (mode === 'title-desc')return (b.dataset.title || '').localeCompare(a.dataset.title || '');
    return 0;
  }

  function applySort() {
    if (!sortSelect) return;
    var mode = sortSelect.value;
    if (grid)      cards.slice().sort(function (a, b) { return cmp(a, b, mode); })
                                .forEach(function (n) { grid.appendChild(n); });
    if (tableBody) rows.slice().sort(function (a, b) { return cmp(a, b, mode); })
                                .forEach(function (n) { tableBody.appendChild(n); });
  }

  // ── Wire up ─────────────────────────────────────────────────────────
  if (searchInput)   searchInput.addEventListener('input',  applyFilters);
  if (formatSelect)  formatSelect.addEventListener('change', applyFilters);
  if (subjectSelect) subjectSelect.addEventListener('change', applyFilters);
  if (sortSelect)    sortSelect.addEventListener('change',  applySort);
  if (clearBtn)      clearBtn.addEventListener('click',     clearAll);
}());
