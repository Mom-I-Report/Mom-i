/**
 * SleepReport — 주간 수면 리포트 (Chart.js + CSS-in-JS)
 *
 * Props:
 *   reportData  — EMTAKE 날짜키 JSON 또는 API GenerateReportResponse
 *   childName   — e.g. "은우"
 *   dateRange   — e.g. "2026년 5월 6일 – 11일"
 *   reportRef   — html2canvas 캡처 대상 ref
 */

import { useRef, useMemo, type RefObject, type ReactNode, type CSSProperties } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Filler,
  Tooltip,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale, LinearScale, BarElement,
  LineElement, PointElement, Filler, Tooltip
);

/* ─── 색상 토큰 ─────────────────────────────────────────── */
const C = {
  blue:       "#5C7A6B",
  teal:       "#7A9E8E",
  amber:      "#C4956A",
  amberDark:  "#7A4F2A",
  greenBg:    "#E8EDE4",
  greenBorder:"#A8BBA0",
  greenDark:  "#2E4A35",
  greenMid:   "#3D5C44",
  greenBadge: "#C0DD97",
  amberBg:    "#F0E8D8",
  amberBorder:"#C4A882",
  amberText:  "#633806",
  amberTagBg: "#FAC775",
  amberTagText:"#412402",
  textPrimary:"#2A2420",
  textSecond: "#7A6E64",
  textThird:  "#A89E94",
  neutral:    "#888780",
  surface:    "#EDE9E0",
  border:     "rgba(42,36,32,0.10)",
  white:      "#FAF8F3",
  pageBg:     "#F3F0E9",
  sectionOnDark: "#6B7E8F",
  borderOnDark: "rgba(26,43,60,0.12)",
  grid:       "rgba(136,135,128,0.12)",
  blueFill:   "rgba(74,144,184,0.08)",
  onBlue:     "#FFFFFF",
  onBlueMuted:"rgba(255,255,255,0.78)",
  onBlueFaint:"rgba(255,255,255,0.5)",
  onBlueBadge:"rgba(255,255,255,0.22)",
  tipBg:      "#EAE6DC",
  tipBorder:  "#C8C0B0",
};

/* ─── 유틸 함수 ─────────────────────────────────────────── */
function parseHM(s = "") {
  const m = s.match(/(\d+)h(\d+)m/);
  if (!m) return 0;
  return parseInt(m[1]) * 60 + parseInt(m[2]);
}

