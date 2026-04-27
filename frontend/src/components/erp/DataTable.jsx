import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Download, Loader2 } from 'lucide-react';
import { useSortableTable } from './useSortableTable';
import PaginationFooter from './PaginationFooter';

/**
 * DataTable
 *
 * Reusable listing table with two pagination modes:
 *
 *   1. **Client-side mode (default, legacy)**
 *      Pass `data` prop with the full array. The component handles search,
 *      sort, and paging locally (10 rows/page).
 *
 *   2. **Server-side mode (Phase 10C)**
 *      Pass `serverPagination` prop. The component manages page/per_page/sort/search
 *      state internally and calls the provided `fetcher` to retrieve each page.
 *      The `data` prop is ignored in this mode.
 *
 * Server pagination prop shape:
 *   serverPagination = {
 *     fetcher: async ({ page, per_page, sort_by, sort_dir, search }) =>
 *                ({ items, total, page, per_page, total_pages }),
 *     deps: [filterStatus, refetchKey],   // refetch when these change (resets to page 1)
 *     initialPerPage: 20,                 // default 20
 *     initialSort: { key: 'created_at', dir: 'desc' },  // optional default
 *     itemLabel: 'produk',                 // shown in pagination footer
 *     searchDebounceMs: 350,               // default 350ms
 *   }
 *
 * Common props:
 *   columns     : [{ key, label, render?, sortable?, sortValue? }]
 *   data        : array (client-mode only)
 *   searchKeys  : keys used for client-mode search
 *   storageKey  : localStorage key to persist sort
 *   defaultSort : { key, direction } initial sort
 *   actions     : ReactNode rendered in header
 *   exportData  : function to trigger CSV/Excel export (server-mode aware)
 *   expandedRow : (row) => ReactNode | null
 */
