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