function fmtMin(totalMin: number) {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function timeToDecimalHour(t = "") {
  const [h, m] = t.split(":").map(Number);
  let hour = h + m / 60;
  if (hour < 12) hour += 24;
  return hour;
}

type DayRow = {
  dateKey: string;
  label: string;
  short: string;
  gs: number;
  pr: number;
  wu: number;
  eff: number;
  sessions: Array<{
    start: string;
    end: string;
    duration_min: number;
    wake_up: number;
  }>;
  env: Record<string, unknown>;
};

function processData(reportData: Record<string, unknown>): DayRow[] {
  const days = Object.keys(reportData).filter(k => k.match(/^\d{4}-\d{2}-\d{2}$/));
  const SHORT_LABELS = ["일","월","화","수","목","금","토"];

  return days.map((dateKey) => {
    const raw = reportData[dateKey] as Record<string, unknown>;
    const sd = (raw.SleepData ?? {}) as Record<string, unknown>;
    const gs = parseHM(String(sd.day_gs ?? ""));
    const pr = parseHM(String(sd.day_pr ?? ""));
    const wu = parseInt(String(sd.day_wakeup ?? "0"), 10) || 0;
    const eff = gs > 0 ? Math.round(((gs - pr) / gs) * 100) : 0;
    const dow = new Date(dateKey).getDay();

    return {
      dateKey,
      label: `${parseInt(dateKey.slice(8))}일(${SHORT_LABELS[dow]})`,
      short: SHORT_LABELS[dow],
      gs, pr, wu, eff,
      sessions: (sd.sessions as DayRow["sessions"]) ?? [],
      env: raw,
    };
  });
}

export interface SleepReportProps {
  reportData?: Record<string, unknown>;
  childName?: string;
  dateRange?: string;
  reportRef?: RefObject<HTMLDivElement | null> | null;
  /** false면 하단 정적 가이드라인 블록 숨김 (PC 우측 ReportView와 분리용) */
  showGuidelines?: boolean;
  /** 모바일 등 좁은 화면 — 한 눈에 보이도록 축소 */
  compact?: boolean;
  /** 분할 패널 안에 넣을 때 배경·maxWidth 제거 */
  embedded?: boolean;
  /** PC 좌측 패널 등 좁은 영역 — 차트 2열 대신 세로 배치 */
  splitPanel?: boolean;
}

export default function SleepReport({
  reportData = {},
  childName  = "아기",
  dateRange  = "",
  reportRef,
  showGuidelines = true,
  compact = false,
  embedded = false,
  splitPanel = false,
}: SleepReportProps) {
  const chartH = compact ? 88 : splitPanel ? 150 : 160;
  const tlH = compact ? 12 : 20;
  const effChartRef   = useRef(null);
  const trendChartRef = useRef(null);

  const data = useMemo(() => processData(reportData), [reportData]);
  const len = data.length || 1;
  const avgGs   = Math.round(data.reduce((a, d) => a + d.gs,  0) / len);
  const avgWu   = Math.round(data.reduce((a, d) => a + d.wu,  0) / len);
  const avgEff  = Math.round(data.reduce((a, d) => a + d.eff, 0) / len);
  const avgPr   = Math.round(data.reduce((a, d) => a + d.pr,  0) / len);
  const worstDay = data.length ? data.reduce((a, b) => (b.wu > a.wu ? b : a), data[0]) : null;

  const effChartData = {
    labels: data.map(d => d.short),
    datasets: [{
      data: data.map(d => d.eff),
      backgroundColor: data.map(d => d.eff >= 80 ? C.teal : C.amber),
      borderRadius: 4,
      borderSkipped: false,
    }],
  };
  const tickSm = compact ? 9 : 11;
  const chartLayoutPad = { padding: { top: 4, right: splitPanel ? 14 : 8, bottom: 4, left: 6 } };
  const effChartOpts: Record<string, unknown> = {
    responsive: true, maintainAspectRatio: false,
    layout: chartLayoutPad,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: { parsed: { y: number } }) => ctx.parsed.y + "%" } } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: tickSm }, color: C.textSecond } },
      y: { min: 0, max: 100, ticks: { stepSize: 25, callback: (v: number) => v + "%", font: { size: tickSm - 1 }, color: C.textSecond }, grid: { color: C.grid } },
    },
  };

  const trendChartData = {
    labels: data.map(d => d.short),
    datasets: [
      {
        label: "총수면(시간)",
        data: data.map(d => Math.round((d.gs / 60) * 10) / 10),
        borderColor: C.blue, backgroundColor: C.blueFill,
        tension: 0.35, pointRadius: 4, pointBackgroundColor: C.blue,
        fill: true, borderWidth: 2,
      },
      {
        label: "권장 하한(12h)",
        data: data.map(() => 12),
        borderColor: C.teal, borderDash: [5, 4], pointRadius: 0,
        borderWidth: 1.5, fill: false,
      },
    ],
  };
  const trendChartOpts: Record<string, unknown> = {
    responsive: true, maintainAspectRatio: false,
    layout: chartLayoutPad,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: { dataset: { label: string }; parsed: { y: number } }) => ctx.dataset.label + ": " + ctx.parsed.y + "h" } } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: tickSm }, color: C.textSecond } },
      y: { min: 4, max: 16, ticks: { stepSize: 4, callback: (v: number) => v + "h", font: { size: tickSm - 1 }, color: C.textSecond }, grid: { color: C.grid } },
    },
  };

  const latestEnv = data[data.length - 1]?.env ?? {};
  const indoor = (latestEnv.IndoorTemp ?? {}) as { Min?: number; Max?: number };
  const humidity = (latestEnv.Humidity ?? { Min: 0, Max: 0 }) as { Min: number; Max: number };
  const breathEnv = (latestEnv.Breath ?? {}) as { Min?: number; Max?: number };

  const tempAvg = ((indoor.Min ?? 20) + (indoor.Max ?? 22)) / 2;
  const tempScore = Math.round(Math.max(0, 100 - Math.abs(tempAvg - 20) * 8));
  const tempHint = (indoor.Max ?? 22) > 26 ? "취침 온도 다소 높음"
    : (indoor.Min ?? 20) < 16 ? "취침 온도 다소 낮음"
    : "적정 범위 유지";
  const tempOk = (indoor.Min ?? 20) >= 16 && (indoor.Max ?? 22) <= 26;

  const hasHumidity = (humidity.Min ?? 0) > 0 || (humidity.Max ?? 0) > 0;
  const humAvg = hasHumidity ? ((humidity.Min ?? 50) + (humidity.Max ?? 50)) / 2 : 50;
  const humScore = hasHumidity ? Math.round(Math.max(0, 100 - Math.max(0, humAvg - 60) * 2 - Math.max(0, 40 - humAvg) * 2)) : 0;

  const breathAvg = ((breathEnv.Min ?? 20) + (breathEnv.Max ?? 30)) / 2;
  const breathScore = Math.round(Math.max(0, 100 - Math.max(0, breathAvg - 35) * 4 - Math.max(0, 20 - breathAvg) * 4));

  const envItems = [
    {
      icon: "🌡️", label: "실내 온도",
      range: `${indoor.Min?.toFixed(1)}–${indoor.Max?.toFixed(1)}°C`,
      score: tempScore,
      color: C.blue,
      hint: tempHint,
      hintOk: tempOk,
    },
    {
      icon: "💧", label: "습도",
      range: hasHumidity ? (humidity.Min === humidity.Max ? `${humidity.Min}%` : `${humidity.Min}–${humidity.Max}%`) : "데이터 없음",
      score: humScore,
      color: C.teal,
      hint: !hasHumidity ? "센서 미지원" : ((humidity.Max ?? 0) - (humidity.Min ?? 0)) > 30 ? "습도 변동폭 큼" : "적정 습도 유지",
      hintOk: !hasHumidity ? true : !(((humidity.Max ?? 0) - (humidity.Min ?? 0)) > 30),
    },
    {
      icon: "🌬️", label: "호흡수",
      range: `${breathEnv.Min ?? 0}–${breathEnv.Max ?? 0} rpm`,
      score: breathScore,
      color: C.neutral,
      hint: (breathEnv.Max ?? 0) > 40 ? "호흡수 최대값 확인" : "정상 범위",
      hintOk: !((breathEnv.Max ?? 0) > 40),
    },
  ];

  const TL_START = 12;
  const TL_END   = 36;
  const TL_SPAN  = TL_END - TL_START;

  const pageStyle: CSSProperties = {
    ...s.page,
    ...(embedded ? { maxWidth: "100%", margin: 0, padding: compact ? "0 0 0.5rem" : "0 0 1rem", background: "transparent" } : {}),
    ...(compact && !embedded ? { maxWidth: "100%", padding: "0 4px 0.5rem" } : {}),
  };
  const grid4Style = compact || splitPanel
    ? { ...s.grid4, gridTemplateColumns: "repeat(2, 1fr)", gap: 6 }
    : s.grid4;
  const grid2Style = compact || splitPanel
    ? { ...s.grid2, gridTemplateColumns: "1fr", gap: 10 }
    : { ...s.grid2, gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 10 };
  const grid3Style = compact
    ? { ...s.grid3, gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }
    : splitPanel
      ? { ...s.grid3, gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }
      : s.grid3;

  const chartBoxStyle: CSSProperties = {
    position: "relative",
    height: chartH,
    width: "100%",
    minWidth: 0,
    maxWidth: "100%",
  };
  const cardStyle = (tight?: boolean): CSSProperties => ({
    ...(tight ? { ...s.card, padding: "0.65rem 0.75rem" } : s.card),
    minWidth: 0,
    maxWidth: "100%",
    overflow: "visible",
  });

  return (
    <div ref={reportRef} style={pageStyle}>
      <div style={compact ? s.headerCompact : s.header}>
        <div style={s.headerRow}>
          <div>
            <h1 style={compact ? { ...s.headerTitle, fontSize: 16 } : s.headerTitle}>{childName}의 수면 리포트</h1>
            <p style={compact ? { ...s.headerSub, fontSize: 11 } : s.headerSub}>{dateRange} · 주간 분석</p>
          </div>
          <span style={compact ? { ...s.statusBadge, fontSize: 10, padding: "3px 8px" } : s.statusBadge}>✓ NORMAL</span>
        </div>
        {!compact && <p style={s.brand}>MOM-I INTELLIGENCE · PREMIUM SLEEP DIAGNOSTICS</p>}
      </div>

      <SectionLabel compact={compact}>주간 핵심 요약</SectionLabel>
      <div style={grid4Style}>
        <SumCard label="평균 총수면"   value={fmtMin(avgGs)} sub={avgGs >= 600 ? "권장범위 근접" : "권장 12–14h"} ok={avgGs >= 600} />
        <SumCard label="평균 수면 효율" value={`${avgEff}%`} sub="순수면 / 총수면"     ok={avgEff >= 80} />
        <SumCard label="평균 각성 횟수" value={`${avgWu}회`} sub="일 평균"             ok={avgWu <= 10}  />
        <SumCard label="평균 뒤척임"   value={fmtMin(avgPr)} sub="총수면 대비"         ok={null} />
      </div>

      <Divider compact={compact} />

      <SectionLabel compact={compact}>일별 수면 타임라인</SectionLabel>
      <div style={s.card}>
        <div style={s.legend}>
          <span style={s.legendItem}><span style={{...s.legendDot, background: C.blue}} />야간수면</span>
          <span style={s.legendItem}><span style={{...s.legendDot, background: C.teal}} />낮잠</span>
          <span style={{ ...s.legendItem, color: C.amberDark }}>● 각성 횟수</span>
        </div>
        <div style={s.tlAxisRow}>
          <span style={{width: 28}} />
          <div style={s.tlAxisLabels}>
            {[12,15,18,20,22,24,2,4,6,8].map(h => (
              <span key={h} style={s.tlAxisTick}>{h < 24 ? h : h - 24}시</span>
            ))}
          </div>
          <span style={{width: 32}} />
        </div>
        {data.map(d => (
          <div key={d.dateKey} style={s.tlRow}>
            <span style={s.tlDayLabel}>{d.short}</span>
            <div style={{ ...s.tlBarArea, height: tlH }}>
              {d.sessions.map((sess, i) => {
                const sh  = timeToDecimalHour(sess.start);
                const left = Math.max(0, (sh - TL_START) / TL_SPAN * 100);
                const w    = Math.max(0.5, Math.min((sess.duration_min / (TL_SPAN * 60)) * 100, 100 - left));
                const isNight = sh >= 20 || sh < 12;
                return (
                  <div key={i} title={`${sess.start}–${sess.end} (${sess.duration_min}분, 각성 ${sess.wake_up}회)`}
                    style={{
                      position: "absolute", left: `${left.toFixed(1)}%`, width: `${w.toFixed(1)}%`,
                      height: "100%", background: isNight ? C.blue : C.teal, borderRadius: 2, top: 0,
                    }}
                  />
                );
              })}
            </div>
            <span style={{...s.tlWakeup, color: d.wu > 10 ? C.amberDark : C.textSecond}}>● {d.wu}회</span>
          </div>
        ))}
      </div>

      <Divider compact={compact} />

      <SectionLabel compact={compact}>수면 구성 &amp; 주간 트렌드</SectionLabel>
      <div style={grid2Style}>
        <div style={cardStyle(compact)}>
          <p style={compact ? { ...s.chartTitle, fontSize: 12 } : s.chartTitle}>수면 효율 (일별)</p>
          <p style={compact ? { ...s.chartSub, marginBottom: 6 } : s.chartSub}>뒤척임을 제외한 순수면 비율 · 80% 이상이면 양호</p>
          <div style={chartBoxStyle}>
            <Bar ref={effChartRef} data={effChartData} options={effChartOpts as object}
              aria-label="일별 수면 효율 막대 차트" />
          </div>
          <div style={{display:"flex", gap:12, marginTop:8}}>
            <span style={s.chartLegendItem}><span style={{...s.chartLegendDot, background: C.teal}} />80% 이상</span>
            <span style={s.chartLegendItem}><span style={{...s.chartLegendDot, background: C.amber}} />80% 미만</span>
          </div>
        </div>
        <div style={cardStyle(compact)}>
          <p style={compact ? { ...s.chartTitle, fontSize: 12 } : s.chartTitle}>일별 총수면 시간</p>
          <p style={compact ? { ...s.chartSub, marginBottom: 6 } : s.chartSub}>점선 아래로 내려가면 수면 부족 · 영아 권장 12–14시간</p>
          <div style={chartBoxStyle}>
            <Line ref={trendChartRef} data={trendChartData} options={trendChartOpts as object}
              aria-label="주간 수면시간 추이 라인 차트" />
          </div>
          <div style={{display:"flex", gap:12, marginTop:8}}>
            <span style={s.chartLegendItem}><span style={{...s.chartLegendDot, background: C.blue}} />총수면</span>
            <span style={s.chartLegendItem}>
              <span style={{...s.chartLegendDot, background: C.teal, borderStyle:"dashed", borderWidth:1, borderColor: C.teal}} />
              권장 하한
            </span>
          </div>
        </div>
      </div>

      <Divider compact={compact} />

      <SectionLabel compact={compact}>수면 환경 모니터링</SectionLabel>
      <div style={grid3Style}>
        {envItems.map(item => (
          <div key={item.label} style={s.card}>
            <span style={{fontSize: 20}}>{item.icon}</span>
            <p style={s.envName}>{item.label}</p>
            <p style={s.envRange}>{item.range}</p>
            <div style={s.envTrack}>
              <div style={{...s.envFill, width: `${Math.min(100, Math.max(0, item.score))}%`, background: item.color}} />
            </div>
            <p style={{...s.envHint, color: item.hintOk ? C.greenMid : C.amberDark}}>{item.hint}</p>
          </div>
        ))}
      </div>

      {showGuidelines && (
        <>
          <Divider compact={compact} />
          <SectionLabel compact={compact}>가이드라인 &amp; 인사이트</SectionLabel>
          <div style={s.guideGreen}>
            <p style={s.guideTitle}>
              이번 주 총평 &nbsp;
              <span style={s.badgeGreen}>정상</span>
            </p>
            <p style={s.guideText}>
              {childName}의 주간 평균 수면시간은 <strong>{fmtMin(avgGs)}</strong>이며,
              수면 효율은 평균 <strong>{avgEff}%</strong>로{" "}
              {avgEff >= 80 ? "안정적인 수준입니다." : "다소 낮은 편입니다."}{" "}
              낮잠을 포함한 총수면 패턴은 전반적으로 일관되게 유지되고 있습니다.
            </p>
            <span style={s.tagGreen}>수면 패턴 일관</span>
            <span style={s.tagGreen}>야간 수면 확보</span>
          </div>
          {worstDay && (
            <div style={{...s.guideAmber, marginTop: 10}}>
              <p style={s.guideTextAmber}>
                <strong>{worstDay.label}</strong>에 각성 횟수가 <strong>{worstDay.wu}회</strong>로
                이번 주 중 가장 높았습니다. 해당일 습도 범위(
                {(reportData[worstDay.dateKey] as Record<string, unknown> & { Humidity?: { Min?: number; Max?: number } })?.Humidity?.Min}–
                {(reportData[worstDay.dateKey] as Record<string, unknown> & { Humidity?: { Min?: number; Max?: number } })?.Humidity?.Max}%)가 평소보다 넓어
                수면 환경이 불안정했을 수 있습니다. 취침 전 실내 습도를
                40–60% 사이로 맞춰주시면 각성 횟수를 줄이는 데 도움이 됩니다.
              </p>
              <span style={s.tagAmber}>습도 관리 권장</span>
              <span style={s.tagAmber}>낮잠 시간 일정하게</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SectionLabel({ children, compact }: { children: ReactNode; compact?: boolean }) {
  return <p style={compact ? s.sectionLabelCompact : s.sectionLabel}>{children}</p>;
}

function Divider({ compact }: { compact?: boolean }) {
  return <hr style={compact ? s.dividerCompact : s.divider} />;
}

function SumCard({ label, value, sub, ok }: { label: string; value: string; sub: string; ok: boolean | null }) {
  const subColor = ok === null ? C.textSecond : ok ? C.greenMid : C.amberDark;
  return (
    <div style={s.sumCard}>
      <p style={s.sumLabel}>{label}</p>
      <p style={s.sumValue}>{value}</p>
      <p style={{...s.sumSub, color: subColor}}>{sub}</p>
    </div>
  );
}

const s: Record<string, CSSProperties> = {
  page: {
    fontFamily: "'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
    maxWidth: 720,
    margin: "0 auto",
    padding: "0 0 2rem",
    color: C.textPrimary,
    background: C.pageBg,
  },
  header: {
    background: C.blue,
    borderRadius: 12,
    padding: "1.25rem 1.5rem",
    marginBottom: "1rem",
  },
  headerCompact: {
    background: C.blue,
    borderRadius: 10,
    padding: "0.75rem 0.85rem",
    marginBottom: "0.65rem",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  headerTitle: {
    color: C.onBlue,
    fontSize: 20,
    fontWeight: 500,
    margin: "0 0 3px",
  },
  headerSub: {
    color: C.onBlueMuted,
    fontSize: 13,
    margin: 0,
  },
  statusBadge: {
    background: C.onBlueBadge,
    color: C.onBlue,
    fontSize: 11,
    fontWeight: 500,
    padding: "4px 10px",
    borderRadius: 20,
    whiteSpace: "nowrap",
    marginTop: 2,
  },
  brand: {
    color: C.onBlueFaint,
    fontSize: 11,
    marginTop: 10,
    letterSpacing: "0.06em",
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: 500,
    color: C.sectionOnDark,
    letterSpacing: "0.07em",
    textTransform: "uppercase",
    margin: "1.25rem 0 0.6rem",
  },
  sectionLabelCompact: {
    fontSize: 10,
    fontWeight: 500,
    color: C.sectionOnDark,
    letterSpacing: "0.07em",
    textTransform: "uppercase",
    margin: "0.65rem 0 0.4rem",
  },
  divider: {
    border: "none",
    borderTop: `0.5px solid ${C.borderOnDark}`,
    margin: "1.25rem 0",
  },
  dividerCompact: {
    border: "none",
    borderTop: `0.5px solid ${C.borderOnDark}`,
    margin: "0.65rem 0",
  },
  grid4: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 10,
  },
  grid2: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
  },
  grid3: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 10,
  },
  card: {
    background: C.white,
    border: `0.5px solid ${C.border}`,
    borderRadius: 12,
    padding: "1rem 1.25rem",
  },
  sumCard: {
    background: C.white,
    border: `0.5px solid ${C.border}`,
    borderRadius: 8,
    padding: "0.85rem 1rem",
  },
  sumLabel: { fontSize: 11, color: C.textSecond, marginBottom: 5 },
  sumValue: { fontSize: 20, fontWeight: 500, color: C.textPrimary, lineHeight: 1.1 },
  sumSub:   { fontSize: 11, marginTop: 4 },

  legend: { display: "flex", gap: 16, marginBottom: 10, flexWrap: "wrap" },
  legendItem: { display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.textSecond },
  legendDot: { display: "inline-block", width: 14, height: 8, borderRadius: 2 },

  tlAxisRow:    { display: "flex", alignItems: "center", gap: 8, paddingBottom: 4 },
  tlAxisLabels: { flex: 1, display: "flex", justifyContent: "space-between" },
  tlAxisTick:   { fontSize: 10, color: C.textThird },
  tlRow:        { display: "flex", alignItems: "center", gap: 8, marginBottom: 6 },
  tlDayLabel:   { fontSize: 11, color: C.textSecond, width: 20, textAlign: "right", flexShrink: 0 },
  tlBarArea:    { flex: 1, height: 20, background: C.surface, borderRadius: 3, position: "relative", overflow: "visible" },
  tlWakeup:     { fontSize: 11, width: 28, textAlign: "right", flexShrink: 0 },

  chartTitle:      { fontSize: 13, fontWeight: 500, color: C.textPrimary, marginBottom: 4 },
  chartSub:        { fontSize: 11, color: C.textSecond, marginBottom: 10 },
  chartLegendItem: { display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: C.textSecond },
  chartLegendDot:  { display: "inline-block", width: 10, height: 10, borderRadius: 2 },

  envName:  { fontSize: 11, color: C.textSecond, margin: "6px 0 3px" },
  envRange: { fontSize: 14, fontWeight: 500, color: C.textPrimary, marginBottom: 6 },
  envTrack: { height: 5, background: C.surface, borderRadius: 3, overflow: "hidden", marginBottom: 4 },
  envFill:  { height: "100%", borderRadius: 3 },
  envHint:  { fontSize: 10 },

  guideGreen: {
    background: C.greenBg,
    border: `0.5px solid ${C.greenBorder}`,
    borderRadius: 12,
    padding: "1rem 1.25rem",
  },
  guideTitle: {
    fontSize: 13, fontWeight: 500, color: C.greenDark,
    marginBottom: 6, display: "flex", alignItems: "center", gap: 8,
  },
  badgeGreen: {
    background: C.greenBadge, color: C.greenDark,
    fontSize: 11, padding: "2px 8px", borderRadius: 4,
  },
  guideText: { fontSize: 13, color: C.greenMid, lineHeight: 1.65, marginBottom: 10 },
  tagGreen: {
    display: "inline-block", background: C.greenBadge, color: C.greenDark,
    fontSize: 11, padding: "3px 9px", borderRadius: 4, marginRight: 5, marginBottom: 4,
  },
  guideAmber: {
    background: C.amberBg,
    border: `0.5px solid ${C.amberBorder}`,
    borderRadius: 12,
    padding: "1rem 1.25rem",
  },
  guideTextAmber: { fontSize: 13, color: C.amberText, lineHeight: 1.65, marginBottom: 8 },
  tagAmber: {
    display: "inline-block", background: C.amberTagBg, color: C.amberTagText,
    fontSize: 11, padding: "3px 9px", borderRadius: 4, marginRight: 5, marginBottom: 4,
  },
};
