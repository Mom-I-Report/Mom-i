// ============================================================
// Mom-i 더미 데이터 (Mock Data)
// 실제 백엔드 연동 전 UI/UX 프로토타입용
// ============================================================

export const babyProfile = {
  name: '민준',
  ageInMonths: 7,
  birthDate: '2025-09-10',
  parentName: '김지현',
  avatarEmoji: '🍼',
  cameraId: 'CAM-A1B2C3',
};

export const currentWeek = {
  startDate: '2026.04.09',
  endDate: '2026.04.15',
  weekNum: 4,
  reportGeneratedAt: '2026.04.15 오전 7:00',
};

export interface DailySleep {
  date: string;       // 요일
  fullDate: string;   // 날짜
  bedtime: string;    // 취침 시간
  wakeTime: string;   // 기상 시간
  totalMinutes: number;         // 총 수면 시간(분)
  actualSleepMinutes: number;   // 실제 수면 시간(분)
  tossingMinutes: number;       // 뒤척임 시간(분)
  temperature: number;          // 환경 온도(°C)
  noiseDb: number;              // 소음(dB)
  sleepScore: number;           // 수면 점수(0~100)
}

export const dailySleepData: DailySleep[] = [
  {
    date: '월', fullDate: '4/9',
    bedtime: '21:30', wakeTime: '06:45',
    totalMinutes: 795, actualSleepMinutes: 710, tossingMinutes: 85,
    temperature: 22.3, noiseDb: 35, sleepScore: 78,
  },
  {
    date: '화', fullDate: '4/10',
    bedtime: '21:00', wakeTime: '06:30',
    totalMinutes: 810, actualSleepMinutes: 745, tossingMinutes: 65,
    temperature: 22.1, noiseDb: 28, sleepScore: 88,
  },
  {
    date: '수', fullDate: '4/11',
    bedtime: '22:00', wakeTime: '06:30',
    totalMinutes: 750, actualSleepMinutes: 630, tossingMinutes: 120,
    temperature: 23.5, noiseDb: 48, sleepScore: 62,
  },
  {
    date: '목', fullDate: '4/12',
    bedtime: '21:15', wakeTime: '06:50',
    totalMinutes: 835, actualSleepMinutes: 780, tossingMinutes: 55,
    temperature: 21.8, noiseDb: 22, sleepScore: 92,
  },
  {
    date: '금', fullDate: '4/13',
    bedtime: '21:30', wakeTime: '06:20',
    totalMinutes: 770, actualSleepMinutes: 700, tossingMinutes: 70,
    temperature: 22.0, noiseDb: 30, sleepScore: 82,
  },
  {
    date: '토', fullDate: '4/14',
    bedtime: '21:00', wakeTime: '07:00',
    totalMinutes: 840, actualSleepMinutes: 785, tossingMinutes: 55,
    temperature: 21.5, noiseDb: 25, sleepScore: 93,
  },
  {
    date: '일', fullDate: '4/15',
    bedtime: '21:45', wakeTime: '06:30',
    totalMinutes: 765, actualSleepMinutes: 690, tossingMinutes: 75,
    temperature: 22.2, noiseDb: 33, sleepScore: 80,
  },
];

// 주간 통계 (computed)
const totalDays = dailySleepData.length;
export const weeklyStats = {
  avgTotalSleep: Math.round(dailySleepData.reduce((a, d) => a + d.totalMinutes, 0) / totalDays),
  avgActualSleep: Math.round(dailySleepData.reduce((a, d) => a + d.actualSleepMinutes, 0) / totalDays),
  avgTossing: Math.round(dailySleepData.reduce((a, d) => a + d.tossingMinutes, 0) / totalDays),
  avgTemp: parseFloat((dailySleepData.reduce((a, d) => a + d.temperature, 0) / totalDays).toFixed(1)),
  avgNoise: Math.round(dailySleepData.reduce((a, d) => a + d.noiseDb, 0) / totalDays),
  avgScore: Math.round(dailySleepData.reduce((a, d) => a + d.sleepScore, 0) / totalDays),
  bestDay: dailySleepData.reduce((best, d) => d.sleepScore > best.sleepScore ? d : best),
  worstDay: dailySleepData.reduce((worst, d) => d.sleepScore < worst.sleepScore ? d : worst),
};

