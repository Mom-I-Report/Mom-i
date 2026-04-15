import './style.css';
import {
  babyProfile,
  currentWeek,
  dailySleepData,
  weeklyStats,
  aiAnalysis,
  reportHistory,
  formatMinutes,
  getScoreColor,
  getScoreLabel,
} from './data/mockData.ts';

// ============================================================
// 라우터 (Hash-based SPA)
// ============================================================

type Route = 'dashboard' | 'report' | 'history';

let currentRoute: Route = 'dashboard';

function getRoute(): Route {
  const hash = window.location.hash.replace('#/', '');
  if (hash === 'report') return 'report';
  if (hash === 'history') return 'history';
  return 'dashboard';
}

function navigate(route: Route) {
  window.location.hash = `/${route}`;
}

// ============================================================
// 유틸 함수
// ============================================================

function minToPercent(minutes: number, max: number): number {
  return Math.min((minutes / max) * 100, 100);
}

// ============================================================
// 네비게이션 바
// ============================================================

function renderNav(active: Route): string {
  const items = [
    { route: 'dashboard' as Route, icon: '🏠', label: '홈' },
    { route: 'report' as Route, icon: '📊', label: '리포트' },
    { route: 'history' as Route, icon: '📅', label: '히스토리' },
  ];

  return `
    <nav class="bottom-nav">
      ${items.map(item => `
        <button
          class="nav-item nav-item-bg ${active === item.route ? 'active' : ''}"
          onclick="window.__navigate('${item.route}')"
          id="nav-${item.route}"
          aria-label="${item.label} 페이지"
        >
          <span class="nav-icon">${item.icon}</span>
          <span>${item.label}</span>
        </button>
      `).join('')}
    </nav>
  `;
}

// ============================================================
// 수면 타임라인 차트 (SVG 바 차트)
// ============================================================

function renderTimelineChart(): string {
  const maxMinutes = Math.max(...dailySleepData.map(d => d.totalMinutes));

  return `
    <div class="timeline-chart">
      ${dailySleepData.map(day => {
        const sleepPct = minToPercent(day.actualSleepMinutes, maxMinutes);
        const tossPct = minToPercent(day.tossingMinutes, maxMinutes);
        const scoreColor = getScoreColor(day.sleepScore);

        return `
          <div class="timeline-row">
            <span class="timeline-label">${day.date}</span>
            <div class="timeline-bar-track">
              <div class="timeline-bar-sleep" style="width: ${sleepPct}%"></div>
              <div class="timeline-bar-tossing" style="left: ${sleepPct}%; width: ${tossPct}%"></div>
            </div>
            <span class="timeline-score" style="color: ${scoreColor}">${day.sleepScore}</span>
          </div>
        `;
      }).join('')}
      <div class="timeline-legend">
        <div class="legend-item">
          <div class="legend-dot" style="background: linear-gradient(90deg, var(--primary), var(--primary-light))"></div>
          <span>실제 수면</span>
        </div>
        <div class="legend-item">
          <div class="legend-dot" style="background: var(--secondary-light)"></div>
          <span>뒤척임</span>
        </div>
      </div>
    </div>
  `;
}

// ============================================================
// 페이지: 대시보드 (홈)
// ============================================================

