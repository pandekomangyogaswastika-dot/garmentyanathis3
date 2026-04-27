
import React, { useState } from 'react';
import { Search, ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { useSortableTable } from './useSortableTable';

/**
 * DataTable
 *
 * Reusable listing table. Phase 8.4 — adds click-to-sort column headers with
 * localStorage persistence.
 *
 * Props:
 *   columns     : [{ key, label, render?, sortable?, sortValue? }]
 *                 - `sortable` defaults to true unless key === 'actions'.
 *                 - `sortValue(row)` can return the value used for sorting
 *                   when `render` returns JSX that differs from the raw field.
 *   data        : array of row objects
 *   searchKeys  : keys used for the built-in search box
 *   storageKey  : (optional) unique key for persisting sort choice in localStorage.
 *                 When absent, sort state lives only for the component lifetime.
 *   defaultSort : { key, direction } optional initial sort.
 */
export default function DataTable({ columns, data, searchKeys = [], onSearch, actions, exportData, expandedRow, storageKey, defaultSort }) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const getSortValue = (row, key) => {
    const col = columns.find(c => c.key === key);
    if (col && typeof col.sortValue === 'function') {
      try { return col.sortValue(row); } catch (_) { return row[key]; }
    }
    return row ? row[key] : undefined;
  };

  // Sorting is applied BEFORE search/pagination so results are consistent.
  const { sortedData, sortKey, sortDir, toggleSort } = useSortableTable(data || [], {
    storageKey,
    defaultKey: defaultSort?.key || null,
    defaultDir: defaultSort?.direction || 'asc',
    getValue: getSortValue,
  });

  const filtered = search
    ? sortedData.filter(row =>
        searchKeys.some(key =>
          String(row[key] || '').toLowerCase().includes(search.toLowerCase())
        )
      )
    : sortedData;

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  const handleSearch = (val) => {
    setSearch(val);
    setPage(1);
    if (onSearch) onSearch(val);
  };

  const indicatorFor = (key) => {
    if (key === sortKey && sortDir) return sortDir === 'asc' ? '▲' : '▼';
    return '↕';
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      {/* Table Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 border-b border-slate-100">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Cari..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-2">
          {exportData && (
            <button onClick={exportData} className="flex items-center gap-2 px-3 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600">
              <Download className="w-4 h-4" /> Export
            </button>
          )}
          {actions}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              {columns.map((col) => {
                const isSortable = col.sortable !== false && col.key !== 'actions';
                const active = isSortable && sortKey === col.key && !!sortDir;
                return (
                  <th
                    key={col.key}
                    role={isSortable ? 'button' : undefined}
                    aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    data-testid={isSortable ? `sort-header-${col.key}` : undefined}
                    onClick={isSortable ? () => toggleSort(col.key) : undefined}
                    className={`text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap ${isSortable ? 'cursor-pointer select-none hover:bg-slate-100' : ''}`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {isSortable && (
                        <span className={`text-[10px] ${active ? 'text-blue-600' : 'text-slate-300'}`} aria-hidden="true">
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
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-12 text-slate-400 text-sm">
                  Tidak ada data
                </td>
              </tr>
            ) : (
              paginated.map((row, i) => (
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
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
          <span className="text-sm text-slate-500">
            {(page-1)*pageSize+1}–{Math.min(page*pageSize, filtered.length)} dari {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="p-1 rounded disabled:opacity-40 hover:bg-slate-100">
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const p = i + 1;
              return (
                <button key={p} onClick={() => setPage(p)}
                  className={`w-8 h-8 rounded text-sm ${page === p ? 'bg-blue-600 text-white' : 'hover:bg-slate-100 text-slate-600'}`}>
                  {p}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="p-1 rounded disabled:opacity-40 hover:bg-slate-100">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
