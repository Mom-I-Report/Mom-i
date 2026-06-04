import { useState, useEffect, useRef } from 'react';
import ReportSplitLayout from '../components/ReportSplitLayout';
import { downloadPdf } from '../utils/downloadPdf';
import { toSleepReportData, buildDateRange } from '../utils/sleepReportData';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

type Sub = { ser_no: string; account: string };

type ResultRow = {
  ser_no: string;
  account: string;
  status: 'ok' | 'error';
  week_label?: string;
  avg_sleep_h?: number;
  report?: Record<string, unknown>;
  error?: string;
};

export default function Batch() {
  const [apiKey, setApiKey]           = useState(import.meta.env.VITE_API_KEY ?? '');
  const [subs, setSubs]               = useState<Sub[]>([]);
  const [selected, setSelected]       = useState<Set<string>>(new Set());
  const [subsLoading, setSubsLoading] = useState(false);
  const [subsErr, setSubsErr]         = useState('');
  const [running, setRunning]         = useState<Set<string>>(new Set());
  const [results, setResults]         = useState<Record<string, ResultRow>>({});
  const [pdfLoading, setPdfLoading]   = useState('');

  // PDF 캡처용
  const captureRef = useRef<HTMLDivElement>(null);
  const [pdfCapture, setPdfCapture]   = useState<{ data: Record<string, unknown>; version: 'mobile' | 'pc'; label: string } | null>(null);

  useEffect(() => {
    if (!pdfCapture || !captureRef.current) return;
    const el = captureRef.current;
    const timer = setTimeout(async () => {
      try {
        await downloadPdf(el, pdfCapture.label);
      } finally {
        setPdfCapture(null);
        setPdfLoading('');
      }
    }, 1200);
    return () => clearTimeout(timer);
  }, [pdfCapture]);

  const openPdf = (ser_no: string, version: 'mobile' | 'pc') => {
    const result = results[ser_no];
    if (!result?.report) return;
    const key = `${ser_no}-${version}`;
    setPdfLoading(key);
    setPdfCapture({
      data: result.report,
      version,
      label: `${ser_no}_${result.week_label ?? ''}`.replace(/\s/g, '_'),
    });
  };

  const loadSubs = async (key: string) => {
    if (!key) return;
    setSubsLoading(true);
    setSubsErr('');
    try {
      const res = await fetch(`${BASE_URL}/api/v1/subscriptions`, {
        headers: { 'X-API-Key': key },
      });
      if (res.status === 403) throw new Error('API Key가 올바르지 않습니다.');
      if (!res.ok) throw new Error(`서버 오류 ${res.status}`);
      setSubs(await res.json());
    } catch (e: any) {
      setSubsErr(e.message);
    } finally {
      setSubsLoading(false);
    }
  };

  useEffect(() => { if (apiKey) loadSubs(apiKey); }, []);

  const toggleAll = () => {
    if (selected.size === subs.length) setSelected(new Set());
    else setSelected(new Set(subs.map(s => s.ser_no)));
  };

  const toggle = (ser_no: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(ser_no) ? next.delete(ser_no) : next.add(ser_no);
      return next;
    });
  };

  const runSelected = async () => {
    const targets = subs.filter(s => selected.has(s.ser_no));
    setRunning(new Set(targets.map(s => s.ser_no)));
    setResults({});
    await Promise.all(targets.map(async sub => {
      const params = new URLSearchParams({ account: sub.account, uid: sub.ser_no, ser_no: sub.ser_no });
      try {
        const res = await fetch(`${BASE_URL}/api/v1/admin/emtake/generate?${params}`, {
          method: 'POST',
          headers: { 'X-API-Key': apiKey },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail ?? `서버 오류 ${res.status}`);
        setResults(prev => ({ ...prev, [sub.ser_no]: { ...sub, status: 'ok', ...data } }));
      } catch (e: any) {
        setResults(prev => ({ ...prev, [sub.ser_no]: { ...sub, status: 'error', error: e.message } }));
      } finally {
        setRunning(prev => { const next = new Set(prev); next.delete(sub.ser_no); return next; });
      }
    }));
  };

  const allSelected = subs.length > 0 && selected.size === subs.length;
  const someSelected = selected.size > 0;

  return (
    <div style={s.page}>
      {/* 숨겨진 PDF 캡처 영역 */}
      {pdfCapture && (
        <div style={{ position: 'absolute', left: -9999, top: 0, width: pdfCapture.version === 'mobile' ? 390 : 860, background: '#fff' }}>
          <div ref={captureRef}>
            <ReportSplitLayout
              viewMode={pdfCapture.version}
              apiReportData={pdfCapture.data}
              sleepReportData={toSleepReportData(pdfCapture.data)}
              childName={(() => {
                const n = pdfCapture.data.baby_name as string | undefined;
                const g = pdfCapture.data.baby_gender as string | undefined;
                const title = g === 'M' ? ' 왕자님' : g === 'F' ? ' 공주님' : '';
                return n ? `${n}${title}` : '아기';
              })()}
              dateRange={buildDateRange(pdfCapture.data)}
              meta={{
                ageMonths: (pdfCapture.data.baby_age_months as number) || 0,
                name: pdfCapture.data.baby_name as string | undefined,
                gender: pdfCapture.data.baby_gender as string | undefined,
              }}
            />
          </div>
        </div>
      )}

      <div style={s.header}>
        <div style={s.logo}>MOM<span style={{ color: '#24614A' }}>-I</span></div>
        <div style={s.headerSub}>Batch Report Generator</div>
      </div>

      <div style={s.card}>
        <div style={s.row}>
          <input style={s.input} type="password" placeholder="X-API-Key" value={apiKey} onChange={e => setApiKey(e.target.value)} />
          <button style={{ ...s.btn, background: '#2C2C2E' }} onClick={() => loadSubs(apiKey)} disabled={subsLoading}>
            {subsLoading ? '로딩...' : '목록 불러오기'}
          </button>
        </div>
        {subsErr && <p style={s.error}>{subsErr}</p>}
      </div>

      {!subsLoading && subs.length === 0 && !subsErr && apiKey && (
        <div style={s.card}>
          <p style={{ color: '#555', fontSize: 13, margin: 0 }}>구독자가 없습니다. 엠테이크 서버에서 구독 등록 후 다시 불러오세요.</p>
        </div>
      )}

      {subs.length > 0 && (
        <div style={s.card}>
          <div style={{ ...s.row, justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>구독자 목록 ({subs.length}명)</div>
            <label style={s.toggle}>
              <input type="checkbox" checked={allSelected} onChange={toggleAll} style={{ marginRight: 6 }} />
              전체 선택
            </label>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {subs.map(sub => {
              const result = results[sub.ser_no];
              const isRunning = running.has(sub.ser_no);
              return (
                <label key={sub.ser_no} style={{ ...s.subRow, background: selected.has(sub.ser_no) ? '#1A2E24' : '#0F0F0F' }}>
                  <input type="checkbox" checked={selected.has(sub.ser_no)} onChange={() => toggle(sub.ser_no)} style={{ marginRight: 12, accentColor: '#24614A' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, color: '#fff' }}>{sub.account}</div>
                    <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>{sub.ser_no}</div>
                  </div>
                  {isRunning && <div style={s.spinner} />}
                  {result && !isRunning && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ ...s.badge, background: result.status === 'ok' ? '#1A3A25' : '#3A1A1A', color: result.status === 'ok' ? '#4ADE80' : '#F87171' }}>
                        {result.status === 'ok' ? `완료 · ${result.week_label} · ${result.avg_sleep_h}h` : `실패 · ${result.error}`}
                      </span>
                      {result.status === 'ok' && result.report && (
                        <>
                          <button onClick={e => { e.preventDefault(); openPdf(sub.ser_no, 'mobile'); }} style={{ ...s.pdfBtn, opacity: pdfLoading === `${sub.ser_no}-mobile` ? 0.5 : 1 }} disabled={!!pdfLoading}>
                            {pdfLoading === `${sub.ser_no}-mobile` ? '생성 중...' : '모바일 PDF'}
                          </button>
                          <button onClick={e => { e.preventDefault(); openPdf(sub.ser_no, 'pc'); }} style={{ ...s.pdfBtn, opacity: pdfLoading === `${sub.ser_no}-pc` ? 0.5 : 1 }} disabled={!!pdfLoading}>
                            {pdfLoading === `${sub.ser_no}-pc` ? '생성 중...' : 'PC PDF'}
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </label>
              );
            })}
          </div>
        </div>
      )}

      {someSelected && (
        <div style={s.card}>
          <div style={s.row}>
            <button style={{ ...s.btn, marginLeft: 'auto', opacity: running.size > 0 ? 0.6 : 1 }} onClick={runSelected} disabled={running.size > 0}>
              {running.size > 0 ? `생성 중... (${running.size}명)` : `선택 ${selected.size}명 리포트 생성`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0F0F0F', color: '#fff', fontFamily: "'Outfit', sans-serif", padding: '48px 24px', maxWidth: 960, margin: '0 auto' },
  header: { marginBottom: 40 },
  logo: { fontSize: 28, fontWeight: 800, letterSpacing: 2, marginBottom: 4 },
  headerSub: { fontSize: 13, color: '#555', letterSpacing: 1, textTransform: 'uppercase' },
  card: { background: '#1C1C1E', border: '1px solid #2C2C2E', borderRadius: 12, padding: '20px 24px', marginBottom: 16 },
  row: { display: 'flex', gap: 12, alignItems: 'center' },
  input: { flex: 1, background: '#0F0F0F', border: '1px solid #2C2C2E', borderRadius: 8, padding: '10px 14px', color: '#fff', fontSize: 14, fontFamily: 'monospace' },
  btn: { background: '#24614A', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' },
  error: { color: '#F87171', fontSize: 13, marginTop: 10 },
  toggle: { display: 'flex', alignItems: 'center', fontSize: 13, color: '#aaa', cursor: 'pointer', whiteSpace: 'nowrap' },
  subRow: { display: 'flex', alignItems: 'center', padding: '12px 14px', borderRadius: 8, cursor: 'pointer', border: '1px solid #2C2C2E' },
  spinner: { width: 16, height: 16, border: '2px solid #2C2C2E', borderTop: '2px solid #24614A', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  badge: { padding: '3px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap' },
  pdfBtn: { padding: '3px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600, background: '#2C2C2E', color: '#aaa', border: '1px solid #3C3C3E', cursor: 'pointer', whiteSpace: 'nowrap' },
};