function renderDashboard(): string {
  const score = weeklyStats.avgScore;
  const scoreLabel = getScoreLabel(score);

  return `
    <div class="page page-enter" id="page-dashboard">
      <!-- Header -->
      <header class="page-header">
        <div class="header-logo">
          <span class="header-logo-moon">🌙</span>
          <span class="header-logo-text">Mom-i</span>
        </div>
        <div class="header-actions">
          <button class="icon-btn" aria-label="알림" title="알림">🔔</button>
          <button class="icon-btn" aria-label="프로필" title="프로필">👤</button>
        </div>
      </header>

      <!-- 인사말 -->
      <div class="greeting-section">
        <p class="greeting-text">안녕하세요,</p>
        <p class="greeting-main"><strong>${babyProfile.parentName} 님</strong>의 수면 리포트 📋</p>
      </div>

      <!-- 히어로 카드 (아이 정보 + 점수) -->
      <div class="section">
        <div class="hero-card">
          <span class="hero-card-emoji">🌙</span>
          <p class="hero-greeting">이번 주 우리 아이</p>
          <h1 class="hero-baby-name">${babyProfile.name}이</h1>
          <p class="hero-baby-age">${babyProfile.ageInMonths}개월 ·  ${currentWeek.startDate} ~ ${currentWeek.endDate}</p>
          <p class="hero-score-label">이번 주 수면 점수</p>
          <div class="hero-score-value">${score}<span>점</span></div>
          <div class="score-bar-track">
            <div class="score-bar-fill" style="width: ${score}%"></div>
          </div>
          <div class="score-badge">⭐ ${scoreLabel}</div>
        </div>
      </div>

      <!-- 이번 주 요약 -->
      <div class="section">
        <h2 class="section-title"><span>📈</span> 이번 주 요약</h2>
        <div class="stats-grid">
          <div class="stat-card purple">
            <span class="stat-icon">⏱️</span>
            <div class="stat-value">${formatMinutes(weeklyStats.avgTotalSleep)}</div>
            <div class="stat-label">평균 총 수면</div>
            <div class="stat-sub">권장: 14~16시간</div>
          </div>
          <div class="stat-card pink">
            <span class="stat-icon">😴</span>
            <div class="stat-value">${formatMinutes(weeklyStats.avgActualSleep)}</div>
            <div class="stat-label">평균 실제 수면</div>
            <div class="stat-sub">전주 대비 +0h 18m</div>
          </div>
          <div class="stat-card amber">
            <span class="stat-icon">🔄</span>
            <div class="stat-value">${weeklyStats.avgTossing}분</div>
            <div class="stat-label">평균 뒤척임</div>
            <div class="stat-sub">전주 대비 -12분</div>
          </div>
          <div class="stat-card green">
            <span class="stat-icon">🌡️</span>
            <div class="stat-value">${weeklyStats.avgTemp}°C</div>
            <div class="stat-label">평균 환경 온도</div>
            <div class="stat-sub">권장: 20~22°C</div>
          </div>
        </div>
      </div>

      <!-- Best / Worst Day -->
      <div class="section">
        <h2 class="section-title"><span>🏆</span> 이번 주 Best & Worst</h2>
        <div class="best-worst-row">
          <div class="bw-card best">
            <div class="bw-label">🏅 최고의 날</div>
            <div class="bw-day">${weeklyStats.bestDay.date} (${weeklyStats.bestDay.fullDate})</div>
            <div class="bw-score">점수 ${weeklyStats.bestDay.sleepScore}점 · ${formatMinutes(weeklyStats.bestDay.actualSleepMinutes)} 실수면</div>
          </div>
          <div class="bw-card worst">
            <div class="bw-label">😅 가장 힘든 날</div>
            <div class="bw-day">${weeklyStats.worstDay.date} (${weeklyStats.worstDay.fullDate})</div>
            <div class="bw-score">점수 ${weeklyStats.worstDay.sleepScore}점 · 뒤척임 ${weeklyStats.worstDay.tossingMinutes}분</div>
          </div>
        </div>
      </div>

      <!-- CTA -->
      <div class="section">
        <button class="cta-btn" id="btn-go-report" onclick="window.__navigate('report')">
          📊 주간 리포트 자세히 보기
          <span class="btn-arrow">→</span>
        </button>
      </div>

      <!-- 최근 리포트 미리보기 -->
      <div class="section">
        <h2 class="section-title"><span>📅</span> 최근 리포트</h2>
        ${reportHistory.slice(0, 2).map((r, i) => `
          <div class="history-item ${i === 0 ? 'current' : ''}" style="margin-bottom: 8px" onclick="window.__navigate('history')">
            <div class="history-week-badge">${r.week}</div>
            <div class="history-info">
              <div class="history-dates">${r.dates}</div>
              <div class="history-sleep">평균 수면 ${r.avgSleep}</div>
            </div>
            <div class="history-score-col">
              <span class="history-score" style="color: ${getScoreColor(r.score)}">${r.score}</span>
              <span class="history-trend ${r.trend === 'up' ? 'trend-up' : 'trend-down'}">
                ${r.trend === 'up' ? '↑ 상승' : '↓ 하락'}
              </span>
            </div>
          </div>
        `).join('')}
      </div>

      <div class="generated-at">리포트 생성: ${currentWeek.reportGeneratedAt} · Powered by Gemini 1.5 Flash</div>

      ${renderNav('dashboard')}
    </div>
  `;
}

// ============================================================
// 페이지: 주간 리포트 상세
// ============================================================