export default function DataTable({
  columns,
  data,
  searchKeys = [],
  onSearch,
  actions,
  exportData,
  expandedRow,
  storageKey,
  defaultSort,
  serverPagination,
}) {
  const isServerMode = !!serverPagination?.fetcher;

  // ─── Common state ──────────────────────────────────────────────────────────
  const [search, setSearch] = useState('');

  // ─── Server-mode state ─────────────────────────────────────────────────────
  const initialPerPage = serverPagination?.initialPerPage || 20;
  const [serverPage, setServerPage] = useState(1);
  const [serverPerPage, setServerPerPage] = useState(initialPerPage);
  const [serverItems, setServerItems] = useState([]);
  const [serverTotal, setServerTotal] = useState(0);
  const [serverLoading, setServerLoading] = useState(false);
  const [serverError, setServerError] = useState(null);
  const [serverSort, setServerSort] = useState(() => {
    if (storageKey && typeof window !== 'undefined') {
      try {
        const raw = window.localStorage.getItem(`sort:${storageKey}`);
        if (raw) {
          const p = JSON.parse(raw);
          if (p?.sortKey) return { key: p.sortKey, dir: p.sortDir || 'desc' };
        }
      } catch (_) { /* ignore */ }
    }
    if (serverPagination?.initialSort) return { ...serverPagination.initialSort };
    if (defaultSort) return { key: defaultSort.key, dir: defaultSort.direction || 'desc' };
    return { key: null, dir: null };
  });
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Debounce the search box for server mode
  useEffect(() => {
    if (!isServerMode) return undefined;
    const wait = serverPagination?.searchDebounceMs ?? 350;
    const t = setTimeout(() => setDebouncedSearch(search), wait);
    return () => clearTimeout(t);
  }, [search, isServerMode, serverPagination?.searchDebounceMs]);

  // Persist server-mode sort to localStorage (parity with client-mode)
  useEffect(() => {
    if (!isServerMode || !storageKey) return;
    try {
      window.localStorage.setItem(
        `sort:${storageKey}`,
        JSON.stringify({ sortKey: serverSort.key, sortDir: serverSort.dir })
      );
    } catch (_) { /* ignore */ }
  }, [isServerMode, storageKey, serverSort.key, serverSort.dir]);

  // Reset to page 1 whenever caller deps, search, sort, or per-page changes
  const deps = serverPagination?.deps || [];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!isServerMode) return;
    setServerPage(1);
    // deps spread is intentional
  }, [isServerMode, debouncedSearch, serverSort.key, serverSort.dir, serverPerPage, ...deps]);

  // Track latest fetch to avoid race conditions
  const fetchSeqRef = useRef(0);

  const runFetch = useCallback(async () => {
    if (!isServerMode) return;
    const seq = ++fetchSeqRef.current;
    setServerLoading(true);
    setServerError(null);
    try {
      const env = await serverPagination.fetcher({
        page: serverPage,
        per_page: serverPerPage,
        sort_by: serverSort.key || undefined,
        sort_dir: serverSort.dir || undefined,
        search: debouncedSearch || undefined,
      });
      // Stale response — drop
      if (seq !== fetchSeqRef.current) return;
      // Defensive: backend may legacy-return an array for pre-paginated endpoints
      if (Array.isArray(env)) {
        setServerItems(env);
        setServerTotal(env.length);
      } else if (env && typeof env === 'object') {
        setServerItems(Array.isArray(env.items) ? env.items : []);
        setServerTotal(typeof env.total === 'number' ? env.total : 0);
      } else {
        setServerItems([]);
        setServerTotal(0);
      }
    } catch (err) {
      if (seq !== fetchSeqRef.current) return;
      setServerError(err?.message || 'Gagal memuat data');
      setServerItems([]);
      setServerTotal(0);
    } finally {
      if (seq === fetchSeqRef.current) setServerLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isServerMode, serverPagination, serverPage, serverPerPage, serverSort.key, serverSort.dir, debouncedSearch, ...deps]);

  useEffect(() => {
    if (!isServerMode) return;
    runFetch();
  }, [runFetch, isServerMode]);

  // ─── Client-mode setup ─────────────────────────────────────────────────────
  const [clientPage, setClientPage] = useState(1);
  const clientPageSize = 10;

  const getSortValue = (row, key) => {
    const col = columns.find((c) => c.key === key);
    if (col && typeof col.sortValue === 'function') {
      try {
        return col.sortValue(row);
      } catch (_) {
        return row[key];
      }
    }
    return row ? row[key] : undefined;
  };

  // Sorting hook only used for client-mode; server-mode bypasses it
  const { sortedData, sortKey: clientSortKey, sortDir: clientSortDir, toggleSort: clientToggleSort } = useSortableTable(
    isServerMode ? [] : data || [],
    {
      storageKey: isServerMode ? null : storageKey,
      defaultKey: defaultSort?.key || null,
      defaultDir: defaultSort?.direction || 'asc',
      getValue: getSortValue,
    }
  );

  // ─── Sort indicator + toggle (mode-aware) ─────────────────────────────────
  const activeSortKey = isServerMode ? serverSort.key : clientSortKey;
  const activeSortDir = isServerMode ? serverSort.dir : clientSortDir;

  const toggleSort = (key) => {
    if (isServerMode) {
      setServerSort((prev) => {
        if (prev.key !== key) return { key, dir: 'asc' };
        if (prev.dir === 'asc') return { key, dir: 'desc' };
        if (prev.dir === 'desc') return { key: null, dir: null };
        return { key, dir: 'asc' };
      });
    } else {
      clientToggleSort(key);
    }
  };

  const indicatorFor = (key) => {
    if (key === activeSortKey && activeSortDir) return activeSortDir === 'asc' ? '▲' : '▼';
    return '↕';
  };

  // ─── Client-mode filter/paginate ──────────────────────────────────────────
  const clientFiltered = !isServerMode && search
    ? sortedData.filter((row) =>
        searchKeys.some((key) =>
          String(row[key] || '').toLowerCase().includes(search.toLowerCase())
        )
      )
    : sortedData;
  const clientTotalPages = Math.ceil((clientFiltered?.length || 0) / clientPageSize);
  const clientPaginated = !isServerMode
    ? (clientFiltered || []).slice((clientPage - 1) * clientPageSize, clientPage * clientPageSize)
    : [];

  const handleSearch = (val) => {
    setSearch(val);
    if (!isServerMode) setClientPage(1);
    if (onSearch) onSearch(val);
  };

  // ─── Render data choice ────────────────────────────────────────────────────
  const renderRows = isServerMode ? serverItems : clientPaginated;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 border-b border-slate-100">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Cari..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="datatable-search-input"
          />
          {isServerMode && serverLoading && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 text-blue-500 w-4 h-4 animate-spin" />
          )}
        </div>
        <div className="flex items-center gap-2">
          {exportData && (
            <button
              onClick={exportData}
              className="flex items-center gap-2 px-3 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600"
              data-testid="datatable-export-btn"
            >
              <Download className="w-4 h-4" /> Export
            </button>
          )}
          {actions}
        </div>
      </div>

      {/* Server-mode error banner */}
      {isServerMode && serverError && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-sm text-red-700" data-testid="datatable-error">
          ⚠️ {serverError}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              {columns.map((col) => {
                const isSortable = col.sortable !== false && col.key !== 'actions';
                const active = isSortable && activeSortKey === col.key && !!activeSortDir;
                return (
                  <th
                    key={col.key}
                    role={isSortable ? 'button' : undefined}
                    aria-sort={active ? (activeSortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    data-testid={isSortable ? `sort-header-${col.key}` : undefined}
                    onClick={isSortable ? () => toggleSort(col.key) : undefined}
                    className={`text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap ${
                      isSortable ? 'cursor-pointer select-none hover:bg-slate-100' : ''
                    }`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {isSortable && (
                        <span
                          className={`text-[10px] ${active ? 'text-blue-600' : 'text-slate-300'}`}
                          aria-hidden="true"
                        >
                          {indicatorFor(col.key)}
                        </span>
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isServerMode && serverLoading && renderRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-12 text-slate-400 text-sm">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-500" />
                  Memuat data...
                </td>
              </tr>
            ) : renderRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-12 text-slate-400 text-sm">
                  Tidak ada data
                </td>
              </tr>
            ) : (
              renderRows.map((row, i) => (
                <React.Fragment key={row.id || i}>
                  <tr className="hover:bg-slate-50 transition-colors">
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3 text-sm text-slate-700">
                        {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '-')}
                      </td>
                    ))}
                  </tr>
                  {expandedRow && expandedRow(row) && (
                    <tr>
                      <td colSpan={columns.length} className="p-0 border-b border-slate-100">
                        {expandedRow(row)}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {isServerMode ? (
        <PaginationFooter
          page={serverPage}
          perPage={serverPerPage}
          total={serverTotal}
          onPageChange={setServerPage}
          onPerPageChange={setServerPerPage}
          loading={serverLoading}
          itemLabel={serverPagination?.itemLabel || 'baris'}
          testIdPrefix="datatable-pagination"
        />
      ) : (
        clientTotalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
            <span className="text-sm text-slate-500">
              {(clientPage - 1) * clientPageSize + 1}–{Math.min(clientPage * clientPageSize, clientFiltered.length)} dari {clientFiltered.length}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setClientPage((p) => Math.max(1, p - 1))}
                disabled={clientPage === 1}
                className="p-1 rounded disabled:opacity-40 hover:bg-slate-100"
              >
                ‹
              </button>
              {Array.from({ length: Math.min(5, clientTotalPages) }, (_, i) => {
                const p = i + 1;
                return (
                  <button
                    key={p}
                    onClick={() => setClientPage(p)}
                    className={`w-8 h-8 rounded text-sm ${
                      clientPage === p ? 'bg-blue-600 text-white' : 'hover:bg-slate-100 text-slate-600'
                    }`}
                  >
                    {p}
                  </button>
                );
              })}
              <button
                onClick={() => setClientPage((p) => Math.min(clientTotalPages, p + 1))}
                disabled={clientPage === clientTotalPages}
                className="p-1 rounded disabled:opacity-40 hover:bg-slate-100"
              >
                ›
              </button>
            </div>
          </div>
        )
      )}
    </div>
  );
}
