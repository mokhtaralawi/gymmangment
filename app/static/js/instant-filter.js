/**
 * Instant Live Filter & Arabic Search Engine for "النادي اليمني الصحي"
 * تطوير: يمن كود لتصميم الأنظمة والبرمجيات الحديثة
 * ميزة: مجرد كتابة حرف واحد تظهر النتائج المطابقة فورياً (0ms lag)
 */

(function() {
  'use strict';

  // Normalize Arabic text for superior matching
  function normalizeArabic(text) {
    if (!text) return '';
    return text.toString()
      .trim()
      .toLowerCase()
      // Remove Arabic diacritics / tashkeel
      .replace(/[\u064B-\u065F\u0670]/g, '')
      // Normalize Alef variants
      .replace(/[أإآٱ]/g, 'ا')
      // Normalize Taa Marbuta & Haa
      .replace(/ة/g, 'ه')
      // Normalize Yaa & Alef Maksura
      .replace(/[ىي]/g, 'ي')
      // Normalize Hamza variants
      .replace(/[ؤئ]/g, 'ء')
      // Collapse multiple whitespace
      .replace(/\s+/g, ' ');
  }

  // Filter a standard HTML table
  function filterTable(table, query, columnIdx) {
    if (!table) return;
    const tbody = table.querySelector('tbody') || table;
    const rows = tbody.querySelectorAll('tr:not(.no-filter-results):not(.table-header-row)');
    const normQuery = normalizeArabic(query);
    let matchCount = 0;

    // Remove any previous "no results" message
    const oldNoResults = tbody.querySelector('.no-filter-results');
    if (oldNoResults) oldNoResults.remove();

    rows.forEach(row => {
      // Skip header rows if inside tbody
      if (row.querySelector('th')) return;

      let rowText = '';
      if (columnIdx !== undefined && columnIdx !== null && columnIdx >= 0) {
        const cells = row.querySelectorAll('td');
        if (cells[columnIdx]) {
          rowText = normalizeArabic(cells[columnIdx].textContent);
        }
      } else {
        rowText = normalizeArabic(row.textContent);
      }

      if (normQuery === '' || rowText.includes(normQuery)) {
        row.style.display = '';
        matchCount++;
      } else {
        row.style.display = 'none';
      }
    });

    // If no results, show helpful message
    if (normQuery !== '' && matchCount === 0 && rows.length > 0) {
      const colCount = (table.querySelector('thead tr') ? table.querySelector('thead tr').children.length : 10);
      const emptyRow = document.createElement('tr');
      emptyRow.className = 'no-filter-results';
      emptyRow.innerHTML = `
        <td colspan="${colCount}" style="text-align: center; color: var(--text-muted); padding: 2.5rem 1rem; font-weight: 800;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
          <div style="font-size: 1.05rem; color: var(--text-main); margin-bottom: 0.35rem;">لا توجد نتائج مطابقة لـ "${escapeHtml(query)}"</div>
          <small style="color: var(--text-caption);">جرب البحث بكلمات أخرى أو تحقق من الحروف المدخلة.</small>
        </td>
      `;
      tbody.appendChild(emptyRow);
    }

    return { total: rows.length, matches: matchCount };
  }

  // Filter grid cards (e.g. shifts, payment methods)
  function filterCards(container, query) {
    if (!container) return;
    const cards = container.querySelectorAll('.card:not(.no-filter-cards)');
    const normQuery = normalizeArabic(query);
    let matchCount = 0;

    const oldMsg = container.querySelector('.no-filter-cards');
    if (oldMsg) oldMsg.remove();

    cards.forEach(card => {
      const cardText = normalizeArabic(card.textContent);
      if (normQuery === '' || cardText.includes(normQuery)) {
        card.style.display = '';
        matchCount++;
      } else {
        card.style.display = 'none';
      }
    });

    if (normQuery !== '' && matchCount === 0 && cards.length > 0) {
      const emptyCard = document.createElement('div');
      emptyCard.className = 'card no-filter-cards';
      emptyCard.style.cssText = 'grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 3rem 1rem; font-weight: 800;';
      emptyCard.innerHTML = `
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
        <div style="font-size: 1.05rem; color: var(--text-main); margin-bottom: 0.35rem;">لا توجد عناصر مطابقة لـ "${escapeHtml(query)}"</div>
        <small style="color: var(--text-caption);">تأكد من الحروف أو الكود المدخل.</small>
      `;
      container.appendChild(emptyCard);
    }

    return { total: cards.length, matches: matchCount };
  }

  // Filter hierarchical tree (e.g. chart of accounts)
  function filterTree(treeContainer, query) {
    if (!treeContainer) return;
    const nodes = treeContainer.querySelectorAll('[id^="node-"]');
    const normQuery = normalizeArabic(query);

    if (normQuery === '') {
      // Restore tree default
      treeContainer.querySelectorAll('div').forEach(d => {
        if (d.getAttribute('data-originally-hidden') === 'true') {
          d.style.display = 'none';
        } else {
          d.style.display = '';
        }
      });
      return;
    }

    // Expand nodes and show matches
    treeContainer.querySelectorAll('[id^="node-"]').forEach(node => {
      node.style.display = 'block';
    });

    // Check each account line
    const accountLines = treeContainer.querySelectorAll('div[onclick^="toggleNode"]');
    accountLines.forEach(line => {
      const parentBlock = line.parentElement;
      const text = normalizeArabic(line.textContent);
      if (text.includes(normQuery)) {
        parentBlock.style.display = '';
        line.style.background = 'var(--badge-fire-bg)';
        line.style.borderRadius = '6px';
      } else {
        line.style.background = '';
        // If children have matches, keep block visible
        const childText = normalizeArabic(parentBlock.textContent);
        if (childText.includes(normQuery)) {
          parentBlock.style.display = '';
        } else {
          parentBlock.style.display = 'none';
        }
      }
    });
  }

  function escapeHtml(str) {
    return (str || '').replace(/[&<>"']/g, function(m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }

  // Initialize live filtering on DOMContentLoaded
  function initLiveFilters() {
    // 1. Bind search inputs (name="q" or class="live-search-input" or [data-live-filter])
    const searchInputs = document.querySelectorAll('input[name="q"], input.live-search-input, [data-live-filter]');

    searchInputs.forEach(input => {
      // Find matching table or card container in document
      let targetTable = null;
      let targetCards = null;
      let targetTree = null;

      const targetAttr = input.getAttribute('data-live-filter');
      if (targetAttr) {
        targetTable = document.getElementById(targetAttr) || document.querySelector(targetAttr);
      } else {
        // Find closest table on page
        targetTable = document.querySelector('table');
        // Or grid cards container
        targetCards = document.querySelector('.card-grid, [style*="grid-template-columns"]:not(.form-group)');
        // Or chart of accounts tree
        targetTree = document.querySelector('[style*="font-family: monospace"]');
      }

      // Add visual counter badge if not already present
      let counterBadge = document.getElementById(input.id + '_counter') || input.parentElement.querySelector('.live-filter-counter');
      if (!counterBadge && input.parentElement) {
        counterBadge = document.createElement('span');
        counterBadge.className = 'live-filter-counter';
        counterBadge.style.cssText = 'font-size: 0.75rem; font-weight: 800; color: var(--primary); margin-right: 0.4rem; white-space: nowrap; display: none;';
        input.parentElement.appendChild(counterBadge);
      }

      // Instant input listener (fires on EVERY single character typed or deleted!)
      input.addEventListener('input', function() {
        const val = this.value;

        if (targetTable) {
          const res = filterTable(targetTable, val);
          if (counterBadge && res) {
            if (val.trim() !== '') {
              counterBadge.style.display = 'inline-block';
              counterBadge.textContent = `${res.matches} من ${res.total}`;
            } else {
              counterBadge.style.display = 'none';
            }
          }
        }

        if (targetCards && !targetTable) {
          const res = filterCards(targetCards, val);
          if (counterBadge && res) {
            if (val.trim() !== '') {
              counterBadge.style.display = 'inline-block';
              counterBadge.textContent = `${res.matches} من ${res.total}`;
            } else {
              counterBadge.style.display = 'none';
            }
          }
        }

        if (targetTree) {
          filterTree(targetTree, val);
        }
      });

      // Prevent full page reload on Enter if filtering is handled client-side
      if (input.form) {
        input.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            // If already filtered locally and results are visible, prevent unnecessary reload
            if (targetTable || targetCards || targetTree) {
              e.preventDefault();
            }
          }
        });
      }

      // Trigger immediately on load if input already has initial value
      if (input.value && input.value.trim() !== '') {
        input.dispatchEvent(new Event('input'));
      }
    });

    // 2. Bind dropdown filters (e.g. status, shift, type)
    const selectFilters = document.querySelectorAll('select[name="status"], select[data-live-filter-col]');
    selectFilters.forEach(select => {
      const colIdx = select.getAttribute('data-live-filter-col');
      const table = document.querySelector('table');
      if (table) {
        select.addEventListener('change', function() {
          const val = this.value;
          filterTable(table, val, colIdx !== null ? parseInt(colIdx) : null);
        });
      }
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLiveFilters);
  } else {
    initLiveFilters();
  }

  // Export to window for dynamic use
  window.InstantFilter = {
    filterTable: filterTable,
    filterCards: filterCards,
    filterTree: filterTree,
    normalizeArabic: normalizeArabic,
    reinit: initLiveFilters
  };

})();
