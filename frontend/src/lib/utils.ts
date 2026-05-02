export function fmtH(h: number | null | undefined): string {
  if (h == null) return '-';
  const hh = Math.floor(h);
  const mm = Math.round((h - hh) * 60);
  return mm > 0 ? `${hh}h ${mm}m` : `${hh}h`;
}

export function md2html(str: string | undefined): string {
  return (str || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

export function stripLeadingEmoji(str: string | undefined): string {
  return (str || '').replace(/^[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}️\s]+/u, '').trim();
}

export function fmt(s: string | null | undefined): string {
  return s ? s.replace('T', ' ').slice(0, 16) : '-';
}

export function fmtDate(s: string | null | undefined): string {
  return s ? s.slice(0, 10) : '-';
}
