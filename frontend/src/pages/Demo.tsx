import { useState } from 'react';
import ReportBody from '../components/report/ReportBody';
import { generateReport } from '../lib/api';
import { exportPdf } from '../lib/pdf';
import type { ReportJson, SleepInput } from '../types/report';

const DAYS = ['월', '화', '수', '목', '금', '토', '일'];
const SLEEP_DEF    = [710, 745, 630, 780, 700, 785, 690];
const RESTLESS_DEF = [25,  15,  55,  10,  35,  20,  40];

interface SleepRow { sleep_min: number; restless_min: number }

interface ReportMeta {
  ageMonths: number;
  weekNum: number;
  weekStart: string;
  weekEnd: string;
  generated: string;
}

function fmtDate(d: Date) {
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

export default function Demo() {
  const [serNo,        setSerNo]        = useState('');
  const [ageMonths,    setAgeMonths]    = useState(7);
  const [weekStart,    setWeekStart]    = useState('2026-04-14');
  const [sleep,        setSleep]        = useState<SleepRow[]>(
    DAYS.map((_, i) => ({ sleep_min: SLEEP_DEF[i], restless_min: RESTLESS_DEF[i] }))
  );
  const [tempAvg,      setTempAvg]      = useState(22.0);
  const [tempMax,      setTempMax]      = useState(23.5);
  const [tempMin,      setTempMin]      = useState(21.5);
  const [dbMax,        setDbMax]        = useState(58);
  const [dbAvg,        setDbAvg]        = useState(44);
  const [breathMin,    setBreathMin]    = useState(22);
  const [breathAvg,    setBreathAvg]    = useState(30);
  const [breathMax,    setBreathMax]    = useState(38);
  const [btMin,        setBtMin]        = useState(36.3);
  const [btAvg,        setBtAvg]        = useState(36.7);
  const [btMax,        setBtMax]        = useState(37.1);
  const [monthSleep,   setMonthSleep]   = useState(12.5);
  const [monthRestless,setMonthRestless]= useState(0.5);
  const [cryCount,     setCryCount]     = useState(5);
  const [leaveCount,   setLeaveCount]   = useState(2);

  const [report,    setReport]    = useState<ReportJson | null>(null);
  const [meta,      setMeta]      = useState<ReportMeta | null>(null);
  const [status,    setStatus]    = useState('');
  const [statusCls, setStatusCls] = useState('');
  const [loading,   setLoading]   = useState(false);
  const [pdfLoading,setPdfLoading]= useState(false);

  function updateSleep(i: number, key: keyof SleepRow, val: number) {
    setSleep(prev => prev.map((r, idx) => idx === i ? { ...r, [key]: val } : r));
  }

  function buildMeta(): ReportMeta {
    const [wy, wm, wd] = weekStart.split('-').map(Number);
    const ws = new Date(wy, wm - 1, wd);
    const we = new Date(wy, wm - 1, wd + 6);
    return {
      ageMonths,
      weekNum: Math.floor((ws.getDate() - 1) / 7) + 1,
      weekStart: fmtDate(ws),
      weekEnd:   fmtDate(we),
      generated: fmtDate(new Date()),
    };
  }

  async function handleGenerate() {
    setLoading(true);
    setStatus('요청 중 — 10~20초 소요될 수 있습니다.');
    setStatusCls('');

    const [wy, wm, wd] = weekStart.split('-').map(Number);
    const sleepInput: SleepInput[] = DAYS.map((_, i) => {
      const d = new Date(wy, wm - 1, wd + i);
      return {
        date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
        sleep_min:    sleep[i].sleep_min,
        restless_min: sleep[i].restless_min,
      };
    });

    try {
      const rj = await generateReport({
        ser_no:          serNo.trim() || `DEMO-${ageMonths}m`,
        baby_age_months: ageMonths,
        week_start:      weekStart,
        sleep:           sleepInput,
        environment: { temp_avg: tempAvg, temp_max: tempMax, temp_min: tempMin, db_max: dbMax, db_avg: dbAvg },
        breath:      { breath_min: breathMin, breath_max: breathMax, breath_avg: breathAvg },
        body_temp:   { body_temp_min: btMin, body_temp_max: btMax, body_temp_avg: btAvg },
        monthly:     { month_sleep_h: monthSleep, month_restless_h: monthRestless },
        events:      { cry_count: cryCount, leave_count: leaveCount },
      });
      setReport(rj);
      setMeta(buildMeta());
      setStatus('✅ AI 리포트 생성 완료');
      setStatusCls('ok');
    } catch (e) {
      setStatus(`오류: ${(e as Error).message}`);
      setStatusCls('err');
    } finally {
      setLoading(false);
    }
  }

  async function handlePdf() {
    if (!report || !meta) { setStatus('먼저 AI 리포트를 생성하세요.'); setStatusCls('err'); return; }
    setPdfLoading(true);

    const headerHtml = `
      <div class="rep-header">
        <div>
          <div class="brand-name">Mom-i</div>
          <div class="brand-sub">프리미엄 수면 교육 가이드</div>
        </div>
        <div class="header-info">
          <div class="header-main">아기 (${meta.ageMonths}개월) · ${meta.weekNum}주차</div>
          <div class="header-sub">${meta.weekStart} ~ ${meta.weekEnd}</div>
        </div>
      </div>`;

    try {
      await exportPdf(report, headerHtml, `아기_${meta.ageMonths}개월_${meta.weekNum}주차`);
      setStatus('✅ PDF 저장 완료'); setStatusCls('ok');
    } catch (e) {
      setStatus(`PDF 저장 실패: ${(e as Error).message}`); setStatusCls('err');
    } finally {
      setPdfLoading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>🌙 Mom-i AI 리포트 테스트</h1>
        <a href="/admin.html">← 관리자 홈</a>
      </div>

      <div className="layout">
        {/* 왼쪽 입력 패널 */}
        <div className="panel-left">
          <div className="card">
            <div className="card-title">👶 기본 정보</div>
            <div className="field">
              <label>기기 번호 (ser_no) — 비우면 자동 생성</label>
              <input type="text" value={serNo} onChange={e => setSerNo(e.target.value)} placeholder="예: DEMO-7m" />
            </div>
            <div className="grid-2">
              <div className="field">
                <label>월령 (개월)</label>
                <input type="number" value={ageMonths} min={0} max={36} onChange={e => setAgeMonths(+e.target.value)} />
              </div>
              <div className="field">
                <label>주 시작일 (월요일)</label>
                <input type="date" value={weekStart} onChange={e => setWeekStart(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">😴 수면 데이터 (7일)</div>
            <table className="sleep-table">
              <thead><tr><th>요일</th><th>수면 (분)</th><th>뒤척임 (분)</th></tr></thead>
              <tbody>
                {DAYS.map((day, i) => (
                  <tr key={day}>
                    <td className="day-label">{day}</td>
                    <td><input type="number" value={sleep[i].sleep_min} min={0} max={1440} onChange={e => updateSleep(i, 'sleep_min', +e.target.value)} /></td>
                    <td><input type="number" value={sleep[i].restless_min} min={0} max={300} onChange={e => updateSleep(i, 'restless_min', +e.target.value)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="card-title">🌡️ 실내 환경</div>
            <div className="grid-3">
              <div className="field"><label>평균 온도</label><input type="number" step={0.1} value={tempAvg} onChange={e => setTempAvg(+e.target.value)} /></div>
              <div className="field"><label>최고 온도</label><input type="number" step={0.1} value={tempMax} onChange={e => setTempMax(+e.target.value)} /></div>
              <div className="field"><label>최저 온도</label><input type="number" step={0.1} value={tempMin} onChange={e => setTempMin(+e.target.value)} /></div>
            </div>
            <div className="grid-2" style={{ marginTop: 6 }}>
              <div className="field"><label>최대 소음 (dB)</label><input type="number" value={dbMax} onChange={e => setDbMax(+e.target.value)} /></div>
              <div className="field"><label>평균 소음 (dB)</label><input type="number" value={dbAvg} onChange={e => setDbAvg(+e.target.value)} /></div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">💨 호흡수 (회/분)</div>
            <div className="grid-3">
              <div className="field"><label>최소</label><input type="number" value={breathMin} onChange={e => setBreathMin(+e.target.value)} /></div>
              <div className="field"><label>평균</label><input type="number" value={breathAvg} onChange={e => setBreathAvg(+e.target.value)} /></div>
              <div className="field"><label>최대</label><input type="number" value={breathMax} onChange={e => setBreathMax(+e.target.value)} /></div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">🌡️ 체온 (°C)</div>
            <div className="grid-3">
              <div className="field"><label>최소</label><input type="number" step={0.1} value={btMin} onChange={e => setBtMin(+e.target.value)} /></div>
              <div className="field"><label>평균</label><input type="number" step={0.1} value={btAvg} onChange={e => setBtAvg(+e.target.value)} /></div>
              <div className="field"><label>최고</label><input type="number" step={0.1} value={btMax} onChange={e => setBtMax(+e.target.value)} /></div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">📅 월간 집계 &amp; 이벤트</div>
            <div className="grid-2">
              <div className="field"><label>월간 평균 수면 (h)</label><input type="number" step={0.1} value={monthSleep} onChange={e => setMonthSleep(+e.target.value)} /></div>
              <div className="field"><label>월간 뒤척임 (h)</label><input type="number" step={0.1} value={monthRestless} onChange={e => setMonthRestless(+e.target.value)} /></div>
              <div className="field"><label>울음 감지 (회)</label><input type="number" value={cryCount} onChange={e => setCryCount(+e.target.value)} /></div>
              <div className="field"><label>카메라 이탈 (회)</label><input type="number" value={leaveCount} onChange={e => setLeaveCount(+e.target.value)} /></div>
            </div>
          </div>

          <div className={`status-msg ${statusCls}`}>{status}</div>
          <button className="run-btn" disabled={loading} onClick={handleGenerate}>
            {loading ? '⏳ Gemini 분석 중...' : '✨ AI 리포트 생성'}
          </button>
          <button className="run-btn secondary" disabled={pdfLoading || !report} onClick={handlePdf}>
            {pdfLoading ? '⏳ PDF 생성 중...' : '🖨️ PDF 저장'}
          </button>
        </div>

        {/* 오른쪽 리포트 패널 */}
        <div className="panel-right">
          <div className="a4">
            {report && meta ? (
              <>
                <div className="rep-header">
                  <div>
                    <div className="brand-name">Mom-i</div>
                    <div className="brand-sub">프리미엄 수면 교육 가이드</div>
                  </div>
                  <div className="header-info">
                    <div className="header-main">아기 ({meta.ageMonths}개월) · {meta.weekNum}주차</div>
                    <div className="header-sub">{meta.weekStart} ~ {meta.weekEnd}</div>
                  </div>
                </div>
                <ReportBody rj={report} showTrend={false} />
                <div className="rep-footer">
                  <span>Mom-i © 2026 · 본 가이드라인은 의학적 진단을 대체하지 않습니다.</span>
                  <span>생성일: {meta.generated}</span>
                </div>
              </>
            ) : (
              <div className="placeholder">
                <div className="ph-icon">🌙</div>
                <p>값을 입력하고 "AI 리포트 생성"을 누르세요.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
