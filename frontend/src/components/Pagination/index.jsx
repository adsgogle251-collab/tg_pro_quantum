const PAGE_SIZES = [10, 20, 50, 100]

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  onPageSizeChange,
  totalItems,
}) {
  if (totalPages <= 0) return null

  // Build visible page numbers (max 5)
  const getPages = () => {
    if (totalPages <= 5) return Array.from({ length: totalPages }, (_, i) => i + 1)
    let start = Math.max(1, currentPage - 2)
    let end = start + 4
    if (end > totalPages) {
      end = totalPages
      start = Math.max(1, end - 4)
    }
    return Array.from({ length: end - start + 1 }, (_, i) => start + i)
  }

  const pages = getPages()

  const btnBase = {
    minWidth: 34,
    height: 34,
    borderRadius: 7,
    border: '1px solid #252D4A',
    background: 'transparent',
    color: '#9099B7',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 8px',
    transition: 'all 0.15s',
  }

  const activeBtn = {
    ...btnBase,
    background: '#00D9FF',
    border: '1px solid #00D9FF',
    color: '#0A0E27',
    fontWeight: 700,
  }

  const disabledBtn = {
    ...btnBase,
    opacity: 0.35,
    cursor: 'not-allowed',
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        padding: '14px 0 4px',
      }}
    >
      {/* Page size + info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {onPageSizeChange && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, color: '#9099B7' }}>Rows per page</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              style={{
                background: '#252D4A',
                border: '1px solid #252D4A',
                borderRadius: 6,
                color: '#E0E0FF',
                fontSize: 13,
                padding: '4px 8px',
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              {PAGE_SIZES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        )}
        {totalItems != null && (
          <span style={{ fontSize: 13, color: '#9099B7' }}>
            {totalItems} total
          </span>
        )}
      </div>

      {/* Page buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {/* First */}
        {currentPage > 1 && (
          <button style={btnBase} onClick={() => onPageChange(1)} title="First page">«</button>
        )}

        {/* Previous */}
        <button
          style={currentPage <= 1 ? disabledBtn : btnBase}
          onClick={() => currentPage > 1 && onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          title="Previous page"
        >
          ‹
        </button>

        {/* Page numbers */}
        {pages[0] > 1 && (
          <span style={{ color: '#9099B7', padding: '0 4px', fontSize: 13 }}>…</span>
        )}
        {pages.map((p) => (
          <button
            key={p}
            style={p === currentPage ? activeBtn : btnBase}
            onClick={() => onPageChange(p)}
            onMouseEnter={(e) => { if (p !== currentPage) { e.currentTarget.style.borderColor = '#00D9FF44'; e.currentTarget.style.color = '#E0E0FF' } }}
            onMouseLeave={(e) => { if (p !== currentPage) { e.currentTarget.style.borderColor = '#252D4A'; e.currentTarget.style.color = '#9099B7' } }}
          >
            {p}
          </button>
        ))}
        {pages[pages.length - 1] < totalPages && (
          <span style={{ color: '#9099B7', padding: '0 4px', fontSize: 13 }}>…</span>
        )}

        {/* Next */}
        <button
          style={currentPage >= totalPages ? disabledBtn : btnBase}
          onClick={() => currentPage < totalPages && onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          title="Next page"
        >
          ›
        </button>

        {/* Last */}
        {currentPage < totalPages && (
          <button style={btnBase} onClick={() => onPageChange(totalPages)} title="Last page">»</button>
        )}
      </div>
    </div>
  )
}
