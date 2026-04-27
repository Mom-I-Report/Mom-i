import React, { useState } from 'react';
import ReportView from '../components/ReportView';
import { LucideSettings, LucideList, LucideChevronRight } from 'lucide-react';

const AdminPage: React.FC = () => {
  const [apiKey, setApiKey] = useState('dev-local-key');
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState(0);

  const loadDevices = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/devices`, { 
        headers: { 'X-API-Key': apiKey } 
      });
      if (res.status === 403) throw new Error('API Key가 올바르지 않습니다.');
      if (!res.ok) throw new Error(`오류 ${res.status}`);
      const data = await res.json();
      setDevices(data);
    } catch (e: any) {
      setError(e.message);
      // Dummy data fallback
      setDevices([
        { ser_no: 'cam-001', service_start_date: '2026-04-01T00:00:00Z', last_report_date: '2026-04-24T00:00:00Z', total_reports: 3 },
        { ser_no: 'cam-002', service_start_date: '2026-04-10T00:00:00Z', last_report_date: null, total_reports: 0 }
      ]);
      setError(e.message + ' (더미 데이터 표시)');
    } finally {
      setLoading(false);
    }
  };

  const loadDeviceReports = async (serNo: string) => {
    setSelectedDevice(serNo);
    setReports([]);
    setActiveTab(0);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/reports/${serNo}?limit=3`, {
        headers: { 'X-API-Key': apiKey }
      });
      if (!res.ok) throw new Error(`리포트 조회 오류 ${res.status}`);
      const data = await res.json();
      setReports(data);
    } catch (e: any) {
      console.error(e);
      // Dummy fallback
      setReports([
        {
          id: 1, created_at: '2026-04-25T10:00:00Z', target_start_date: '2026-04-18', target_end_date: '2026-04-24',
          report_json: {
            device_info: { device_name: serNo, baby_name: "더미" },
            score: 90,
            summary: { status: "정상", text: "수면 매우 좋음" }
          }
        }
      ]);
    }
  };

  const formatDate = (s: string) => s ? s.slice(0, 10) : '-';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-color)' }}>
      {/* Top Navbar */}
      <div style={{ height: '60px', background: 'var(--black)', color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px', justifyContent: 'space-between' }}>
        <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <LucideSettings size={20} />
            MOM-I ADMIN
          </div>
          <a href="/" style={{ color: '#fff', textDecoration: 'none', fontSize: '13px', background: 'var(--charcoal)', padding: '4px 12px', borderRadius: '20px' }}>🧪 AI 테스트</a>
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
        {/* Left Panel: Devices */}
        <div style={{ width: '380px', borderRight: '1px solid var(--gray-lt)', background: 'var(--surface)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--gray-lt)' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}><LucideList size={18} /> 가입된 기기 목록</h2>
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
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--black)', marginBottom: '4px' }}>{d.ser_no}</div>
                    <div style={{ fontSize: '12px', color: 'var(--gray-dark)' }}>
                      최근 리포트: {formatDate(d.last_report_date)} ({d.total_reports}건)
                    </div>
                  </div>
                  <LucideChevronRight size={18} color="var(--gray-mut)" />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Panel: Report Details */}
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
              {/* Tabs */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
                {reports.map((r: any, idx: number) => (
                  <button 
                    key={r.id}
                    onClick={() => setActiveTab(idx)}
                    style={{
                      padding: '10px 20px',
                      borderRadius: '8px',
                      border: 'none',
                      background: activeTab === idx ? 'var(--black)' : 'var(--bg-color)',
                      color: activeTab === idx ? '#fff' : 'var(--charcoal)',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {formatDate(r.target_start_date)} ~ {formatDate(r.target_end_date)}
                  </button>
                ))}
              </div>

              {/* Report Render */}
              <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid var(--gray-lt)' }}>
                {reports[activeTab] && (
                  <ReportView data={reports[activeTab].report_json} />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
