import { useEffect, useState, type CSSProperties } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

interface DevCareData {
  id: number;
  type: string;
  age_months: number;
  age_weeks: number | null;
  age_label: string;
  wonder_weeks_leap: number | null;
  is_sleep_regression: boolean;
  dev_status: string;
  sleep_activities: string[];
  vaccination: string;
  separation_sleep_guide: string;
}

interface Props {
  ageMonths?: number;
  ageWeeks?: number;
  childName?: string;
  apiBase?: string;
}

/* ─── 색상 토큰 ─────────────────────────────────── */
const C = {
  bgWarm:       '#EDE9E0',
  bgLeap:       '#EDE9E0',
  borderLeap:   '#C4A882',
  bgRegress:    '#EDE9E0',
  borderRegress:'#C4A882',
  bgActivity:   '#EDE9E0',
  borderActivity:'rgba(42,36,32,0.10)',
  bgVacc:       '#EDE9E0',
  borderVacc:   '#A8BBA0',
  textPrimary:  '#2A2420',
  textSecond:   '#7A6E64',
  textLeap:     '#7A5A00',
  textRegress:  '#7A3A00',
  textVacc:     '#1A3A7A',
  green:        '#3D7A5C',
  amber:        '#C4956A',
  stepBg:       '#5C7A6B',
  stepText:     '#FFFFFF',
  progressBg:   'rgba(42,36,32,0.08)',
  progressFill: '#5C7A6B',
  sectionLabel: '#6B7E8F',
  border:       'rgba(42,36,32,0.10)',
  surface:      '#EDE9E0',
};

/* 4개월(16주)~36개월 전체 범위에서 현재 위치 % */
function calcProgress(ageMonths: number): number {
  return Math.min(100, Math.max(0, ((ageMonths - 4) / (36 - 4)) * 100));
}

/* age_label에서 이모지와 "원더윅스" 관련 텍스트 제거 */
function cleanAgeLabel(label: string): string {
  return label
    .replace(/★|☆|🌙|💛|🌀|✨|⭐|🌟/g, '')
    .replace(/\s*원더윅스.*/g, '')
    .trim()
    .replace(/\s+/g, ' ');
}

