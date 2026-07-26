/**
 * Reusable sortable + filterable + paginated table.
 *
 * Sorting: give a <table> the class "ars-sortable-table", an id, and
 * `data-page-size="N"`. Each sortable <th> needs `data-sort-key="foo"`,
 * and its matching <td> needs the same `data-sort-key="foo"` plus a
 * `data-sort-value="..."` attribute holding the raw value to sort by.
 *
 * Filtering (optional): any input/checkbox with `data-filter-for="<table id>"`
 * drives a live filter:
 *   - data-filter-key="name"            -> substring match (search input)
 *   - data-filter-key="score"           -> data-filter-type="min"|"max" (number inputs)
 *   - data-filter-key="recommendation"  -> checkbox, its `value` is matched
 *     against the row's recommendation `data-sort-value` (OR'd if multiple checked)
 *
 * Pagination controls render into any element with `data-pagination-for="<table id>"`.
 * A live result count can render into `data-result-count-for="<table id>"`.
 * The comma-separated ids of currently *filtered* rows (pre-pagination) are
 * written into an element with `data-result-ids-for="<table id>"` (e.g. a
 * hidden input), so other UI — like export buttons — can act on exactly
 * what's currently visible after filtering.
 */
(function () {
  function initSortableTable(table) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    const allRows = Array.from(tbody.querySelectorAll('tr'));
    const headers = table.querySelectorAll('th[data-sort-key]');
    const pageSize = parseInt(table.dataset.pageSize || '10', 10);

    const paginationEl = document.querySelector('[data-pagination-for="' + table.id + '"]');
    const countEl = document.querySelector('[data-result-count-for="' + table.id + '"]');
    const idsOutputEl = document.querySelector('[data-result-ids-for="' + table.id + '"]');
    const filterControls = Array.from(
      document.querySelectorAll('[data-filter-for="' + table.id + '"]')
    );

    let sortKey = null;
    let sortDir = 1; // 1 = ascending, -1 = descending
    let currentPage = 1;

    function cellValue(row, key) {
      const cell = row.querySelector('td[data-sort-key="' + key + '"]');
      if (!cell) return null;
      return cell.dataset.sortValue !== undefined ? cell.dataset.sortValue : cell.textContent.trim();
    }

    function sortValue(row, key) {
      const raw = cellValue(row, key);
      if (raw === null) return '';
      const num = parseFloat(raw);
      return Number.isNaN(num) ? String(raw).toLowerCase() : num;
    }

    function readFilterState() {
      const state = { search: '', scoreMin: null, scoreMax: null, recommendations: [] };
      filterControls.forEach(function (el) {
        const key = el.dataset.filterKey;
        if (key === 'name') {
          state.search = el.value.trim().toLowerCase();
        } else if (key === 'score') {
          const val = el.value === '' ? null : parseFloat(el.value);
          if (el.dataset.filterType === 'min') state.scoreMin = Number.isNaN(val) ? null : val;
          if (el.dataset.filterType === 'max') state.scoreMax = Number.isNaN(val) ? null : val;
        } else if (key === 'recommendation' && el.checked) {
          state.recommendations.push(el.value);
        }
      });
      return state;
    }

    function matchesFilters(row, state) {
      if (state.search) {
        const name = String(cellValue(row, 'name') || '').toLowerCase();
        if (!name.includes(state.search)) return false;
      }
      if (state.scoreMin !== null || state.scoreMax !== null) {
        const raw = cellValue(row, 'score');
        const score = raw === null ? null : parseFloat(raw);
        if (state.scoreMin !== null && (score === null || Number.isNaN(score) || score < state.scoreMin)) return false;
        if (state.scoreMax !== null && (score === null || Number.isNaN(score) || score > state.scoreMax)) return false;
      }
      if (state.recommendations.length > 0) {
        const rec = cellValue(row, 'recommendation');
        if (state.recommendations.indexOf(rec) === -1) return false;
      }
      return true;
    }

    function render() {
      const filterState = readFilterState();
      const filtered = allRows.filter(function (row) { return matchesFilters(row, filterState); });

      if (sortKey) {
        filtered.sort(function (a, b) {
          const va = sortValue(a, sortKey);
          const vb = sortValue(b, sortKey);
          if (va < vb) return -1 * sortDir;
          if (va > vb) return 1 * sortDir;
          return 0;
        });
      }

      if (countEl) countEl.textContent = String(filtered.length);
      if (idsOutputEl) {
        idsOutputEl.value = filtered
          .map(function (row) { return row.dataset.resultId; })
          .filter(Boolean)
          .join(',');
      }

      const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      currentPage = Math.min(currentPage, totalPages);
      const start = (currentPage - 1) * pageSize;
      const pageRows = filtered.slice(start, start + pageSize);

      tbody.innerHTML = '';
      if (pageRows.length === 0) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = table.querySelectorAll('thead th').length;
        emptyCell.className = 'ars-empty-note text-center';
        emptyCell.textContent = 'No results match the current filters.';
        emptyRow.appendChild(emptyCell);
        tbody.appendChild(emptyRow);
      } else {
        pageRows.forEach(function (row) { tbody.appendChild(row); });
      }

      headers.forEach(function (header) {
        header.classList.remove('ars-sort-asc', 'ars-sort-desc');
        if (header.dataset.sortKey === sortKey) {
          header.classList.add(sortDir === 1 ? 'ars-sort-asc' : 'ars-sort-desc');
        }
      });

      if (paginationEl) renderPagination(totalPages);
    }

    function renderPagination(totalPages) {
      paginationEl.innerHTML = '';
      if (totalPages <= 1) return;

      for (let page = 1; page <= totalPages; page++) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = String(page);
        btn.className = 'ars-page-btn' + (page === currentPage ? ' active' : '');
        btn.addEventListener('click', function () {
          currentPage = page;
          render();
        });
        paginationEl.appendChild(btn);
      }
    }

    headers.forEach(function (header) {
      header.classList.add('ars-sortable-th');
      header.setAttribute('role', 'button');
      header.setAttribute('tabindex', '0');
      header.addEventListener('click', function () {
        if (sortKey === header.dataset.sortKey) {
          sortDir *= -1;
        } else {
          sortKey = header.dataset.sortKey;
          sortDir = 1;
        }
        currentPage = 1;
        render();
      });
      header.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          header.click();
        }
      });
    });

    filterControls.forEach(function (el) {
      const eventName = (el.type === 'checkbox' || el.tagName === 'SELECT') ? 'change' : 'input';
      el.addEventListener(eventName, function () {
        currentPage = 1;
        render();
      });
    });

    render();
  }

  document.querySelectorAll('.ars-sortable-table').forEach(initSortableTable);
})();
