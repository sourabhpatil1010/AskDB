/**
 * index.ts — Central export barrel for the AskDB formatting system.
 *
 * Import everything from this single entry point:
 *
 *   import { formatNumber, formatCurrency, formatDate } from "@/utils/formatters";
 *
 * ─── Architecture note ───────────────────────────────────────────────────────
 * All formatting functions live in their dedicated module files.
 * This barrel file only re-exports them — it contains zero logic.
 * Adding a new formatter: create a new file, add its export here.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// Number
export {
  EMPTY_DISPLAY,
  formatNumber,
  formatInteger,
  formatDecimal,
  formatCompactNumber,
  smartFormatNumber,
} from "./numberFormatter";

// Currency
export {
  formatCurrency,
  formatCurrencyCompact,
  type SupportedCurrency,
  CURRENCY_LOCALE_MAP,
} from "./currencyFormatter";

// Percentage
export {
  formatPercentage,
  formatPercentageValue,
  formatPercentageRaw,
} from "./percentageFormatter";

// Date / Time
export {
  formatDate,
  formatDateShort,
  formatDateFull,
  formatDateISO,
  formatDateTime,
  formatMs,
} from "./dateFormatter";

// String
export {
  toTitleCase,
  toSentenceCase,
  truncateText,
  withFallback,
  slugify,
  formatColumnLabel,
} from "./stringFormatter";
