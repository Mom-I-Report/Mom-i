import React, { useState, useRef } from 'react';
import ReportView from '../components/ReportView';
import { downloadPdf } from '../utils/pdfExport';

const Admin: React.FC = () => {
  const [apiKey, setApiKey] = useState('dev-local-key');
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [viewMode, setViewMode] = useState<'mobile' | 'pc'>('mobile');
  const [pdfLoading, setPdfLoading] = useState(false);
  const captureRef = useRef<HTMLDivElement>(null);

  const loadDevices = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/devices', {
        headers: { 'X-API-Key': apiKey },
      });
      if (res.status === 403) throw new Error('API Key가 올바르지 않습니다.');
      if (!res.ok) throw new Error(`오류 ${res.status}`);
      setDevices(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDeviceReports = async (serNo: string) => {
    setSelectedDevice(serNo);
    setReports([]);
    setActiveTab(0);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/devices/${encodeURIComponent(serNo)}/reports`, {
        headers: { 'X-API-Key': apiKey },
      });
      if (!res.ok) throw new Error(`리포트 조회 오류 ${res.status}`);
      setReports(await res.json());
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleDownloadPdf = async () => {
    const el = captureRef.current;
    if (!el) return;
    setPdfLoading(true);
    try {
      const r = reports[activeTab];
      const label = (r?.report_json?.week_label ?? r?.week_start ?? 'report').replace(/\s/g, '_');
      await downloadPdf(el, label);
    } finally {
      setPdfLoading(false);
    }
  };

  const formatDate = (s: string | null) => (s ? s.slice(0, 10) : '-');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-color)' }}>
      <div style={{ height: '60px', background: 'var(--black)', color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px', justifyContent: 'space-between' }}>
        <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: '16px' }}>
          MOM-I ADMIN
          <a href="/demo.html" style={{ color: '#fff', textDecoration: 'none', fontSize: '13px', background: 'var(--charcoal)', padding: '4px 12px', borderRadius: '20px' }}>🧪 AI 테스트</a>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--gray-mut)' }}>API Key:</span>
          <input
            type="text"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            style={{ padding: '6px 12px', borderRadius: '4px', border: 'none', background: 'var(--charcoal)', color: '#fff', fontSize: '13px' }}
          />
          <button
            onClick={loadDevices}
            style={{ padding: '6px 16px', background: 'var(--accent-1)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            {loading ? '조회 중...' : '기기 목록 조회'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '380px', borderRight: '1px solid var(--gray-lt)', background: 'var(--surface)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--gray-lt)' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700 }}>가입된 기기 목록</h2>
            {error && <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--accent-2)' }}>{error}</div>}
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {devices.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--gray-mut)', fontSize: '14px' }}>목록이 비어있습니다.</div>
            ) : (
              devices.map((d: any) => (
                <div
                  key={d.ser_no}
                  onClick={() => loadDeviceReports(d.ser_no)}
                  style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid var(--gray-lt)',
                    background: selectedDevice === d.ser_no ? '#fff' : 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--black)', marginBottom: '4px' }}>{d.ser_no}</div>
                    <div style={{ fontSize: '12px', color: 'var(--gray-dark)' }}>
                      최근 리포트: {formatDate(d.last_report_at)} ({d.report_count}건)
                    </div>
                  </div>
                  <span style={{ fontSize: '18px', color: 'var(--gray-mut)' }}>›</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ flex: 1, background: 'var(--gray-lt)', overflowY: 'auto', padding: '24px' }}>
          {!selectedDevice ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--gray-mut)' }}>
              좌측에서 기기를 선택하면 최근 3주치 리포트를 표시합니다.
            </div>
          ) : reports.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--gray-mut)' }}>
              생성된 리포트가 없습니다.
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {reports.map((r: any, idx: number) => (
                    <button
                      key={r.report_id}
                      onClick={() => setActiveTab(idx)}
                      style={{
                        padding: '10px 20px',
                        borderRadius: '8px',
                        border: 'none',
                        background: activeTab === idx ? 'var(--black)' : 'var(--bg-color)',
                        color: activeTab === idx ? '#fff' : 'var(--charcoal)',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      {formatDate(r.week_start)}
                    </button>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {(['mobile', 'pc'] as const).map(m => (
                    <button key={m} onClick={() => setViewMode(m)} style={{ padding: '8px 14px', borderRadius: '8px', border: 'none', background: viewMode === m ? 'var(--black)' : 'var(--bg-color)', color: viewMode === m ? '#fff' : 'var(--charcoal)', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}>
                      {m === 'mobile' ? '모바일' : 'PC'}
                    </button>
                  ))}
                  <button onClick={handleDownloadPdf} disabled={pdfLoading || !reports[activeTab]} style={{ padding: '8px 14px', borderRadius: '8px', border: 'none', background: 'var(--accent-1)', color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: '13px', opacity: !reports[activeTab] ? 0.4 : 1 }}>
                    {pdfLoading ? '⏳ PDF...' : '⬇️ PDF'}
                  </button>
                </div>
              </div>
              <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid var(--gray-lt)' }}>
                {reports[activeTab] && (
                  <ReportView
                    data={reports[activeTab].report_json}
                    hideSideAds={true}
                    mode={viewMode === 'pc' ? 'split' : 'default'}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      {/* PDF 캡처용 숨김 영역 */}
      <div style={{ position: 'fixed', left: '-9999px', top: 0, width: '1100px', background: '#fff', overflow: 'visible', pointerEvents: 'none' }}>
        <div ref={captureRef}>
          {reports[activeTab] && <ReportView data={reports[activeTab].report_json} mode="split" hideSideAds={true} />}
        </div>
      </div>
    </div>
  );
};

export default Admin;
