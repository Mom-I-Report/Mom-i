import React, { useState } from 'react';
import ReportView from '../components/ReportView';

const DAYS = ['월', '화', '수', '목', '금', '토', '일'];
const SLEEP_DEFAULTS = [710, 745, 630, 780, 700, 785, 690];
const RESTLESS_DEFAULTS = [25, 15, 55, 10, 35, 20, 40];

// ─── 더미 데이터 ────────────────────────────────────────────────────────────────
// ⚠️ 실제 API 응답이 들어오면 이 데이터는 자동으로 교체됩니다.
// ⚠️ 배포 전에 실제 데이터 구조에 맞게 확인하세요.
const DUMMY_REPORT = {
  summary: { avg_sleep_h: 11.8, avg_restless_min: 29, cry_count: 8 },
  breath: { breath_avg: 28, breath_min: 22, breath_max: 38, is_normal: true },
  body_temp: { body_temp_avg: 36.6, status: '정상' },
  ai_comment: [
    { type: 'caution', label: 'ALERT', title: '수요일 수면 중단: 실내 온도 상승', text: '실내 온도가 23.5도로 오르며 뒤척임이 폭증했습니다. 7개월 아이 쾌적 온도는 21~22도입니다.' },
    { type: 'good', label: 'EXCELLENT', title: '안정적인 취침 시간 확보', text: '일주일 내내 21:00~22:00 사이의 취침 시간을 지켜주고 계십니다. 현재의 리듬을 반드시 유지해 주십시오.' },
  ],
  sleep_guide: {
    title: '[ ACTION PLAN ] "쉬닥법"을 활용한 연장 수면 가이드',
    reason: '수요일 새벽, 실내 온도 상승으로 인해 깬 이후 다시 혼자 잠드는 것에 어려움을 겪은 것으로 분석됩니다. 당장 울리기보다, 부모의 개입을 서서히 줄여나가는 쉬닥법이 가장 안전하고 효과적입니다.',
    steps: [
      '잠들기 30분 전 방 온도를 **21~22도**로 서늘하게 맞추고 백색소음기를 가동합니다.',
      '칭얼거리기 시작할 때 안아올리지 않습니다. 옆에 앉아 일정한 리듬으로 가슴을 토닥이며 조용히 "쉬-" 소리를 내어 진정시킵니다.',
      '아이가 하품을 하거나 **몽롱한 상태일 때 물리적 스킨십을 멈추고** 조용히 방을 이탈합니다.',
    ],
  },
  age_kick: {
    title: '7개월 차 분리불안 멘탈 케어',
    text: '7개월 시기 아이들은 인지능력이 발달하며 보호자가 시야에서 사라지는 것을 두려워합니다. 낮 시간에 "까꿍 놀이"를 반복하여, 부모가 잠시 안 보여도 곧 다시 나타난다는 굳건한 대상영속성을 심어주어야 합니다.',
  },
  daily: DAYS.map((day, i) => ({
    day,
    sleep_min: SLEEP_DEFAULTS[i],
    restless_min: RESTLESS_DEFAULTS[i],
  })),
};

const DUMMY_META = {
  ageMonths: 7,
  weekNum: 4,
  weekStart: '2026.04.14',
  weekEnd: '2026.04.20',
  generated: '2026.04.20',
};
// ─────────────────────────────────────────────────────────────────────────────