function renderReport(): string {
  return `
    <div class="page page-enter" id="page-report">
      <!-- 헤더 -->
      <div class="back-header">
        <button class="back-btn" onclick="window.__navigate('dashboard')">
          ← 홈
        </button>
        <span class="back-header-title">주간 리포트</span>
        <button class="share-btn" aria-label="공유">
          📤 공유
        </button>
      </div>

      <!-- 기간 배지 -->
      <div class="week-info-bar">
        <span class="week-range">📆 ${currentWeek.startDate} ~ ${currentWeek.endDate}</span>
        <span class="week-num-badge">${currentWeek.weekNum}주차</span>
      </div>

      <!-- 수면 타임라인 차트 -->
      <div class="section">
        <h2 class="section-title"><span>📊</span> 일별 수면 타임라인</h2>
        <div class="card">
          ${renderTimelineChart()}
        </div>
      </div>

      <!-- 핵심 지표 그리드 -->
      <div class="section">
        <h2 class="section-title"><span>📋</span> 핵심 지표</h2>
        <div class="stats-grid">
          <div class="stat-card purple">
            <span class="stat-icon">⏱️</span>
            <div class="stat-value">${formatMinutes(weeklyStats.avgTotalSleep)}</div>
            <div class="stat-label">평균 총 수면</div>
          </div>
          <div class="stat-card pink">
            <span class="stat-icon">😴</span>
            <div class="stat-value">${formatMinutes(weeklyStats.avgActualSleep)}</div>
            <div class="stat-label">평균 실제 수면</div>
          </div>
          <div class="stat-card amber">
            <span class="stat-icon">🔄</span>
            <div class="stat-value">${weeklyStats.avgTossing}분</div>
            <div class="stat-label">평균 뒤척임</div>
          </div>
          <div class="stat-card green">
            <span class="stat-icon">🌡️</span>
            <div class="stat-value">${weeklyStats.avgTemp}°C</div>
            <div class="stat-label">평균 환경 온도</div>
          </div>
        </div>
      </div>

      <!-- 일별 상세 테이블 -->
      <div class="section">
        <h2 class="section-title"><span>📅</span> 일별 상세 데이터</h2>
        <div class="card" style="padding: 0; overflow: hidden;">
          <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
            <thead>
              <tr style="background: var(--primary-bg);">
                <th style="padding: 10px 12px; text-align: left; color: var(--text-secondary); font-weight: 600; white-space: nowrap;">날짜</th>
                <th style="padding: 10px 8px; text-align: center; color: var(--text-secondary); font-weight: 600;">취침</th>
                <th style="padding: 10px 8px; text-align: center; color: var(--text-secondary); font-weight: 600;">기상</th>
                <th style="padding: 10px 8px; text-align: center; color: var(--text-secondary); font-weight: 600;">온도</th>
                <th style="padding: 10px 8px; text-align: center; color: var(--primary); font-weight: 700;">점수</th>
              </tr>
            </thead>
            <tbody>
              ${dailySleepData.map((day, i) => `
                <tr style="border-top: 1px solid var(--border-light); background: ${i % 2 === 0 ? 'white' : 'var(--bg)'}">
                  <td style="padding: 10px 12px; font-weight: 600; color: var(--text-primary);">
                    ${day.date} <span style="color: var(--text-muted); font-weight: 400;">${day.fullDate}</span>
                  </td>
                  <td style="padding: 10px 8px; text-align: center; font-family: var(--font-en); color: var(--text-secondary);">${day.bedtime}</td>
                  <td style="padding: 10px 8px; text-align: center; font-family: var(--font-en); color: var(--text-secondary);">${day.wakeTime}</td>
                  <td style="padding: 10px 8px; text-align: center; font-family: var(--font-en); color: ${day.temperature > 23 ? 'var(--caution-dark)' : 'var(--text-secondary)'};">${day.temperature}°</td>
                  <td style="padding: 10px 8px; text-align: center; font-family: var(--font-en); font-weight: 800; color: ${getScoreColor(day.sleepScore)};">${day.sleepScore}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- AI 분석 -->
      <div class="section">
        <h2 class="section-title"><span>🤖</span> AI 분석 코멘트</h2>
        <div class="ai-card">
          <div class="ai-header">
            <span class="ai-badge">✨ AI · Gemini</span>
          </div>
          <p class="ai-text">"${aiAnalysis.overallComment}"</p>
        </div>
      </div>

      <!-- 케어 팁 -->
      <div class="section">
        <h2 class="section-title"><span>💡</span> 이번 주 케어 팁</h2>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${aiAnalysis.tips.map(tip => `
            <div class="tip-card">
              <div class="tip-icon-wrap">${tip.icon}</div>
              <div class="tip-content">
                <div class="tip-title-row">
                  <span class="tip-title">${tip.title}</span>
                  <span class="tag ${tip.tagColor}">${tip.tag}</span>
                </div>
                <p class="tip-text">${tip.content}</p>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- 개월수 발달 가이드 -->
      <div class="section">
        <h2 class="section-title"><span>📚</span> 발달 가이드</h2>
        <div class="guidance-card">
          <div class="guidance-header">
            <div class="guidance-age-badge">${aiAnalysis.ageGuidance.month}M</div>
            <span class="guidance-title">${aiAnalysis.ageGuidance.title}</span>
          </div>
          <p class="guidance-text">${aiAnalysis.ageGuidance.content}</p>
        </div>
      </div>

      <!-- 광고 배너 -->
      <div class="section">
        <div class="ad-banner">
          <span class="ad-label">광고</span>
          <div class="ad-content">
            <div class="ad-title">👶 맘스홀릭 프리미엄 육아용품</div>
            <div class="ad-sub">7개월 아이를 위한 맞춤 육아 가이드</div>
          </div>
          <button class="ad-btn">자세히</button>
        </div>
      </div>

      <div class="generated-at">리포트 생성: ${currentWeek.reportGeneratedAt} · Powered by Gemini 1.5 Flash</div>

      ${renderNav('report')}
    </div>
  `;
}

// ============================================================
// 페이지: 히스토리
// ============================================================

function renderHistory(): string {
  return `
    <div class="page page-enter" id="page-history">
      <!-- Header -->
      <header class="page-header">
        <div class="header-logo">
          <span class="header-logo-moon">🌙</span>
          <span class="header-logo-text">Mom-i</span>
        </div>
        <div class="header-actions">
          <button class="icon-btn" aria-label="알림">🔔</button>
        </div>
      </header>

      <div class="section">
        <h2 class="section-title"><span>📅</span> ${babyProfile.name}이의 리포트 히스토리</h2>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; margin-top: -8px;">
          최근 ${reportHistory.length}주 기록 · 탭하면 리포트를 볼 수 있어요
        </p>

        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${reportHistory.map((r, i) => `
            <div class="history-item ${i === 0 ? 'current' : ''}" onclick="window.__navigate('report')" id="history-item-${i}">
              <div class="history-week-badge">${r.week}</div>
              <div class="history-info">
                <div class="history-dates">${r.dates}</div>
                <div class="history-sleep">평균 수면 ${r.avgSleep}</div>
              </div>
              <div class="history-score-col">
                <span class="history-score" style="color: ${getScoreColor(r.score)}">${r.score}</span>
                <span class="history-trend ${r.trend === 'up' ? 'trend-up' : r.trend === 'down' ? 'trend-down' : 'trend-same'}">
                  ${r.trend === 'up' ? '↑ 상승' : r.trend === 'down' ? '↓ 하락' : '→ 유지'}
                </span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- 점수 추이 (간단 시각화) -->
      <div class="section">
        <h2 class="section-title"><span>📈</span> 점수 추이</h2>
        <div class="card">
          <div style="display: flex; align-items: flex-end; gap: 10px; height: 100px; padding: 8px 0;">
            ${[...reportHistory].reverse().map((r, i) => {
              const heightPct = (r.score / 100) * 100;
              return `
                <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                  <span style="font-family: var(--font-en); font-size: 11px; font-weight: 700; color: ${getScoreColor(r.score)}">${r.score}</span>
                  <div style="width: 100%; background: var(--primary-bg); border-radius: 6px; height: 80px; position: relative; overflow: hidden;">
                    <div style="position: absolute; bottom: 0; left: 0; right: 0; height: ${heightPct}%; background: ${i === reportHistory.length - 1 ? 'linear-gradient(to top, var(--primary), var(--primary-light))' : 'var(--primary-bg)'}; border: ${i === reportHistory.length - 1 ? 'none' : '2px solid var(--primary-light)'}; border-radius: 6px; transition: height 0.8s ease;"></div>
                  </div>
                  <span style="font-size: 10px; color: var(--text-muted); text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 40px;" title="${r.week}">${r.week.replace('주차', 'W')}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>

      ${renderNav('history')}
    </div>
  `;
}

// ============================================================
// 앱 렌더러
// ============================================================

function render() {
  currentRoute = getRoute();
  const app = document.getElementById('app')!;

  let html = '';
  switch (currentRoute) {
    case 'report':
      html = renderReport();
      break;
    case 'history':
      html = renderHistory();
      break;
    default:
      html = renderDashboard();
  }

  app.innerHTML = `<div class="app-shell">${html}</div>`;
}

// ============================================================
// 전역 네비게이션 핸들러
// ============================================================

(window as any).__navigate = (route: Route) => {
  navigate(route);
};

// 라우트 변경 감지
window.addEventListener('hashchange', render);

// 초기 렌더링
render();