export default function DevCareSection({ ageMonths, ageWeeks, childName = '아기', apiBase = API_BASE }: Props) {
  const [data, setData] = useState<DevCareData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ageMonths && !ageWeeks) return;

    setLoading(true);
    setError('');

    const params = new URLSearchParams();
    if (ageWeeks)       params.set('age_weeks', String(ageWeeks));
    else if (ageMonths) params.set('age_months', String(ageMonths));

    fetch(`${apiBase}/api/v1/dev-care?${params}`)
      .then(r => {
        if (!r.ok) throw new Error(r.status === 404 ? 'not_found' : 'error');
        return r.json();
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [ageMonths, ageWeeks, apiBase]);

  if (loading) return <div style={s.skeleton} />;
  if (error === 'not_found' || (!loading && !data)) return null;
  if (error) return null;
  if (!data) return null;

  const progress = calcProgress(data.age_months);
  const hasLeap = data.wonder_weeks_leap !== null;
  const hasVacc = Boolean(data.vaccination)
    && !data.vaccination.includes('해당 없음')
    && !data.vaccination.includes('없음')
    && !data.vaccination.startsWith('이번 달');

  return (
    <div style={s.wrap}>
      {/* ── 헤더: 성장 스냅샷 ── */}
      <div style={s.header}>
        <div style={s.headerTop}>
          <div>
            <span style={s.sectionLabel}>발달 케어</span>
            <h3 style={s.headerTitle}>{childName} · {cleanAgeLabel(data.age_label)}</h3>
          </div>
          <div style={s.badges}>
            {hasLeap && (
              <span style={s.badgeLeap}>발달 도약기 {data.wonder_weeks_leap}단계</span>
            )}
            {data.is_sleep_regression && (
              <span style={s.badgeRegress}>수면 퇴행 시기</span>
            )}
          </div>
        </div>

        {/* 성장 타임라인 바 */}
        <div style={s.timelineWrap}>
          <span style={s.timelineLabel}>4M</span>
          <div style={s.timelineTrack}>
            <div style={{ ...s.timelineFill, width: `${progress}%` }} />
            <div style={{ ...s.timelineMarker, left: `${progress}%` }}>
              <div style={s.markerDot} />
              <span style={s.markerLabel}>{data.age_months}M</span>
            </div>
          </div>
          <span style={s.timelineLabel}>36M</span>
        </div>

        {/* 수면 퇴행 알림 */}
        {data.is_sleep_regression && (
          <div style={s.regressAlert}>
            <p style={s.regressText}>
              이 시기 수면 퇴행은 <strong>정상 발달 신호</strong>예요.
              {childName}가 새로운 능력을 익히느라 뇌가 바쁜 거랍니다.
            </p>
          </div>
        )}

        {/* 발달 도약기 설명 */}
        {hasLeap && (
          <div style={s.leapAlert}>
            <p style={s.leapText}>
              이 시기는 아기의 뇌가 빠르게 성장하는 <strong>발달 도약기</strong>예요.
              평소보다 칭얼거림이 늘고 수면이 불규칙할 수 있습니다.
            </p>
          </div>
        )}
      </div>

      {/* ── 수면 도움 놀이 ── */}
      <div style={s.activitiesWrap}>
        <p style={s.activitiesLabel}>이번 주 수면 도움 놀이</p>
        <div style={s.activityList}>
          {data.sleep_activities.map((act, i) => (
            <div key={i} style={s.activityRow}>
              <span style={s.activityStep}>{i + 1}</span>
              <p style={s.activityText}>{act}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── 예방접종 (있을 때만) ── */}
      {hasVacc && (
        <div style={{ ...s.vaccCard, borderRadius: 12, padding: '0.9rem 1rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: C.textVacc, margin: 0 }}>예방접종</p>
          <p style={{ ...s.bottomCardText, color: C.textVacc }}>
            {data.vaccination}
          </p>
        </div>
      )}
    </div>
  );
}

const s: Record<string, CSSProperties> = {
  wrap: {
    fontFamily: "'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  skeleton: {
    height: 200,
    background: C.progressBg,
    borderRadius: 12,
    animation: 'pulse 1.5s ease-in-out infinite',
  },

  /* 헤더 */
  header: {
    background: C.bgWarm,
    border: `0.5px solid ${C.border}`,
    borderRadius: 12,
    padding: '1rem 1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: 8,
  },
  sectionLabel: {
    display: 'block',
    fontSize: 10,
    fontWeight: 500,
    color: C.sectionLabel,
    letterSpacing: '0.07em',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 500,
    color: C.textPrimary,
    margin: 0,
    lineHeight: 1.3,
  },
  badges: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    alignItems: 'flex-start',
    paddingTop: 4,
  },
  badgeLeap: {
    background: C.bgLeap,
    border: `0.5px solid ${C.borderLeap}`,
    color: C.textLeap,
    fontSize: 11,
    fontWeight: 500,
    padding: '3px 9px',
    borderRadius: 20,
    whiteSpace: 'nowrap',
  },
  badgeRegress: {
    background: C.bgRegress,
    border: `0.5px solid ${C.borderRegress}`,
    color: C.textRegress,
    fontSize: 11,
    fontWeight: 500,
    padding: '3px 9px',
    borderRadius: 20,
    whiteSpace: 'nowrap',
  },

  /* 타임라인 */
  timelineWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  timelineLabel: {
    fontSize: 10,
    color: C.textSecond,
    flexShrink: 0,
    fontVariantNumeric: 'tabular-nums',
  },
  timelineTrack: {
    flex: 1,
    height: 6,
    background: C.progressBg,
    borderRadius: 3,
    position: 'relative',
  },
  timelineFill: {
    height: '100%',
    background: C.progressFill,
    borderRadius: 3,
  },
  timelineMarker: {
    position: 'absolute',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
  },
  markerDot: {
    width: 12,
    height: 12,
    borderRadius: '50%',
    background: C.progressFill,
    border: '2px solid #FAF7F0',
    boxShadow: '0 0 0 2px ' + C.progressFill,
    marginTop: 3,
  },
  markerLabel: {
    fontSize: 10,
    fontWeight: 600,
    color: C.progressFill,
    whiteSpace: 'nowrap',
  },

  /* 알림 배너 */
  regressAlert: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    background: C.bgRegress,
    border: `0.5px solid ${C.borderRegress}`,
    borderRadius: 8,
    padding: '8px 12px',
  },
  regressText: {
    fontSize: 12,
    color: C.textRegress,
    lineHeight: 1.6,
    margin: 0,
  },
  leapAlert: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    background: C.bgLeap,
    border: `0.5px solid ${C.borderLeap}`,
    borderRadius: 8,
    padding: '8px 12px',
  },
  leapText: {
    fontSize: 12,
    color: C.textLeap,
    lineHeight: 1.6,
    margin: 0,
  },

  /* 수면 활동 */
  activitiesWrap: {
    background: '#FFFFFF',
    border: `0.5px solid ${C.border}`,
    borderRadius: 12,
    padding: '1rem 1.25rem',
  },
  activitiesLabel: {
    fontSize: 10,
    fontWeight: 500,
    color: C.sectionLabel,
    letterSpacing: '0.07em',
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  activityList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  activityRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
  },
  activityStep: {
    flexShrink: 0,
    width: 22,
    height: 22,
    borderRadius: '50%',
    background: C.stepBg,
    color: C.stepText,
    fontSize: 11,
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  activityText: {
    fontSize: 13,
    color: C.textPrimary,
    lineHeight: 1.65,
    margin: 0,
  },

  /* 예방접종 */
  vaccCard: {
    background: C.bgVacc,
    border: `0.5px solid ${C.borderVacc}`,
  },
  bottomCardText: {
    fontSize: 12,
    lineHeight: 1.65,
    margin: 0,
  },
};
