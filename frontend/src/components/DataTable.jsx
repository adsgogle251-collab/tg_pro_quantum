import { useState } from 'react'
import { MdArrowUpward, MdArrowDownward, MdUnfoldMore } from 'react-icons/md'
import theme from '../styles/theme'

/**
 * DataTable — reusable, sortable, paginated table component.
 *
 * Props:
 *   columns  — array of { key, label, render?, sortable?, width? }
 *   rows     — array of data objects
 *   keyField — field name used as React key (default: 'id')
 *   emptyMsg — shown when rows is empty
 *   pageSize — rows per page (0 = no pagination)
 *   onRowClick(row) — optional row click handler
 *   loading  — show skeleton rows
 */
export default function DataTable({
  columns = [],
  rows = [],
  keyField = 'id',
  emptyMsg = 'No data found.',
  pageSize = 0,
  onRowClick,
  loading = false,
}) {
  const [sortKey, setSortKey]   = useState(null)
  const [sortDir, setSortDir]   = useState('asc')
  const [page, setPage]         = useState(1)

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
    setPage(1)
  }

  // Sort
  let sorted = [...rows]
  if (sortKey) {
    sorted.sort((a, b) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv))
      return sortDir === 'asc' ? cmp : -cmp
    })
  }

  // Paginate
  const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1
  const safeP      = Math.min(page, totalPages)
  const visible    = pageSize > 0 ? sorted.slice((safeP - 1) * pageSize, safeP * pageSize) : sorted

  const th = {
    padding: '11px 14px',
    textAlign: 'left',
    fontSize: 12,
    color: theme.textMuted,
    fontWeight: 600,
    letterSpacing: 0.4,
    borderBottom: `1px solid ${theme.bgLight}`,
    whiteSpace: 'nowrap',
    userSelect: 'none',
  }
  const td = {
    padding: '13px 14px',
    fontSize: 13,
    color: theme.text,
    borderBottom: `1px solid ${theme.bgLight}22`,
  }

  const SKELETON_ROWS = pageSize > 0 ? pageSize : 5

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Table wrapper — horizontal scroll on narrow screens */}
      <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 480 }}>
          <thead>
            <tr>
              {columns.map((col) => {
                const isSorted = sortKey === col.key
                return (
                  <th
                    key={col.key}
                    style={{
                      ...th,
                      width: col.width ?? 'auto',
                      cursor: col.sortable ? 'pointer' : 'default',
                    }}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      {col.label}
                      {col.sortable && (
                        isSorted
                          ? sortDir === 'asc'
                            ? <MdArrowUpward size={13} style={{ color: theme.primary }} />
                            : <MdArrowDownward size={13} style={{ color: theme.primary }} />
                          : <MdUnfoldMore size={13} style={{ opacity: 0.4 }} />
                      )}
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: SKELETON_ROWS }).map((_, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col.key} style={td}>
                      <div className="skeleton" style={{ height: 14, borderRadius: 4, width: '70%' }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : visible.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ ...td, textAlign: 'center', color: theme.textMuted, padding: '36px 0' }}
                >
                  {emptyMsg}
                </td>
              </tr>
            ) : (
              visible.map((row, idx) => (
                <tr
                  key={row[keyField] ?? idx}
                  style={{ cursor: onRowClick ? 'pointer' : 'default', transition: 'background 0.15s' }}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  onMouseEnter={(e) => { e.currentTarget.style.background = `${theme.bgLight}55` }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  {columns.map((col) => (
                    <td key={col.key} style={td}>
                      {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageSize > 0 && totalPages > 1 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderTop: `1px solid ${theme.bgLight}`,
          flexWrap: 'wrap',
          gap: 8,
        }}>
          <span style={{ fontSize: 12, color: theme.textMuted }}>
            Page {safeP} of {totalPages} ({sorted.length} total)
          </span>
          <div style={{ display: 'flex', gap: 6 }}>
            {[
              { label: '«', action: () => setPage(1),       disabled: safeP === 1 },
              { label: '‹', action: () => setPage((p) => Math.max(1, p - 1)), disabled: safeP === 1 },
              { label: '›', action: () => setPage((p) => Math.min(totalPages, p + 1)), disabled: safeP === totalPages },
              { label: '»', action: () => setPage(totalPages), disabled: safeP === totalPages },
            ].map(({ label, action, disabled }) => (
              <button
                key={label}
                onClick={action}
                disabled={disabled}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  border: `1px solid ${theme.bgLight}`,
                  background: 'transparent',
                  color: disabled ? theme.textMuted : theme.text,
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  fontSize: 13,
                  opacity: disabled ? 0.4 : 1,
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