const DemoPage: React.FC = () => {
  // 초기값으로 더미 데이터를 보여줌. API 성공 시 실제 데이터로 교체됨.
  const [reportData, setReportData] = useState<any>(DUMMY_REPORT);
  const [reportMeta, setReportMeta] = useState<any>(DUMMY_META);
  const [isDummy, setIsDummy] = useState(true); // 현재 더미 데이터인지 여부
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 폼 상태
  const [serNo, setSerNo] = useState('');
  const [ageMonths, setAgeMonths] = useState(7);
  const [weekStart, setWeekStart] = useState('2026-04-14');
  const [sleepData, setSleepData] = useState(
    DAYS.map((d, i) => ({ day: d, sleep_min: SLEEP_DEFAULTS[i], restless_min: RESTLESS_DEFAULTS[i] }))
  );
  const [env, setEnv] = useState({ tempAvg: 22.0, tempMax: 23.5, tempMin: 21.5, dbMax: 58, dbAvg: 44 });
  const [breath, setBreath] = useState({ min: 22, avg: 30, max: 38 });
  const [bodyTemp, setBodyTemp] = useState({ min: 36.3, avg: 36.7, max: 37.1 });
  const [events, setEvents] = useState({ monthSleep: 12.5, monthRestless: 0.5, cryCount: 5, leaveCount: 2 });

  const buildRequest = () => {
    const [wy, wm, wd] = weekStart.split('-').map(Number);
    const sleep = sleepData.map((s, i) => {
      const d = new Date(wy, wm - 1, wd + i);
      const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      return { date: dateStr, sleep_min: s.sleep_min, restless_min: s.restless_min };
    });
    return {
      ser_no: serNo.trim() || `DEMO-${ageMonths}m`,
      baby_age_months: ageMonths,
      week_start: weekStart,
      sleep,
      environment: { temp_avg: env.tempAvg, temp_max: env.tempMax, temp_min: env.tempMin, db_max: env.dbMax, db_avg: env.dbAvg },
      breath: { breath_min: breath.min, breath_max: breath.max, breath_avg: breath.avg },
      body_temp: { body_temp_min: bodyTemp.min, body_temp_max: bodyTemp.max, body_temp_avg: bodyTemp.avg },
      monthly: { month_sleep_h: events.monthSleep, month_restless_h: events.monthRestless },
      events: { cry_count: events.cryCount, leave_count: events.leaveCount },
    };
  };

  const buildMeta = (req: any) => {
    const [wy, wm, wd] = req.week_start.split('-').map(Number);
    const ws = new Date(wy, wm - 1, wd);
    const we = new Date(wy, wm - 1, wd + 6);
    const fmt = (d: Date) => `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
    return {
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
    try {
      const req = buildRequest();
      const response = await fetch('http://localhost:8000/api/v1/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-local-key' },
        body: JSON.stringify(req),
      });
      if (!response.ok) throw new Error(`서버 오류 ${response.status}: ${await response.text()}`);

      const result = await response.json();
      // ✅ 실제 데이터로 교체
      setReportData(result);
      setReportMeta(buildMeta(req));
      setIsDummy(false);
    } catch (err: any) {
      console.error(err);
      setError(`API 호출 실패: ${err.message}`);
      // ❌ 실패 시 더미 데이터 유지 (교체하지 않음)
    } finally {
      setLoading(false);
    }
  };

  const handleSleepChange = (index: number, field: 'sleep_min' | 'restless_min', value: number) => {
    const newData = [...sleepData];
    newData[index][field] = value;
    setSleepData(newData);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--surface)' }}>
      {/* Header */}
      <div style={{ background: 'var(--black)', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#fff', fontFamily: 'Inter, sans-serif', letterSpacing: 1, textTransform: 'uppercase' }}>🌙 Mom-i AI Report Test</h1>
        <a href="/admin" style={{ color: 'rgba(255,255,255,0.7)', textDecoration: 'none', fontWeight: 500, fontSize: '13px' }}>← Admin Home</a>
      </div>

      <div style={{ display: 'flex', flex: 1, padding: '24px', gap: '24px', overflow: 'hidden' }}>

        {/* Left Panel - Inputs */}
        <div style={{ width: '360px', display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', paddingRight: '8px', flexShrink: 0 }}>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>👶 기본 정보</div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>기기 번호 (비우면 월령 기반 생성)</label>
            <input className="input-field" value={serNo} onChange={e => setSerNo(e.target.value)} placeholder="예: DEMO-7m" style={{ marginBottom: '10px' }} />
            <div style={{ display: 'flex', gap: '10px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>월령 (개월)</label>
                <input className="input-field" type="number" value={ageMonths} onChange={e => setAgeMonths(Number(e.target.value))} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>주 시작일 (월)</label>
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
                    <td style={{ padding: '4px', textAlign: 'center', fontWeight: 700, color: 'var(--black)', borderBottom: '1px solid var(--gray-lt)' }}>{d.day}</td>
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
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>🌡️ 환경</div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>온도 (평균 / 최고 / 최저)</label>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              {[['tempAvg', env.tempAvg], ['tempMax', env.tempMax], ['tempMin', env.tempMin]].map(([k, v]) => (
                <input key={k as string} className="input-field" type="number" step="0.1" value={v as number} onChange={e => setEnv({ ...env, [k]: Number(e.target.value) })} />
              ))}
            </div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>소음 (평균 / 최고)</label>
            <div style={{ display: 'flex', gap: '6px' }}>
              {[['dbAvg', env.dbAvg], ['dbMax', env.dbMax]].map(([k, v]) => (
                <input key={k as string} className="input-field" type="number" value={v as number} onChange={e => setEnv({ ...env, [k]: Number(e.target.value) })} />
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 0 }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: '12px', borderBottom: '1px solid var(--gray-lt)', paddingBottom: '8px' }}>💨 호흡 / 체온</div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>호흡수 (최소 / 평균 / 최대)</label>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              {[['min', breath.min], ['avg', breath.avg], ['max', breath.max]].map(([k, v]) => (
                <input key={k as string} className="input-field" type="number" value={v as number} onChange={e => setBreath({ ...breath, [k]: Number(e.target.value) })} />
              ))}
            </div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--gray-dark)', marginBottom: '4px' }}>체온 (최소 / 평균 / 최고)</label>
            <div style={{ display: 'flex', gap: '6px' }}>
              {[['min', bodyTemp.min], ['avg', bodyTemp.avg], ['max', bodyTemp.max]].map(([k, v]) => (
                <input key={k as string} className="input-field" type="number" step="0.1" value={v as number} onChange={e => setBodyTemp({ ...bodyTemp, [k]: Number(e.target.value) })} />
              ))}
            </div>
          </div>

          <button
            className="btn-primary"
            style={{ padding: '14px', fontSize: '14px', letterSpacing: '0.5px' }}
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? '⏳ Gemini 분석 중 (10~20초)...' : '✨ AI 리포트 생성'}
          </button>
          <button
            className="btn-primary"
            style={{ background: 'transparent', border: '1px solid var(--gray-lt)', color: 'var(--gray-dark)', marginTop: '-6px' }}
            onClick={() => window.print()}
          >
            🖨️ PDF 저장
          </button>

          {error && (
            <div style={{ padding: '10px 12px', background: 'var(--accent-2-lt)', color: 'var(--accent-2)', borderRadius: '8px', fontSize: '12px', lineHeight: 1.5 }}>
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* Right Panel - Report Preview */}
        <div style={{ flex: 1, overflowY: 'auto', background: '#E5E5EA', borderRadius: '16px', padding: '24px' }}>
          {/* 더미 데이터 안내 배너 */}
          {isDummy && (
            <div style={{ maxWidth: 430, margin: '0 auto 12px', padding: '10px 16px', background: 'rgba(15,15,15,0.08)', borderRadius: 8, fontSize: 11, color: 'var(--gray-dark)', fontFamily: 'Inter', letterSpacing: 0.5, textAlign: 'center' }}>
              PREVIEW MODE — 더미 데이터 표시 중. AI 리포트 생성 버튼을 누르면 실제 데이터로 교체됩니다.
            </div>
          )}
          <ReportView data={reportData} meta={reportMeta} />
        </div>

      </div>
    </div>
  );
};

export default DemoPage;
