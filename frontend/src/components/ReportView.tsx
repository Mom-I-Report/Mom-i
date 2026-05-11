import React from 'react';
import { Chart, Radar } from 'react-chartjs-2';
import AdBanner from './AdBanner';
import './charts/ChartSetup';
import { chartColors } from './charts/ChartSetup';

interface ReportViewProps {
  data: any;
  mode?: 'default' | 'split';
  hideSideAds?: boolean;
  contentMaxWidth?: number;
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

// 덜덜 떨리거나 밀리는 현상(Jitter & Lag)을 완벽히 잡은 스크롤 추적 래퍼
const StickyWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [offset, setOffset] = React.useState(0);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    let scrollParent: HTMLElement | Window = window;
    let curr = ref.current?.parentElement;

    while (curr) {
      const style = window.getComputedStyle(curr);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
        scrollParent = curr;
        break;
      }
      curr = curr.parentElement;
    }

    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (scrollParent === window) {
            setOffset(window.scrollY > 24 ? window.scrollY - 24 : 0);
          } else {
            const parent = scrollParent as HTMLElement;
            setOffset(parent.scrollTop > 24 ? parent.scrollTop - 24 : 0);
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    scrollParent.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => scrollParent.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div
      ref={ref}
      style={{
        position: 'relative',
        top: `${offset}px`,
        height: 'max-content',
        willChange: 'top',
      }}
    >
      {children}
    </div>
  );
};