// AI 분석 결과 (LLM 생성 텍스트 더미)
export const aiAnalysis = {
  overallComment:
    '민준이는 이번 주 전반적으로 균형 잡힌 수면 패턴을 보였어요! 수요일에 실내 온도가 23.5°C까지 올라 뒤척임이 늘었지만, 목요일에는 훌륭하게 회복했답니다. 7개월 아이의 권장 수면 시간(14~16시간)에는 조금 미치지 못하지만, 야간 수면의 연속성은 매우 양호해요 😊',
  tips: [
    {
      icon: '🌡️',
      title: '수면 환경 온도 관리',
      content:
        '수요일 실내 온도가 23.5°C로 높았을 때 뒤척임이 30% 증가했어요. 영유아 최적 수면 온도는 20~22°C입니다. 에어컨보다는 창문 환기와 얇은 이불 조합을 추천드려요.',
      tag: '주의',
      tagColor: 'caution',
    },
    {
      icon: '🌙',
      title: '취침 시간 일관성',
      content:
        '이번 주 평균 취침 시간은 21시 21분이에요. 7개월 아이에게는 21~21:30 사이의 일정한 취침 루틴이 수면의 질을 크게 높여줘요. 목욕 → 수유 → 독서 루틴을 30분 전부터 시작해보세요.',
      tag: '좋음',
      tagColor: 'good',
    },
    {
      icon: '🎵',
      title: '소음 환경',
      content:
        '평균 소음이 32dB로 아주 양호한 편이에요. 작은 화이트 노이즈 머신(40~50dB)을 활용하면 외부 소음 차단 효과로 뒤척임을 더욱 줄일 수 있어요.',
      tag: '양호',
      tagColor: 'good',
    },
  ],
  ageGuidance: {
    month: 7,
    title: '7개월 수면 발달 가이드',
    content:
      '7개월은 분리 불안이 시작되는 중요한 시기예요. 이 시기의 아이는 잠자리에서 부모를 찾을 수 있습니다. 일관된 침실 의식(Bedtime Routine)이 아이에게 안정감을 주고 독립적 수면 능력 발달에 도움이 돼요. 권장 수면 시간은 하루 14~16시간(낮잠 포함)입니다.',
  },
};

// 히스토리 (과거 리포트)
export interface ReportHistoryItem {
  week: string;
  dates: string;
  score: number;
  trend: 'up' | 'down' | 'same';
  avgSleep: string;
}

export const reportHistory: ReportHistoryItem[] = [
  { week: '4주차', dates: '4/9 ~ 4/15', score: 82, trend: 'up', avgSleep: '12h 49m' },
  { week: '3주차', dates: '4/2 ~ 4/8', score: 76, trend: 'up', avgSleep: '12h 25m' },
  { week: '2주차', dates: '3/26 ~ 4/1', score: 71, trend: 'down', avgSleep: '11h 58m' },
  { week: '1주차', dates: '3/19 ~ 3/25', score: 74, trend: 'up', avgSleep: '12h 10m' },
  { week: '지난달 4주차', dates: '3/12 ~ 3/18', score: 68, trend: 'down', avgSleep: '11h 43m' },
  { week: '지난달 3주차', dates: '3/5 ~ 3/11', score: 72, trend: 'up', avgSleep: '12h 02m' },
];

// 유틸 함수
export function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m.toString().padStart(2, '0')}m`;
}

export function getScoreColor(score: number): string {
  if (score >= 85) return 'var(--good)';
  if (score >= 70) return 'var(--primary)';
  return 'var(--caution)';
}

export function getScoreLabel(score: number): string {
  if (score >= 90) return '최우수';
  if (score >= 80) return '우수';
  if (score >= 70) return '양호';
  if (score >= 60) return '보통';
  return '주의';
}
