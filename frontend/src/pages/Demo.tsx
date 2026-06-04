import React, { useState, useRef, useMemo, useEffect } from 'react';
import ReportSplitLayout from '../components/ReportSplitLayout';
import { downloadPdf } from '../utils/downloadPdf';
import { enrichSleepReportData, buildDateRange, isEmtakeReportData } from '../utils/sleepReportData';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';
const DEFAULT_API_KEY = (import.meta.env.VITE_API_KEY as string | undefined) ?? 'dev-local-key';

const parseDuration = (s: string): number => {
  if (!s) return 0;
  const h = parseInt(s.match(/(\d+)h/)?.[1] ?? '0');
  const m = parseInt(s.match(/(\d+)m/)?.[1] ?? '0');
  return h * 60 + m;
};

const calcAgeMonths = (birthDateStr: string): number => {
  if (!birthDateStr) return 0;
  const birth = new Date(birthDateStr);
  const today = new Date();
  return (today.getFullYear() - birth.getFullYear()) * 12 + (today.getMonth() - birth.getMonth());
};

const toDateStr = (d: Date): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const getThisMonday = (): string => {
  const today = new Date();
  const day = today.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(today);
  monday.setDate(today.getDate() + diff);
  return toDateStr(monday);
};

type SleepEntry = {
  sleep_min: number;
  restless_min: number;
  wakeup_count: number | null;
  device_status: string | null;
  sessions: any[] | null;
  env_temp_max?: number | null;
  env_db_max?: number | null;
  env_humidity_avg?: number | null;
  env_bright_avg?: number | null;
};

// 초기 목 데이터 — 8개월 아기(민우) 기준 / 수요일(i=2) 온도 25.3°C로 ⚠ 트리거 테스트
const MOCK_SLEEP: SleepEntry[] = [
  { sleep_min: 620, restless_min: 25, wakeup_count: 2, device_status: 'NORMAL', sessions: null, env_temp_max: 22.1, env_db_max: 48, env_humidity_avg: 52.0, env_bright_avg: 1.2 },
  { sleep_min: 580, restless_min: 30, wakeup_count: 3, device_status: 'NORMAL', sessions: null, env_temp_max: 22.8, env_db_max: 51, env_humidity_avg: 53.0, env_bright_avg: 1.5 },
  { sleep_min: 510, restless_min: 52, wakeup_count: 5, device_status: 'CAUTION', sessions: null, env_temp_max: 25.3, env_db_max: 49, env_humidity_avg: 54.0, env_bright_avg: 1.8 },
  { sleep_min: 600, restless_min: 20, wakeup_count: 2, device_status: 'NORMAL', sessions: null, env_temp_max: 21.9, env_db_max: 47, env_humidity_avg: 51.0, env_bright_avg: 1.3 },
  { sleep_min: 590, restless_min: 35, wakeup_count: 3, device_status: 'NORMAL', sessions: null, env_temp_max: 22.5, env_db_max: 50, env_humidity_avg: 52.5, env_bright_avg: 1.4 },
  { sleep_min: 540, restless_min: 42, wakeup_count: 4, device_status: 'NORMAL', sessions: null, env_temp_max: 23.8, env_db_max: 55, env_humidity_avg: 50.0, env_bright_avg: 1.6 },
  { sleep_min: 610, restless_min: 22, wakeup_count: 2, device_status: 'NORMAL', sessions: null, env_temp_max: 22.2, env_db_max: 48, env_humidity_avg: 53.0, env_bright_avg: 1.2 },
];