const ReportView: React.FC<ReportViewProps> = ({ data, meta, mode = 'default', hideSideAds = false, contentMaxWidth = 430 }) => {
  if (!data) return null;

  const { summary, breath, body_temp, daily, daily_stats, ai_comment, sleep_guide, age_kick, parent_message } = data;

  // daily: 백엔드 응답 ({ day, sleep_h, restless_min } 또는 { date, sleep_min, restless_min })
  // daily_stats: 더미 데이터 형태 ({ day, sleep_h, restless_min })
  // 모두 지원
  const dailyRows: Array<{ day: string; sleepMin: number; restlessMin: number }> = [];
  const parseDailyItem = (d: any): { day: string; sleepMin: number; restlessMin: number } => {
    const dayLabel = d.day || (d.date ? new Date(d.date).toLocaleDateString('ko-KR', { weekday: 'short' }).replace('요일', '') : '-');
    // sleep_h(시간) 또는 sleep_min(분) 둘 다 처리
    const sleepMin = d.sleep_min != null
      ? d.sleep_min
      : d.sleep_h != null
        ? Math.round(d.sleep_h * 60)
        : 0;
    const restlessMin = d.restless_min ?? 0;
    return { day: dayLabel, sleepMin, restlessMin };
  };
  if (daily && daily.length) {
    daily.forEach((d: any) => dailyRows.push(parseDailyItem(d)));
  } else if (daily_stats && daily_stats.length) {
    daily_stats.forEach((d: any) => dailyRows.push(parseDailyItem(d)));
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
    layout: { padding: { top: 10, bottom: 10, left: 12, right: 12 } },
    scales: {
      r: {
        min: 0, max: 100,
        ticks: { display: false },
        grid: { color: chartColors.gridLight },
        pointLabels: { font: { size: 9, family: 'Noto Sans KR', weight: '600' }, color: chartColors.textDark },
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
    container: { maxWidth: contentMaxWidth, width: '100%', margin: '0 auto', background: 'var(--bg-color)', display: 'flex', flexDirection: 'column' },
    pageBox: { padding: '32px 24px', display: 'flex', flexDirection: 'column', gap: 24 },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: 20, borderBottom: '1px solid var(--black)' },
    brandName: { fontFamily: 'Inter, sans-serif', fontSize: 18, fontWeight: 500, color: 'var(--black)', letterSpacing: 2, textTransform: 'uppercase' as const, lineHeight: 1.2 },
    brandSub: { fontSize: 9, color: 'var(--gray-mut)', marginTop: 4, fontFamily: 'Inter, sans-serif', textTransform: 'uppercase' as const, letterSpacing: 1 },
    headerInfo: { textAlign: 'right' as const },
    headerMain: { fontSize: 13, fontWeight: 500, color: 'var(--black)', letterSpacing: -0.3 },
    headerSub: { fontSize: 10, color: 'var(--gray-mut)', marginTop: 6, fontFamily: 'Inter, sans-serif', textTransform: 'uppercase' as const, letterSpacing: 0.5 },
    secTitle: { fontFamily: 'Inter, sans-serif', fontSize: 11, fontWeight: 600, color: 'var(--gray-mut)', textTransform: 'uppercase' as const, letterSpacing: 1.5, marginBottom: 12, borderBottom: '1px solid var(--gray-lt)', paddingBottom: 8 },
    compactStats: { display: 'flex', flexDirection: 'column' as const, gap: 8, marginBottom: 20 },
    cStatRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', background: 'var(--surface)', borderRadius: 8, gap: 8 },
    cStatLabel: { fontFamily: 'Inter, sans-serif', fontSize: 9, color: 'var(--gray-dark)', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: 0.8, flexShrink: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const },
    cStatValue: { fontFamily: 'Inter, sans-serif', fontSize: 14, fontWeight: 500, color: 'var(--black)', flexShrink: 0, whiteSpace: 'nowrap' as const },
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

  const pageOne = (
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
                    {['요일', '수면', '뒤척임', '호흡수'].map(h => (
                      <th key={h} style={{ fontFamily: 'Inter', fontWeight: 500, color: 'var(--gray-mut)', textTransform: 'uppercase', letterSpacing: 1, fontSize: 10, padding: '12px 8px', borderBottom: '1px solid var(--black)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dailyRows.map((row, i) => (
                    <tr key={i}>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Noto Sans KR', fontWeight: 500, color: 'var(--gray-dark)' }}>{row.day}</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>{fmtMin(row.sleepMin)}</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>{row.restlessMin}분</td>
                      <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--gray-lt)', fontFamily: 'Inter', fontWeight: 400 }}>{breath?.breath_avg ?? '-'}</td>
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
  );

  const middleAdBanner = (
    <AdBanner
      tag="MOM-I"
      title="맘아이 카메라로 수면을 기록하세요"
      description="설치 한 번으로 호흡·체온·뒤척임을 자동 측정. 매주 AI 리포트로 아이 수면을 한눈에 확인하세요."
      imageUrl="https://www.mom-i.com/img/main01_img_pc.png"
      linkUrl="https://www.mom-i.com/"
    />
  );

  const pageTwoContent = (
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

          {/* 부모 응원 메시지 */}
          {parent_message && (
            <div style={{ padding: '16px 20px', background: 'var(--accent-1-lt)', borderRadius: 12, borderLeft: '4px solid var(--accent-1)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-1)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>이번 주 응원 메시지</div>
              <div style={{ fontSize: 13, color: 'var(--black)', lineHeight: 1.7 }}>{parent_message}</div>
            </div>
          )}

          {/* Weekly Tips — 추후 백엔드 연동 예정, 현재 미노출 */}
        </div>
      </div>
  );

  const footer = (
    <div style={S.footer}>
      <span>© 2026 MOM-I INTELLIGENCE. ALL RIGHTS RESERVED.</span>
      {meta?.generated && <span>ISSUED: {meta.generated}</span>}
    </div>
  );

  if (mode === 'split') {
    return (
      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '20px 16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20, alignItems: 'start' }}>
          <div style={{ ...S.container, maxWidth: 'none', border: '1px solid var(--gray-lt)', borderRadius: 12, overflow: 'hidden' }}>
            {pageOne}
            <div style={{ padding: '0 24px 24px' }}>
              {middleAdBanner}
            </div>
          </div>
          <div style={{ ...S.container, maxWidth: 'none', border: '1px solid var(--gray-lt)', borderRadius: 12, overflow: 'hidden' }}>
            {pageTwoContent}
          </div>
        </div>
        <div style={{ ...S.container, maxWidth: 'none', marginTop: 12, border: '1px solid var(--gray-lt)', borderRadius: 12, overflow: 'hidden' }}>
          {footer}
        </div>
      </div>
    );
  }

  return (
    <div className="side-ad-container">
      {!hideSideAds && (
        <div className="side-ad" style={{ zIndex: 10 }}>
          <StickyWrapper>
            <AdBanner
              layout="vertical"
              tag="MOM-I"
              title="맘아이 카메라"
              description="호흡·체온·뒤척임을 실시간으로 감지하는 AI 수면 카메라"
              imageUrl="https://www.mom-i.com/img/main06_img1.jpg"
              linkUrl="https://www.mom-i.com/"
            />
          </StickyWrapper>
        </div>
      )}

      <div style={{ ...S.container, margin: 0, padding: '20px 0' }}>
        {pageOne}
        <div style={S.pageBox}>
          {middleAdBanner}
        </div>
        {pageTwoContent}
        {footer}
      </div>

      {!hideSideAds && (
        <div className="side-ad" style={{ zIndex: 10 }}>
          <StickyWrapper>
            <AdBanner
              layout="vertical"
              tag="MOM-I"
              title="지금 바로 시작해보세요"
              description="맘아이 카메라 하나로 아이 수면 걱정 끝"
              imageUrl="https://www.mom-i.com/img/main10_img1.jpg"
              linkUrl="https://www.mom-i.com/"
            />
          </StickyWrapper>
        </div>
      )}
    </div>
  );
};

export default ReportView;
