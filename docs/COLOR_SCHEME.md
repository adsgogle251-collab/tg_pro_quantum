# TG PRO QUANTUM — Color Scheme & Design System

## Color Palette

### Primary Colors

| Name | Hex | Usage |
|---|---|---|
| **Quantum Blue** | `#1E90FF` | Primary actions, links, active states |
| **Deep Space** | `#0A0E1A` | Main background |
| **Void Dark** | `#0D1117` | Card / panel background |
| **Nebula Purple** | `#7C3AED` | Accent, highlights, badges |

### Secondary Colors

| Name | Hex | Usage |
|---|---|---|
| **Stellar White** | `#E8EDF5` | Primary text |
| **Muted Grey** | `#8B949E` | Secondary text, placeholders |
| **Surface** | `#161B22` | Input fields, secondary cards |
| **Border** | `#21262D` | Dividers, input borders |

### Semantic Colors

| Name | Hex | Usage |
|---|---|---|
| **Success Green** | `#22C55E` | Active status, success messages |
| **Warning Amber** | `#F59E0B` | Flood wait, caution states |
| **Danger Red** | `#EF4444` | Errors, banned accounts, destructive actions |
| **Info Cyan** | `#06B6D4` | Informational badges, tooltips |

---

## Color Usage Guidelines

- **Backgrounds** always use Deep Space (`#0A0E1A`) or Void Dark (`#0D1117`) — never pure black.
- **Interactive elements** (buttons, links) use Quantum Blue `#1E90FF`; hover state lightens to `#4FACFE`.
- **Destructive actions** (delete, ban) use Danger Red with a confirmation dialog.
- **Status indicators** — always pair color with an icon or text label for accessibility.
- Avoid placing Muted Grey text on Surface backgrounds (contrast ratio < 4.5:1).

---

## Typography

| Role | Font | Size | Weight |
|---|---|---|---|
| Headings | Inter | 24 / 20 / 16 px | 700 |
| Body | Inter | 14 px | 400 |
| Monospace (logs, code) | JetBrains Mono | 13 px | 400 |
| Caption / label | Inter | 12 px | 500 |

---

## Component Styles

### Buttons

| Variant | Background | Text | Border |
|---|---|---|---|
| Primary | `#1E90FF` | `#FFFFFF` | none |
| Secondary | `#21262D` | `#E8EDF5` | `#30363D` |
| Danger | `#EF4444` | `#FFFFFF` | none |
| Ghost | transparent | `#8B949E` | none |

### Status Badges

| Status | Color |
|---|---|
| Active | `#22C55E` |
| Flood Wait | `#F59E0B` |
| Banned | `#EF4444` |
| Disconnected | `#8B949E` |
| Running | `#1E90FF` |

---

## Accessibility Considerations

- All text on dark backgrounds must meet **WCAG AA** contrast (≥ 4.5:1 for normal text).
- Stellar White (`#E8EDF5`) on Deep Space (`#0A0E1A`) achieves a contrast ratio of ~14:1 ✅
- Status indicators must never rely on color alone — always include an icon or text label.
- Interactive elements must have a visible `:focus-visible` outline (2px solid `#1E90FF`).
- Minimum touch target size: **44 × 44 px** for mobile views.
