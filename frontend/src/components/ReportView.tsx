import React from 'react';
import { Chart, Radar } from 'react-chartjs-2';
import './charts/ChartSetup';
import { chartColors } from './charts/ChartSetup';

interface ReportViewProps {
  data: any;
  meta?: {
    ageMonths?: number;
    weekNum?: number;
    weekStart?: string;
    weekEnd?: string;
    generated?: string;
  };
}

function fmtMin(m: number) {
  const h = Math.floor(m / 60), mm = m % 60;
  return mm > 0 ? `${h}h ${mm}m` : `${h}h`;
}

function md2html(str: string) {
  return (str || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

const ReportView: React.FC<ReportViewProps> = ({ data, meta }) => {
  if (!data) return null;

  const { summary, breath, body_temp, daily, daily_stats, ai_comment, sleep_guide, age_kick } = data;

  // daily_stats는 { day, sleep_h, restless_min } 형태
  // daily는 { date, sleep_min, restless_min } 형태
  // 둘 다 지원
  const dailyRows: Array<{ day: string; sleepMin: number; restlessMin: number }> = [];
  if (daily && daily.length) {
    daily.forEach((d: any) => {
      const dayLabel = d.date ? new Date(d.date).toLocaleDateString('ko-KR', { weekday: 'short' }).replace('요일', '') : d.day || '-';
      dailyRows.push({ day: dayLabel, sleepMin: d.sleep_min ?? 0, restlessMin: d.restless_min ?? 0 });
    });
  } else if (daily_stats && daily_stats.length) {
    daily_stats.forEach((d: any) => {
      dailyRows.push({ day: d.day, sleepMin: Math.round((d.sleep_h || 0) * 60), restlessMin: d.restless_min ?? 0 });
    });
  }

  const avgSleepMin = dailyRows.length
    ? Math.round(dailyRows.reduce((s, d) => s + d.sleepMin, 0) / dailyRows.length)
    : summary?.avg_sleep_h ? Math.round(summary.avg_sleep_h * 60) : null;

  const avgRestless = dailyRows.length
    ? Math.round(dailyRows.reduce((s, d) => s + d.restlessMin, 0) / dailyRows.length)
    : summary?.avg_restless_min ?? null;

  // 레이더 차트 점수 계산
  const radarScores = () => {
    const sleep = summary?.avg_sleep_h != null ? Math.min(100, Math.round(summary.avg_sleep_h / 14 * 100)) : 50;
    const stable = summary?.avg_restless_min != null ? Math.max(0, Math.round(100 - summary.avg_restless_min / 60 * 100)) : 50;
    const bScore = breath?.is_normal != null ? (breath.is_normal ? 100 : 45) : (breath?.breath_avg ? (breath.breath_avg >= 20 && breath.breath_avg <= 40 ? 100 : 50) : 50);
    const tScore = body_temp?.status === '정상' ? 100 : body_temp?.status?.includes('주의') ? 60 : 30;
    return [sleep, stable, bScore, tScore];
  };

  const radarData = {
    labels: ['수면', '안정도', '호흡', '체온'],
    datasets: [{
      data: radarScores(),
      backgroundColor: chartColors.radarBackground,
      borderColor: chartColors.radarBorder,
      borderWidth: 2,
      pointBackgroundColor: chartColors.radarBorder,
      pointRadius: 3,
    }],
  };

  const radarOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        min: 0, max: 100,
        ticks: { display: false },
        grid: { color: chartColors.gridLight },
        pointLabels: { font: { size: 11, family: 'Noto Sans KR', weight: '600' }, color: chartColors.textDark },
      },
    },
    plugins: { legend: { display: false } },
    animation: { duration: 400 },
  };

  // 콤보 차트 (바 + 라인)
  const comboData = {
    labels: dailyRows.map(d => d.day),
    datasets: [
      {
        type: 'bar' as const,
        label: '수면 (시간)',
        data: dailyRows.map(d => +(d.sleepMin / 60).toFixed(1)),
        backgroundColor: chartColors.barSleep,
        borderRadius: { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 },
        maxBarThickness: 36,
        yAxisID: 'y',
        order: 2,
      },
      {
        type: 'line' as const,
        label: '뒤척임 (분)',
        data: dailyRows.map(d => d.restlessMin),
        borderColor: chartColors.lineRestless,
        backgroundColor: chartColors.lineRestlessBg,
        borderWidth: 2.5,
        pointBackgroundColor: chartColors.lineRestless,
        pointBorderColor: chartColors.pointBorder,
        pointBorderWidth: 1.5,
        pointRadius: 4.5,
        tension: 0.35,
        yAxisID: 'y2',
        order: 1,
      },
    ],
  };

  const comboOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    scales: {
      y: { position: 'left', min: 0, ticks: { font: { size: 10, family: 'Inter' }, color: chartColors.textLight, callback: (v: any) => v + 'h' }, grid: { color: chartColors.gridLight, tickLength: 0 }, border: { display: false } },
      y2: { position: 'right', min: 0, ticks: { font: { size: 10, family: 'Inter' }, color: chartColors.textLight, callback: (v: any) => v + 'm' }, grid: { drawOnChartArea: false }, border: { display: false } },
      x: { ticks: { font: { size: 11, family: 'Noto Sans KR', weight: '600' }, color: chartColors.textDark }, grid: { display: false }, border: { display: false } },
    },
    plugins: {
      legend: { position: 'top', align: 'end', labels: { font: { size: 11, family: 'Noto Sans KR', weight: '500' }, color: chartColors.textDark, usePointStyle: true, boxWidth: 8, padding: 16 } },
      tooltip: { backgroundColor: 'rgba(15,15,15,0.9)', titleFont: { family: 'Noto Sans KR' }, bodyFont: { family: 'Inter' }, padding: 12, cornerRadius: 8 },
    },
  };

  const S: Record<string, React.CSSProperties> = {
    container: { maxWidth: 430, margin: '0 auto', background: 'var(--bg-color)', display: 'flex', flexDirection: 'column' },
    pageBox: { padding: '32px 24px', display: 'flex', flexDirection: 'column', gap: 24 },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: 20, borderBottom: '1px solid var(--black)' },
    brandName: { fontFamily: 'Inter, sans-serif', fontSize: 18, fontWeight: 500, color: 'var(--black)', letterSpacing: 2, textTransform: 'uppercase' as const, lineHeight: 1.2 },
    brandSub: { fontSize: 9, color: 'var(--gray-mut)', marginTop: 4, fontFamily: 'Inter, sans-serif', textTransform: 'uppercase' as const, letterSpacing: 1 },
    headerInfo: { textAlign: 'right' as const },
    headerMain: { fontSize: 13, fontWeight: 500, color: 'var(--black)', letterSpacing: -0.3 },
    headerSub: { fontSize: 10, color: 'var(--gray-mut)', marginTop: 6, fontFamily: 'Inter, sans-serif', textTransform: 'uppercase' as const, letterSpacing: 0.5 },
    secTitle: { fontFamily: 'Inter, sans-serif', fontSize: 11, fontWeight: 600, color: 'var(--gray-mut)', textTransform: 'uppercase' as const, letterSpacing: 1.5, marginBottom: 12, borderBottom: '1px solid var(--gray-lt)', paddingBottom: 8 },
    compactStats: { display: 'flex', flexDirection: 'column' as const, gap: 8, marginBottom: 20 },
    cStatRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', background: 'var(--surface)', borderRadius: 8 },
    cStatLabel: { fontFamily: 'Inter, sans-serif', fontSize: 9, color: 'var(--gray-dark)', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: 0.8 },
    cStatValue: { fontFamily: 'Inter, sans-serif', fontSize: 14, fontWeight: 500, color: 'var(--black)' },
    summaryBox: { marginTop: 16, padding: 20, background: 'var(--black)', color: 'var(--bg-color)', borderRadius: 8, fontSize: 13, lineHeight: 1.7, fontWeight: 300 },
    summaryLabel: { fontFamily: 'Inter, sans-serif', fontSize: 10, fontWeight: 600, color: 'var(--gray-mut)', textTransform: 'uppercase' as const, letterSpacing: 1.5, marginBottom: 8, display: 'block' },
    aiSolTitle: { fontSize: 16, fontWeight: 500, color: 'var(--black)', marginBottom: 12, lineHeight: 1.4 },
    aiSolReason: { fontSize: 13, color: 'var(--gray-dark)', lineHeight: 1.7, marginBottom: 24, fontWeight: 300 },
    aiSteps: { display: 'flex', flexDirection: 'column' as const, gap: 16 },
    aiStep: { display: 'flex', gap: 16, paddingBottom: 16, borderBottom: '1px solid var(--gray-lt)' },
    stepNum: { fontFamily: 'Inter, sans-serif', fontWeight: 300, fontSize: 15, color: 'var(--gray-mut)', width: 24, flexShrink: 0, paddingTop: 2 },
    stepText: { fontSize: 13, color: 'var(--black)', lineHeight: 1.7, fontWeight: 400 },
    gridWrap: { display: 'flex', flexDirection: 'column' as const, gap: 24, marginTop: 8 },
    kickWrap: { padding: 20, background: 'var(--surface)', borderRadius: 8 },
    kickTitle: { fontSize: 14, fontWeight: 500, color: 'var(--black)', marginBottom: 12 },
    kickText: { fontSize: 12.5, color: 'var(--gray-dark)', lineHeight: 1.7, fontWeight: 300 },
    footer: { padding: '20px 24px', borderTop: '1px solid var(--gray-lt)', display: 'flex', flexDirection: 'column' as const, gap: 8, textAlign: 'center' as const, fontSize: 9, color: 'var(--gray-mut)', fontFamily: 'Inter, sans-serif', letterSpacing: 0.5 },
  };

  const aiCommentArr = Array.isArray(ai_comment) ? ai_comment : [];

  // ai_comment가 객체 배열인지 (원본 HTML형태: { type, label, title, text })
  // 또는 문자열 배열인지 (기존 React 형태) 확인
  const renderTipBox = (tip: any, idx: number) => {
    if (typeof tip === 'string') {
      return (
        <div key={idx} style={{ padding: '16px 20px', borderRadius: 8, marginBottom: 12, background: 'var(--surface)', borderLeft: '2px solid var(--gray-lt)' }}>
          <div style={{ fontSize: 12, color: 'var(--gray-dark)', lineHeight: 1.6, fontWeight: 300 }}>{tip}</div>
        </div>
      );
    }
    const isGood = tip.type === 'good';
    return (
      <div key={idx} style={{
        padding: '16px 20px', borderRadius: 8, marginBottom: 12,
        background: isGood ? 'var(--accent-1-lt)' : 'var(--accent-2-lt)',
        borderLeft: `2px solid ${isGood ? 'var(--accent-1)' : 'var(--accent-2)'}`,
      }}>
        {tip.label && <div style={{ fontFamily: 'Inter', fontSize: 10, fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: 1, color: isGood ? 'var(--accent-1)' : 'var(--accent-2)', marginBottom: 6 }}>{tip.label}</div>}
        {tip.title && <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--black)', marginBottom: 6 }}>{tip.title}</div>}
        <div style={{ fontSize: 12, color: 'var(--gray-dark)', lineHeight: 1.6, fontWeight: 300 }} dangerouslySetInnerHTML={{ __html: md2html(tip.text || '') }} />
      </div>
    );
  };

  return (
    <div style={S.container}>
      {/* ── PAGE 1 ── */}
      <div style={S.pageBox}>
        {/* Header */}
        <div style={S.header}>
          <div>
            <div style={S.brandName}>MOM-I Intelligence</div>
            <div style={S.brandSub}>Premium Sleep Diagnostics</div>
          </div>
          <div style={S.headerInfo}>
            {meta && <div style={S.headerMain}>{meta.ageMonths ? `아기 (${meta.ageMonths}M)` : ''}</div>}
            {meta?.weekNum && <div style={S.headerSub}>Week {meta.weekNum} ({meta.weekStart})</div>}
          </div>
        </div>

        {/* Data Overview */}
        <div>
          <div style={S.secTitle}>데이터 요약</div>
          {/* 레이더(좌) + 통계 행들(우) */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 20 }}>
            {/* 레이더 차트 */}
            <div style={{ flexShrink: 0, width: 140, background: 'var(--surface)', borderRadius: 8, padding: 12 }}>
              <div style={{ fontFamily: 'Inter', fontSize: 9, fontWeight: 600, color: 'var(--gray-mut)', textTransform: 'uppercase' as const, letterSpacing: 1, marginBottom: 6, textAlign: 'center' as const }}>균형</div>
              <div style={{ height: 130 }}>
                <Radar data={radarData} options={radarOptions} />
              </div>
            </div>
            {/* 통계 행들 */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' as const, gap: 6 }}>
              {avgSleepMin != null && (
                <div style={S.cStatRow}>
                  <span style={S.cStatLabel}>평균 수면</span>
                  <span style={S.cStatValue}>{fmtMin(avgSleepMin)}</span>
                </div>
              )}
              {avgRestless != null && (
                <div style={S.cStatRow}>
                  <span style={S.cStatLabel}>평균 뒤척임</span>
                  <span style={S.cStatValue}>{avgRestless}분</span>
                </div>
              )}
              {breath?.breath_avg != null && (
                <div style={S.cStatRow}>
                  <span style={S.cStatLabel}>평균 호흡수</span>
                  <span style={S.cStatValue}>{breath.breath_avg} rpm</span>
                </div>
              )}
              {body_temp?.body_temp_avg != null && (
                <div style={S.cStatRow}>
                  <span style={S.cStatLabel}>평균 체온</span>
                  <span style={S.cStatValue}>{body_temp.body_temp_avg}°C</span>
                </div>
              )}
            </div>
          </div>

          {/* Daily Table */}
          {dailyRows.length > 0 && (
            <div style={{ width: '100%', overflowX: 'auto', marginBottom: 20 }}>
              <table style={{ width: '100%', minWidth: 280, borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
                <thead>
                  <tr>
                    {['Day', 'Sleep', 'Toss', 'Breath', 'Temp'].map(h => (
                      <th key={h} style={{ fontFamily: 'Inter', fontWeight: 500, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, fontSize: 10, padding: '12px 8px', borderBottom: '1px solid var(--black)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dailyRows.map((row, i) => (
                    <tr key={i}>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Noto Sans KR', fontWeight: 500, color: 'var(--gray-dark)' }}>{row.day}</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>{fmtMin(row.sleepMin)}</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>{row.restlessMin}m</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>{breath?.breath_avg ? `${breath.breath_avg}` : '-'}</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>-</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 콤보 차트 (바 + 라인) */}
          {dailyRows.length > 0 && (
            <div style={{ background: 'var(--surface)', borderRadius: 8, padding: 12, marginBottom: 20, height: 200 }}>
              <Chart type='bar' data={comboData} options={comboOptions} />
            </div>
          )}

          {/* AI Summary (검은 배경) */}
          {(ai_comment && typeof ai_comment === 'string') || (aiCommentArr.length > 0 && typeof aiCommentArr[0] === 'string') ? (
            <div style={S.summaryBox}>
              <span style={S.summaryLabel}>AI 종합 의견</span>
              {typeof ai_comment === 'string'
                ? <span dangerouslySetInnerHTML={{ __html: md2html(ai_comment) }} />
                : aiCommentArr.map((c: string, i: number) => <p key={i} style={{ marginBottom: i < aiCommentArr.length - 1 ? 8 : 0 }}>{c}</p>)
              }
            </div>
          ) : null}
        </div>
      </div>

      {/* ── PAGE 2 ── */}
      <div style={S.pageBox}>
        {/* AI Solution */}
        {sleep_guide && (
          <div>
            <div style={S.secTitle}>핵심 솔루션</div>
            <div style={S.aiSolTitle}>{sleep_guide.title}</div>
            <div style={S.aiSolReason} dangerouslySetInnerHTML={{ __html: md2html(sleep_guide.reason || '') }} />
            <div style={S.aiSteps}>
              {(sleep_guide.steps || []).map((step: string, i: number) => (
                <div key={i} style={{ ...S.aiStep, ...(i === (sleep_guide.steps.length - 1) ? { borderBottom: 'none', paddingBottom: 0 } : {}) }}>
                  <div style={S.stepNum}>0{i + 1}</div>
                  <div style={S.stepText} dangerouslySetInnerHTML={{ __html: md2html(step) }} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Key Insights + Developmental Care */}
        <div style={S.gridWrap}>
          {/* Key Insights (tip boxes) */}
          {aiCommentArr.length > 0 && typeof aiCommentArr[0] !== 'string' && (
            <div>
              <div style={S.secTitle}>핵심 인사이트</div>
              {aiCommentArr.map((tip: any, i: number) => renderTipBox(tip, i))}
            </div>
          )}

          {/* Developmental Care */}
          {age_kick && (
            <div>
              <div style={S.secTitle}>발달 케어</div>
              <div style={S.kickWrap}>
                <div style={S.kickTitle}>{age_kick.title}</div>
                <div style={S.kickText} dangerouslySetInnerHTML={{ __html: md2html(age_kick.text || '') }} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={S.footer}>
        <span>© 2026 MOM-I INTELLIGENCE. ALL RIGHTS RESERVED.</span>
        {meta?.generated && <span>ISSUED: {meta.generated}</span>}
      </div>
    </div>
  );
};

export default ReportView;
