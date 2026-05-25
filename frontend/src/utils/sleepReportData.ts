/** EMTAKE 날짜키 JSON vs API GenerateReportResponse → SleepReport reportData */

const DATE_KEY = /^\d{4}-\d{2}-\d{2}$/;

function fmtDuration(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h${m}m`;
}

function toDateKey(d: string | Date): string {
  if (typeof d === 'string') return d.slice(0, 10);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
}

export function isEmtakeReportData(data: Record<string, unknown>): boolean {
  return Object.keys(data).some(k => DATE_KEY.test(k));
}

/** API 응답 또는 EMTAKE raw JSON을 SleepReport용 reportData로 통일 */
export function toSleepReportData(data: Record<string, unknown> | null | undefined): Record<string, unknown> {
  if (!data || typeof data !== 'object') return {};

  if (isEmtakeReportData(data)) return data;

  const daily = data.daily as Array<Record<string, unknown>> | undefined;
  if (!daily?.length) return {};

  const summary = (data.summary ?? {}) as Record<string, unknown>;
  const breath = (data.breath ?? {}) as Record<string, unknown>;
  const out: Record<string, unknown> = {};

  for (const d of daily) {
    const dateKey = toDateKey((d.date as string) ?? '');
    const sleepMin = (d.sleep_min as number) ?? Math.round(((d.sleep_h as number) ?? 0) * 60);
    const restlessMin = (d.restless_min as number) ?? 0;
    const sessions = (d.sessions as unknown[]) ?? [];

    out[dateKey] = {
      SleepData: {
        day_gs: fmtDuration(sleepMin),
        day_pr: fmtDuration(restlessMin),
        day_wakeup: String(d.wakeup_count ?? 0),
        sessions,
      },
      Breath: {
        Min: breath.breath_min,
        Max: breath.breath_max,
      },
      IndoorTemp: {
        Min: summary.temp_min ?? summary.temp_avg,
        Max: summary.temp_max ?? summary.temp_avg,
      },
      Humidity: {
        Min: summary.humidity_min,
        Max: summary.humidity_max,
      },
    };
  }

  return out;
}

function formatKoreanDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  if (!y || !m || !d) return iso;
  return `${y}년 ${m}월 ${d}일`;
}

function weekEndFromStart(weekStart: string): string {
  const [y, m, d] = weekStart.slice(0, 10).split('-').map(Number);
  const end = new Date(y, m - 1, d + 6);
  return toDateKey(end);
}

export function buildDateRange(
  data: Record<string, unknown> | null | undefined,
  meta?: { weekStart?: string; weekEnd?: string },
): string {
  const weekStart = data?.week_start;
  if (typeof weekStart === 'string' && weekStart.length >= 10) {
    const start = weekStart.slice(0, 10);
    const end = weekEndFromStart(start);
    const [y1, m1, d1] = start.split('-').map(Number);
    const [, , d2] = end.split('-').map(Number);
    return `${y1}년 ${m1}월 ${d1}일 – ${d2}일`;
  }
  if (meta?.weekStart && meta?.weekEnd) {
    return `${meta.weekStart} – ${meta.weekEnd}`;
  }
  const label = data?.week_label;
  if (typeof label === 'string' && label) return label;
  const keys = Object.keys(data ?? {}).filter(k => DATE_KEY.test(k)).sort();
  if (keys.length >= 2) {
    const start = keys[0];
    const end = keys[keys.length - 1];
    const [y1, m1, d1] = start.split('-').map(Number);
    const [, , d2] = end.split('-').map(Number);
    if (start.slice(0, 7) === end.slice(0, 7)) {
      return `${y1}년 ${m1}월 ${d1}일 – ${d2}일`;
    }
    return `${formatKoreanDate(start)} – ${formatKoreanDate(end)}`;
  }
  if (keys.length === 1) return formatKoreanDate(keys[0]);
  return '';
}

type SleepDayInput = {
  sessions?: unknown[] | null;
  wakeup_count?: number | null;
};

/** API 응답에 폼/JSON의 sessions·각성 횟수 병합 (타임라인용) */
export function enrichSleepReportData(
  source: Record<string, unknown> | null | undefined,
  opts?: { weekStart?: string; sleepDays?: SleepDayInput[] },
): Record<string, unknown> {
  const base = toSleepReportData(source);
  if (!opts?.weekStart || !opts?.sleepDays?.length) return base;

  const [wy, wm, wd] = opts.weekStart.split('-').map(Number);
  opts.sleepDays.forEach((entry, i) => {
    const d = new Date(wy, wm - 1, wd + i);
    const key = toDateKey(d);
    const day = base[key] as Record<string, unknown> | undefined;
    if (!day) return;
    const sd = { ...(day.SleepData as Record<string, unknown>) };
    if (entry.sessions?.length) sd.sessions = entry.sessions;
    if (entry.wakeup_count != null) sd.day_wakeup = String(entry.wakeup_count);
    day.SleepData = sd;
    base[key] = day;
  });
  return base;
}