const Demo: React.FC = () => {
  const [reportData, setReportData] = useState<any>(null);
  const [rawJsonData, setRawJsonData] = useState<Record<string, unknown> | null>(null);
  const [reportMeta, setReportMeta] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<'mobile' | 'pc'>('mobile');

  const captureRef = useRef<HTMLDivElement>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const [serNo, setSerNo] = useState('MT-00001');
  const [babyName, setBabyName] = useState('민우');
  const [ageMonths, setAgeMonths] = useState(8);
  const [weekStart, setWeekStart] = useState(getThisMonday());
  const [sleepData, setSleepData] = useState(MOCK_SLEEP.map(s => ({ ...s })));

  const [env, setEnv] = useState<{
    tempAvg: number; tempMax: number; tempMin: number; dbMax: number;
    humMin: number | null; humMax: number | null; humAvg: number | null;
    brightMin: number | null; brightMax: number | null; brightAvg: number | null;
  }>({ tempAvg: 23.2, tempMax: 24.5, tempMin: 21.8, dbMax: 52, humMin: 45, humMax: 58, humAvg: 51.5, brightMin: 0.2, brightMax: 3.5, brightAvg: 1.85 });

  const [breath, setBreath] = useState({ min: 32, avg: 40, max: 52 });
  const [bodyTemp, setBodyTemp] = useState({ min: -0.3, avg: 0.2, max: 0.6 });
  const [events, setEvents] = useState({
    monthSleep: 14.5, monthRestless: 0.55,
    weekSleep: 13.8 as number | null, weekRestless: 0.5 as number | null,
    cryCount: 4, leaveCount: 1,
  });

  // URL ?report=<base64> 파라미터로 리포트 데이터 주입 (백엔드 PDF 캡처용)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const encoded = params.get('report');
    const mode = params.get('mode') as 'mobile' | 'pc' | null;
    if (encoded) {
      try {
        const json = JSON.parse(atob(encoded));
        setRawJsonData(json);
        setReportData(json);
        if (mode) setViewMode(mode);
      } catch {}
    }
  }, []);

  const displayReportData = useMemo(
    () => enrichSleepReportData(rawJsonData ?? reportData, { weekStart, sleepDays: sleepData }),
    [reportData, rawJsonData, weekStart, sleepData],
  );

  const sleepReportPayload = useMemo(
    () => (rawJsonData ?? (isEmtakeReportData(reportData ?? {}) ? reportData : displayReportData)) as Record<string, unknown>,
    [rawJsonData, reportData, displayReportData],
  );

  const hasSleepReport = Object.keys(sleepReportPayload).some(k => /^\d{4}-\d{2}-\d{2}$/.test(k));

  const sleepChildName = (() => {
    const name = reportMeta?.name || babyName || '아기';
    const title = reportMeta?.gender === 'M' ? ' 왕자님' : reportMeta?.gender === 'F' ? ' 공주님' : '';
    return `${name}${title}`;
  })();
  const sleepDateRange = buildDateRange(rawJsonData ?? reportData, reportMeta);
  const apiReportForGuidelines =
    reportData && !isEmtakeReportData(reportData) ? reportData : null;

  const handleDownloadPdf = async () => {
    const el = captureRef.current;
    if (!el) return;
    setPdfLoading(true);
    try {
      const label = (reportData?.week_label ?? `${babyName}_${weekStart}`).replace(/\s/g, '_');
      await downloadPdf(el, label);
    } finally {
      setPdfLoading(false);
    }
  };

  const buildRequest = () => {
    const [wy, wm, wd] = weekStart.split('-').map(Number);
    const sleep = sleepData.map((s, i) => {
      const d = new Date(wy, wm - 1, wd + i);
      const dateStr = toDateStr(d);
      const entry: any = { date: dateStr, sleep_min: s.sleep_min, restless_min: s.restless_min };
      if (s.wakeup_count != null) entry.wakeup_count = s.wakeup_count;
      if (s.device_status) entry.device_status = s.device_status;
      if (s.sessions) entry.sessions = s.sessions;
      if (s.env_temp_max != null) entry.env_temp_max = s.env_temp_max;
      if (s.env_db_max != null) entry.env_db_max = s.env_db_max;
      if (s.env_humidity_avg != null) entry.env_humidity_avg = s.env_humidity_avg;
      if (s.env_bright_avg != null) entry.env_bright_avg = s.env_bright_avg;
      return entry;
    });
    const environment: any = { temp_avg: env.tempAvg, temp_max: env.tempMax, temp_min: env.tempMin, db_max: env.dbMax, db_avg: env.dbMax };
    if (env.humAvg != null) { environment.humidity_min = env.humMin; environment.humidity_max = env.humMax; environment.humidity_avg = env.humAvg; }
    if (env.brightAvg != null) { environment.bright_min = env.brightMin; environment.bright_max = env.brightMax; environment.bright_avg = env.brightAvg; }
    const monthly: any = { month_sleep_h: events.monthSleep, month_restless_h: events.monthRestless };
    if (events.weekSleep != null) { monthly.week_sleep_h = events.weekSleep; monthly.week_restless_h = events.weekRestless; }
    return {
      ser_no: serNo.trim() || `DEMO-${ageMonths}m`,
      baby_age_months: ageMonths,
      week_start: weekStart,
      sleep,
      environment,
      breath: { breath_min: breath.min, breath_max: breath.max, breath_avg: breath.avg },
      body_temp: { body_temp_min: bodyTemp.min, body_temp_max: bodyTemp.max, body_temp_avg: bodyTemp.avg },
      monthly,
      events: { cry_count: events.cryCount, leave_count: events.leaveCount },
    };
  };

  const buildMeta = (req: any, res?: any) => {
    const [wy, wm, wd] = req.week_start.split('-').map(Number);
    const ws = new Date(wy, wm - 1, wd);
    const we = new Date(wy, wm - 1, wd + 6);
    const fmt = (d: Date) => `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
    return {
      name: res?.baby_name || babyName || undefined,
      gender: res?.baby_gender || undefined,
      ageMonths: req.baby_age_months,
      weekNum: Math.floor((ws.getDate() - 1) / 7) + 1,
      weekStart: fmt(ws),
      weekEnd: fmt(we),
      generated: fmt(new Date()),
    };
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setReportData(null);
    setRawJsonData(null);
    try {
      const req = buildRequest();
      const response = await fetch(`${BASE_URL}/api/v1/reports/generate?force=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': DEFAULT_API_KEY },
        body: JSON.stringify(req),
      });
      if (!response.ok) throw new Error(`서버 오류 ${response.status}: ${await response.text()}`);
      const result = await response.json();
      setReportData(result);
      setReportMeta(buildMeta(req, result));
    } catch (err: any) {
      setError(`API 호출 실패: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const applyJsonData = (json: any) => {
    const dateKeys = Object.keys(json).filter(k => /^\d{4}-\d{2}-\d{2}$/.test(k)).sort();
    if (dateKeys.length === 0) { setError('날짜 데이터를 찾을 수 없습니다.'); return; }
    setRawJsonData(json);

    const last = dateKeys[dateKeys.length - 1];
    const [ly, lm, ld] = last.split('-').map(Number);
    const lastDate = new Date(ly, lm - 1, ld);
    lastDate.setDate(lastDate.getDate() - 6);
    const weekStartStr = toDateStr(lastDate);
    setWeekStart(weekStartStr);
    setAgeMonths(calcAgeMonths(json.birth_date || ''));
    const classifySessions = (sessions: any[]): any[] =>
      sessions.map(s => ({ ...s, is_nap: parseInt(s.start?.split(':')[0] ?? '0') < 21 }));

    const parseWakeupCount = (s: string): number | null => {
      const m = s?.match(/\d+/);
      return m ? parseInt(m[0]) : null;
    };

    const [wy, wm, wd] = weekStartStr.split('-').map(Number);
    const newSleepData = Array.from({ length: 7 }, (_, i) => {
      const date = new Date(wy, wm - 1, wd + i);
      const key = toDateStr(date);
      const sd = json[key]?.SleepData ?? {};
      return {
        sleep_min: parseDuration(sd.day_gs ?? ''),
        restless_min: parseDuration(sd.day_pr ?? ''),
        wakeup_count: parseWakeupCount(sd.day_wakeup ?? ''),
        device_status: sd.status ?? null,
        sessions: sd.sessions ? classifySessions(sd.sessions) : null,
      };
    });
    setSleepData(newSleepData);

    const breathData = dateKeys.map(k => json[k]?.Breath ?? {});
    const bMinAvg = Math.round(breathData.reduce((s, b) => s + (b.Min ?? 0), 0) / breathData.length);
    const bMaxAvg = Math.round(breathData.reduce((s, b) => s + (b.Max ?? 0), 0) / breathData.length);
    setBreath({ min: bMinAvg, avg: Math.round((bMinAvg + bMaxAvg) / 2), max: bMaxAvg });

    const tempData = dateKeys.map(k => json[k]?.Temp ?? {});
    const tMinAvg = Math.round(tempData.reduce((s, t) => s + (t.Min ?? 0), 0) / tempData.length * 100) / 100;
    const tMaxAvg = Math.round(tempData.reduce((s, t) => s + (t.Max ?? 0), 0) / tempData.length * 100) / 100;
    setBodyTemp({ min: tMinAvg, avg: Math.round((tMinAvg + tMaxAvg) / 2 * 100) / 100, max: tMaxAvg });

    const itData = dateKeys.map(k => json[k]?.IndoorTemp ?? {});
    const itMinAvg = Math.round(itData.reduce((s, t) => s + (t.Min ?? 0), 0) / itData.length * 10) / 10;
    const itMaxAvg = Math.round(itData.reduce((s, t) => s + (t.Max ?? 0), 0) / itData.length * 10) / 10;
    const dbMaxVal = Math.max(...dateKeys.map(k => json[k]?.dB?.Max ?? 0));

    const humDays = dateKeys.filter(k => json[k]?.Humidity);
    let humMin: number | null = null, humMax: number | null = null, humAvg: number | null = null;
    if (humDays.length > 0) {
      humMin = Math.round(humDays.reduce((s, k) => s + (json[k].Humidity.Min ?? 0), 0) / humDays.length * 10) / 10;
      humMax = Math.round(humDays.reduce((s, k) => s + (json[k].Humidity.Max ?? 0), 0) / humDays.length * 10) / 10;
      humAvg = Math.round((humMin + humMax) / 2 * 10) / 10;
    }

    const brtDays = dateKeys.filter(k => json[k]?.Bright);
    let brightMin: number | null = null, brightMax: number | null = null, brightAvg: number | null = null;
    if (brtDays.length > 0) {
      brightMin = Math.round(brtDays.reduce((s, k) => s + (json[k].Bright.Min ?? 0), 0) / brtDays.length * 10) / 10;
      brightMax = Math.round(brtDays.reduce((s, k) => s + (json[k].Bright.Max ?? 0), 0) / brtDays.length * 10) / 10;
      brightAvg = Math.round((brightMin + brightMax) / 2 * 10) / 10;
    }

    setEnv({ tempAvg: Math.round((itMinAvg + itMaxAvg) / 2 * 10) / 10, tempMax: itMaxAvg, tempMin: itMinAvg, dbMax: dbMaxVal, humMin, humMax, humAvg, brightMin, brightMax, brightAvg });

    const lastSd = json[dateKeys[dateKeys.length - 1]]?.SleepData ?? {};
    const weekSleepH = lastSd.week_gs ? Math.round(parseDuration(lastSd.week_gs) / 60 * 100) / 100 : null;
    const weekRestlessH = lastSd.week_pr ? Math.round(parseDuration(lastSd.week_pr) / 60 * 100) / 100 : null;
    setEvents({
      monthSleep: Math.round(parseDuration(lastSd.month_gs ?? '') / 60 * 100) / 100,
      monthRestless: Math.round(parseDuration(lastSd.month_pr ?? '') / 60 * 100) / 100,
      weekSleep: weekSleepH,
      weekRestless: weekRestlessH,
      cryCount: 0,
      leaveCount: 0,
    });
    setError('');

    const ws = new Date(wy, wm - 1, wd);
    const we = new Date(wy, wm - 1, wd + 6);
    setReportData(json);
    setReportMeta({
      name: babyName,
      weekStart: `${ws.getFullYear()}년 ${ws.getMonth() + 1}월 ${ws.getDate()}일`,
      weekEnd: `${we.getDate()}일`,
    });
  };

  const handleLoadJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = evt => {
      try { applyJsonData(JSON.parse(evt.target?.result as string)); }
      catch { setError('JSON 파일 파싱 실패'); }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleSleepChange = (index: number, field: 'sleep_min' | 'restless_min', value: number) => {
    const newData = [...sleepData];
    newData[index] = { ...newData[index], [field]: value };
    setSleepData(newData);
  };

  const DAY_KO = ['일', '월', '화', '수', '목', '금', '토'];
  const getDayLabel = (i: number) => {
    const [wy, wm, wd] = weekStart.split('-').map(Number);
    return DAY_KO[new Date(wy, wm - 1, wd + i).getDay()];
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--surface)' }}>
      <div className="no-print" style={{ background: 'var(--black)', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#fff', fontFamily: 'Inter, sans-serif', letterSpacing: 1, textTransform: 'uppercase' }}>🌙 Mom-i AI Report Test</h1>
        <a href="/admin.html" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontWeight: 500, fontSize: '13px' }}>← Admin Home</a>
      </div>

      <div style={{ display: 'flex', flex: 1, padding: '24px', gap: '24px', overflow: 'hidden' }}>
        {/* 왼쪽 컨트롤 패널 */}
        <div className="no-print" style={{ width: '360px', display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', paddingRight: '8px', flexShrink: 0 }}>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>📂 릴레이 JSON 불러오기</div>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '10px', background: 'var(--surface)', border: '1px dashed var(--gray-lt)', borderRadius: '8px', cursor: 'pointer', fontSize: '12px', color: 'var(--gray-dark)', fontWeight: 600 }}>
              JSON 파일 선택 (릴레이 SensorData 형식)
              <input type="file" accept=".json" style={{ display: 'none' }} onChange={handleLoadJson} />
            </label>
          </div>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>👶 기본 정보</div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>아이 이름</label>
            <input className="input-field" value={babyName} onChange={e => setBabyName(e.target.value)} placeholder="예: 은우" style={{ marginBottom: '10px' }} />
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>시리얼 번호 (비우면 DEMO-[월령]m 자동 입력)</label>
            <input className="input-field" value={serNo} onChange={e => setSerNo(e.target.value)} placeholder="예: MT-00123" style={{ marginBottom: '10px' }} />
            <div style={{ display: 'flex', gap: '10px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>월령 (개월)</label>
                <input className="input-field" type="number" value={ageMonths} onChange={e => setAgeMonths(Number(e.target.value))} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>주 시작일</label>
                <input className="input-field" type="date" value={weekStart} onChange={e => setWeekStart(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>😴 수면 데이터 (7일)</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr>
                  {['요일', '수면 (분)', '뒤척임 (분)'].map(h => (
                    <th key={h} style={{ padding: '5px 3px', fontSize: '10px', fontWeight: 700, color: 'var(--gray-mut)', textAlign: 'center', borderBottom: '1px solid var(--black)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sleepData.map((d, i) => (
                  <tr key={i}>
                    <td style={{ padding: '4px', textAlign: 'center', fontWeight: 700, color: 'var(--black)', borderBottom: '1px solid var(--gray-lt)' }}>{getDayLabel(i)}</td>
                    <td style={{ padding: '4px', borderBottom: '1px solid var(--gray-lt)' }}>
                      <input type="number" className="input-field" style={{ padding: '5px', textAlign: 'center' }} value={d.sleep_min} onChange={e => handleSleepChange(i, 'sleep_min', Number(e.target.value))} />
                    </td>
                    <td style={{ padding: '4px', borderBottom: '1px solid var(--gray-lt)' }}>
                      <input type="number" className="input-field" style={{ padding: '5px', textAlign: 'center' }} value={d.restless_min} onChange={e => handleSleepChange(i, 'restless_min', Number(e.target.value))} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>🌡️ 수면 환경</div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>온도 (평균 / 최고 / 최저)</label>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              {(['tempAvg', 'tempMax', 'tempMin'] as const).map(k => (
                <input key={k} className="input-field" type="number" step="0.1" value={env[k]} onChange={e => setEnv({ ...env, [k]: Number(e.target.value) })} />
              ))}
            </div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>소음 최고 (dB) — 릴레이는 Max만 제공</label>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              <input className="input-field" type="number" value={env.dbMax} onChange={e => setEnv({ ...env, dbMax: Number(e.target.value) })} />
            </div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>습도 (최저 / 최고) — 없으면 비워두기</label>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              {(['humMin', 'humMax'] as const).map(k => (
                <input key={k} className="input-field" type="number" step="0.1" placeholder="—"
                  value={env[k] ?? ''} onChange={e => {
                    const val = e.target.value === '' ? null : Number(e.target.value);
                    const next = { ...env, [k]: val };
                    next.humAvg = next.humMin != null && next.humMax != null ? Math.round((next.humMin + next.humMax) / 2 * 10) / 10 : null;
                    setEnv(next);
                  }} />
              ))}
            </div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>조도 (lux, 최저 / 최고) — 없으면 비워두기</label>
            <div style={{ display: 'flex', gap: '6px' }}>
              {(['brightMin', 'brightMax'] as const).map(k => (
                <input key={k} className="input-field" type="number" step="0.1" placeholder="—"
                  value={env[k] ?? ''} onChange={e => {
                    const val = e.target.value === '' ? null : Number(e.target.value);
                    const next = { ...env, [k]: val };
                    next.brightAvg = next.brightMin != null && next.brightMax != null ? Math.round((next.brightMin + next.brightMax) / 2 * 10) / 10 : null;
                    setEnv(next);
                  }} />
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>💨 호흡 / 체온</div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>호흡수 (최소 / 평균 / 최대)</label>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              {(['min', 'avg', 'max'] as const).map(k => (
                <input key={k} className="input-field" type="number" value={breath[k]} onChange={e => setBreath({ ...breath, [k]: Number(e.target.value) })} />
              ))}
            </div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>체온 상승 델타 °C (최소 / 평균 / 최대) — 절대 체온 아님</label>
            <div style={{ display: 'flex', gap: '6px' }}>
              {(['min', 'avg', 'max'] as const).map(k => (
                <input key={k} className="input-field" type="number" step="0.1" value={bodyTemp[k]} onChange={e => setBodyTemp({ ...bodyTemp, [k]: Number(e.target.value) })} />
              ))}
            </div>
          </div>

          <button className="btn-primary" style={{ padding: '14px', fontSize: '14px', letterSpacing: '0.5px' }} onClick={handleGenerate} disabled={loading}>
            {loading ? '⏳ Gemini 분석 중...' : '✨ AI 리포트 생성'}
          </button>
          <button className="btn-primary" style={{ background: 'transparent', border: '1px solid var(--gray-lt)', color: 'var(--gray-dark)', marginTop: '-6px' }} onClick={handleDownloadPdf} disabled={pdfLoading || !reportData}>
            {pdfLoading ? '⏳ PDF 생성 중...' : '⬇️ PDF 다운로드'}
          </button>
          <div style={{ display: 'flex', gap: 8, marginTop: '-4px' }}>
            {(['mobile', 'pc'] as const).map(mode => (
              <button key={mode} type="button" className="btn-primary" style={{ flex: 1, padding: '10px 12px', background: viewMode === mode ? 'var(--black)' : 'transparent', border: '1px solid var(--gray-lt)', color: viewMode === mode ? '#fff' : 'var(--gray-dark)' }} onClick={() => setViewMode(mode)}>
                {mode === 'mobile' ? '모바일 보기' : 'PC 보기'}
              </button>
            ))}
          </div>

          {error && (
            <div style={{ padding: '10px 12px', background: 'var(--accent-2-lt)', color: 'var(--accent-2)', borderRadius: '8px', fontSize: '12px', lineHeight: 1.5 }}>
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* 오른쪽 리포트 영역 — PC: 좌 데이터(SleepReport) + 우 가이드라인(ReportView) */}
        <div className="print-area" style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', background: 'var(--report-bg)', borderRadius: '16px', padding: viewMode === 'mobile' ? '8px 6px 24px' : '16px' }}>
          {loading ? (
            <div style={{ height: '100%', minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '20px' }}>
              <div style={{
                width: '48px', height: '48px', borderRadius: '50%',
                border: '4px solid rgba(255,255,255,0.2)',
                borderTopColor: 'var(--accent-1)',
                animation: 'spin 0.9s linear infinite',
              }} />
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--charcoal)', marginBottom: '6px' }}>Gemini 분석 중</div>
                <div style={{ fontSize: '12px', color: 'var(--gray-mut)' }}>보통 10~20초 정도 소요됩니다</div>
              </div>
            </div>
          ) : reportData && hasSleepReport ? (
            <ReportSplitLayout
              viewMode={viewMode}
              captureRef={captureRef}
              apiReportData={apiReportForGuidelines}
              meta={reportMeta}
              sleepReportData={sleepReportPayload}
              childName={sleepChildName}
              dateRange={sleepDateRange}
            />
          ) : (
            <div style={{ height: '100%', minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', color: 'var(--gray-mut)' }}>
              <div style={{ fontSize: '32px' }}>🌙</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--charcoal)' }}>리포트가 없습니다</div>
              <div style={{ fontSize: '12px', textAlign: 'center', lineHeight: 1.7 }}>
                JSON 파일을 올리거나 왼쪽에서 데이터를 입력한 후<br />
                <b>AI 리포트 생성</b> 버튼을 눌러주세요.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Demo;
