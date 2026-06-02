import { useState } from 'react';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

type ResultRow = {
  ser_no: string;
  account: string;
  status: 'ok' | 'error';
  week_label?: string;
  avg_sleep_h?: number;
  shared_report_list?: string[];
  error?: string;
};

export default function Batch() {
  const [apiKey, setApiKey]     = useState(import.meta.env.VITE_API_KEY ?? '');
  const [notify, setNotify]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [summary, setSummary]   = useState<{ total: number; ok: number; error: number } | null>(null);
  const [results, setResults]   = useState<ResultRow[]>([]);
  const [errMsg, setErrMsg]     = useState('');

  const run = async () => {
    setLoading(true);
    setErrMsg('');
    setSummary(null);
    setResults([]);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/admin/emtake/generate-all?dry_run=${!notify}`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
      });
      if (res.status === 403) throw new Error('API Key가 올바르지 않습니다.');
      if (!res.ok) throw new Error(`서버 오류 ${res.status}`);
      const data = await res.json();
      setSummary({ total: data.total, ok: data.ok, error: data.error });
      setResults(data.results);
    } catch (e: any) {
      setErrMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div style={s.logo}>MOM<span style={{ color: '#24614A' }}>-I</span></div>
        <div style={s.headerSub}>Batch Report Generator</div>
      </div>

      <div style={s.card}>
        <div style={s.row}>
          <input
            style={s.input}
            type="password"
            placeholder="X-API-Key"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
          />
          <label style={s.toggle}>
            <input
              type="checkbox"
              checked={notify}
              onChange={e => setNotify(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            알림 발송
          </label>
          <button style={{ ...s.btn, opacity: loading ? 0.6 : 1 }} onClick={run} disabled={loading}>
            {loading ? '생성 중...' : '전체 리포트 생성'}
          </button>
        </div>
        {notify && (
          <p style={s.notifyWarn}>SMS/이메일이 실제 발송됩니다.</p>
        )}
        {errMsg && <p style={s.error}>{errMsg}</p>}
      </div>

      {loading && (
        <div style={s.card}>
          <p style={s.loadingText}>구독자 전체 리포트 생성 중입니다. 잠시 기다려주세요...</p>
          <div style={s.spinner} />
        </div>
      )}

      {summary && (
        <div style={s.summaryRow}>
          <div style={{ ...s.summaryChip, background: '#1A2E24' }}>
            전체 <strong>{summary.total}</strong>
          </div>
          <div style={{ ...s.summaryChip, background: '#1A3A25' }}>
            성공 <strong style={{ color: '#4ADE80' }}>{summary.ok}</strong>
          </div>
          {summary.error > 0 && (
            <div style={{ ...s.summaryChip, background: '#3A1A1A' }}>
              실패 <strong style={{ color: '#F87171' }}>{summary.error}</strong>
            </div>
          )}
        </div>
      )}

      {results.length > 0 && (
        <div style={s.card}>
          <table style={s.table}>
            <thead>
              <tr>
                {['상태', '계정', 'ser_no', '리포트 주차', '평균 수면', '알림 수신'].map(h => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #1C1C1E' }}>
                  <td style={s.td}>
                    <span style={{
                      ...s.badge,
                      background: r.status === 'ok' ? '#1A3A25' : '#3A1A1A',
                      color:      r.status === 'ok' ? '#4ADE80' : '#F87171',
                    }}>
                      {r.status === 'ok' ? '완료' : '실패'}
                    </span>
                  </td>
                  <td style={s.td}>{r.account}</td>
                  <td style={{ ...s.td, color: '#666' }}>{r.ser_no}</td>
                  <td style={s.td}>{r.week_label ?? '-'}</td>
                  <td style={s.td}>{r.avg_sleep_h != null ? `${r.avg_sleep_h}h` : r.error ?? '-'}</td>
                  <td style={s.td}>{r.shared_report_list?.join(', ') ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#0F0F0F',
    color: '#fff',
    fontFamily: "'Outfit', sans-serif",
    padding: '48px 24px',
    maxWidth: 960,
    margin: '0 auto',
  },
  header: { marginBottom: 40 },
  logo: { fontSize: 28, fontWeight: 800, letterSpacing: 2, marginBottom: 4 },
  headerSub: { fontSize: 13, color: '#555', letterSpacing: 1, textTransform: 'uppercase' },
  card: {
    background: '#1C1C1E',
    border: '1px solid #2C2C2E',
    borderRadius: 12,
    padding: '20px 24px',
    marginBottom: 16,
  },
  row: { display: 'flex', gap: 12, alignItems: 'center' },
  input: {
    flex: 1,
    background: '#0F0F0F',
    border: '1px solid #2C2C2E',
    borderRadius: 8,
    padding: '10px 14px',
    color: '#fff',
    fontSize: 14,
    fontFamily: 'monospace',
  },
  btn: {
    background: '#24614A',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '10px 24px',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  error: { color: '#F87171', fontSize: 13, marginTop: 10 },
  toggle: { display: 'flex', alignItems: 'center', fontSize: 13, color: '#aaa', cursor: 'pointer', whiteSpace: 'nowrap' },
  notifyWarn: { color: '#FBBF24', fontSize: 12, marginTop: 10 },
  loadingText: { color: '#888', fontSize: 13, marginBottom: 12 },
  spinner: {
    width: 24, height: 24,
    border: '2px solid #2C2C2E',
    borderTop: '2px solid #24614A',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  summaryRow: { display: 'flex', gap: 10, marginBottom: 16 },
  summaryChip: {
    borderRadius: 8, padding: '10px 18px',
    fontSize: 14, color: '#aaa',
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    textAlign: 'left', padding: '10px 12px',
    color: '#555', fontWeight: 600,
    fontSize: 11, textTransform: 'uppercase', letterSpacing: 1,
    borderBottom: '1px solid #2C2C2E',
  },
  td: { padding: '12px 12px', color: '#ccc', verticalAlign: 'middle' },
  badge: { padding: '3px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600 },
};
