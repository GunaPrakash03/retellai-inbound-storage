// SQLite hands back "YYYY-MM-DD HH:MM:SS" in UTC with no timezone marker —
// normalise it before parsing or the browser reads it as local time.
function parseUtc(isoish) {
  return new Date(isoish.replace(" ", "T") + "Z").getTime();
}

export function timeAgo(isoString) {
  if (!isoString) return "—";
  const diffMin = Math.round((Date.now() - parseUtc(isoString)) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}d ago`;
}

export function daysSince(isoString) {
  if (!isoString) return null;
  return Math.floor((Date.now() - parseUtc(isoString)) / 86400000);
}

// --- hearing dates -------------------------------------------------------
// These are plain YYYY-MM-DD calendar dates typed by staff, not timestamps.
// Comparing them as instants would make a hearing flip to "tomorrow" for
// anyone east of UTC, so both sides are reduced to a local calendar day first.

function localMidnight(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/** Whole days from today to a YYYY-MM-DD date. 0 = today, negative = past.
 *  Returns null for anything that isn't a calendar date, so a value typed in
 *  the wrong format shows as-is rather than as a nonsense countdown. */
export function daysUntil(dateString) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((dateString || "").trim());
  if (!m) return null;
  const then = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(then.getTime())) return null;
  return Math.round((localMidnight(then) - localMidnight(new Date())) / 86400000);
}

/** "11 Aug 2026", or the raw string back if it isn't a calendar date. */
export function formatHearingDate(dateString) {
  const raw = (dateString || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw || "—";
  const [y, mo, d] = raw.split("-").map(Number);
  return new Date(y, mo - 1, d).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** "today", "in 8 d", "3 d ago" — null when the date can't be read. */
export function hearingCountdown(dateString) {
  const n = daysUntil(dateString);
  if (n === null) return null;
  if (n === 0) return "today";
  if (n === 1) return "tomorrow";
  if (n > 0) return `in ${n} d`;
  return `${Math.abs(n)} d ago`;
}
