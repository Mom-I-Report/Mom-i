import { useState } from 'react';
import ReportBody from '../components/report/ReportBody';
import ReportView from '../components/ReportView';
import { fetchDevices, fetchDeviceReports } from '../lib/api';
import { fmt, fmtDate } from '../lib/utils';
import type { Device, DeviceReport, ReportJson } from '../types/report';

export default function Admin() {
  const [apiKey,      setApiKey]      = useState('dev-local-key');
  const [devices,     setDevices]     = useState<Device[]>([]);
  const [authStatus,  setAuthStatus]  = useState('');
  const [authCls,     setAuthCls]     = useState('');
  const [reports,     setReports]     = useState<DeviceReport[]>([]);
  const [selectedSer, setSelectedSer] = useState<string | null>(null);
  const [currentTab,  setCurrentTab]  = useState(0);
  const [viewMode,    setViewMode]    = useState<'mobile' | 'pc'>('mobile');
  const [detailState, setDetailState] = useState<'idle' | 'loading' | 'error'>('idle');
  const [detailError, setDetailError] = useState('');

  async function handleLoadDevices() {
    setAuthStatus('불러오는 중...'); setAuthCls('');
    try {
      const data = await fetchDevices(apiKey);
      setDevices(data);
      setAuthStatus(`기기 ${data.length}개 조회됨`); setAuthCls('ok');
    } catch (e) {
      setAuthStatus((e as Error).message); setAuthCls('err');
    }
  }

  async function handleSelectDevice(serNo: string) {
    setSelectedSer(serNo);
    setCurrentTab(0);
    setDetailState('loading');
    setReports([]);
    try {
      const data = await fetchDeviceReports(apiKey, serNo);
      setReports(data);
      setDetailState('idle');
    } catch (e) {
      setDetailError((e as Error).message);
      setDetailState('error');
    }
  }

  const currentReport: ReportJson | null = reports[currentTab]?.report_json ?? null;

  return (
    <>
      <div className="page-header">
        <h1>Mom-i 관리자</h1>
        <a href="/demo.html">🧪 AI 테스트</a>
      </div>

      <div className="auth-bar">
        <input
          type="password"
          value={apiKey}
          onChange={e => setApiKey(e.target.value)}
          placeholder="X-API-Key 입력"
        />
        <button onClick={handleLoadDevices}>기기 목록 불러오기</button>
        <span className={`status-msg ${authCls}`}>{authStatus}</span>
      </div>

      <div className="layout">
        {/* 왼쪽: 기기 목록 */}
        <div className="panel-left admin-panel-left">
          <div className="card">
            <div className="card-title">기기 목록 (ser_no)</div>
            {devices.length === 0 ? (
              <div className="empty">위 버튼으로 기기 목록을 불러오세요.</div>
            ) : (
              <table className="device-table">
                <thead>
                  <tr>
                    <th>ser_no</th><th>구독 시작일</th><th>마지막 리포트</th><th>수</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {devices.map(d => (
                    <tr key={d.ser_no} className={selectedSer === d.ser_no ? 'active' : ''}>
                      <td><span className="ser-badge">{d.ser_no}</span></td>
                      <td>{fmtDate(d.subscribed_at)}</td>
                      <td>{fmt(d.last_report_at)}</td>
                      <td><span className="count-badge">{d.report_count}</span></td>
                      <td>
                        <button
                          className={`detail-btn ${selectedSer === d.ser_no ? 'active' : ''}`}
                          onClick={() => handleSelectDevice(d.ser_no)}
                        >
                          상세보기
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* 오른쪽: 리포트 상세 */}
        <div className="panel-right">
          <div className="card detail-panel">
            {detailState === 'idle' && !selectedSer && (
              <div className="placeholder" style={{ height: 300 }}>기기를 선택하면 최근 3주치 리포트를 표시합니다.</div>
            )}

            {detailState === 'loading' && (
              <div className="placeholder" style={{ height: 300 }}>불러오는 중...</div>
            )}

            {detailState === 'error' && (
              <div className="placeholder" style={{ height: 300, color: 'var(--red)', opacity: 1 }}>{detailError}</div>
            )}

            {detailState === 'idle' && selectedSer && reports.length > 0 && (
              <>
                <div className="detail-header">
                  <div>
                    <div className="detail-ser">{selectedSer}</div>
                    <div className="detail-sub">생성일: {fmt(reports[currentTab]?.created_at)}</div>
                  </div>
                </div>

                <div className="week-tabs">
                  {reports.map((r, i) => (
                    <button
                      key={r.report_id}
                      className={`week-tab ${i === currentTab ? 'active' : ''}`}
                      onClick={() => setCurrentTab(i)}
                    >
                      {r.report_json?.week_label ?? fmtDate(r.week_start)}
                    </button>
                  ))}
                </div>

                <div className="week-tabs" style={{ marginTop: -4 }}>
                  <button
                    className={`week-tab ${viewMode === 'mobile' ? 'active' : ''}`}
                    onClick={() => setViewMode('mobile')}
                  >
                    모바일 보기
                  </button>
                  <button
                    className={`week-tab ${viewMode === 'pc' ? 'active' : ''}`}
                    onClick={() => setViewMode('pc')}
                  >
                    PC 보기
                  </button>
                </div>

                {currentReport && (
                  viewMode === 'mobile'
                    ? <ReportBody rj={currentReport} showTrend={true} />
                    : <ReportView data={currentReport} />
                )}
              </>
            )}

            {detailState === 'idle' && selectedSer && reports.length === 0 && (
              <div className="placeholder" style={{ height: 300 }}>리포트가 없습니다.</div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
