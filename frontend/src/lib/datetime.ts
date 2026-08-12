// The backend (shared/schedules.py) treats schedule strings without timezone
// info as UTC when enforcing deadlines; parse them the same way here so the
// displayed time matches the enforced one.
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }
  const normalized = value.includes(' ') ? value.replace(' ', 'T') : value;
  const withZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(normalized)
    ? normalized
    : `${normalized}Z`;
  const parsed = new Date(withZone);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
