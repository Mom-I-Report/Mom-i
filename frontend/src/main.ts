import './style.css';
import { mockData } from './data/mockData';

// 향후 백엔드 API 연동 시 아래 코드를 fetch 구조로 교체하면 됩니다.
// const response = await fetch('/api/reports/1');
// const DATA = await response.json();
const DATA = mockData;

// --- 유틸 함수 ---
function fmtMin(m: number) {
  const h = Math.floor(m / 60), mm = m % 60;
  return mm > 0 ? `${h}h ${mm}m` : `${h}h`;
}
function avgNum(arr: any[], key: string) {
  return arr.reduce((s, d) => s + d[key], 0) / arr.length;
}
function avgTime(arr: any[], key: string) {
  const mins = arr.map(d => {
    const [h, m] = d[key].split(':').map(Number);
    return h * 60 + m;
  });
  const avg = Math.round(mins.reduce((a, b) => a + b, 0) / mins.length);
  const h = Math.floor(avg / 60) % 24;
  const m = avg % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

// --- 렌더링 함수 ---
function renderReport() {
  const app = document.getElementById('app');
  if (!app) return;

  const d = DATA;
  const avgSleep = Math.round(avgNum(d.daily, 'sleep'));
  const avgTemp  = avgNum(d.daily, 'temp').toFixed(1);
  const avgBed   = avgTime(d.daily, 'bedtime');

  app.innerHTML = `
    <!-- 컨트롤 바 -->
    <div class="ctrl">
      <span>📄 Mom-i 수면 교육 가이드 리포트 미리보기</span>
      <button onclick="window.print()">🖨️ PDF 저장 / 인쇄</button>
    </div>

    <!-- A4 리포트 -->
    <div class="a4">

      <!-- 헤더 -->
      <div class="header">
        <div>
          <div class="brand-name">Mom-i</div>
          <div class="brand-sub">프리미엄 수면 교육 가이드</div>
        </div>
        <div class="header-info">
          <div class="header-main">${d.baby.name}이 (${d.baby.ageMonths}개월) — ${d.week.num}주차 가이드</div>
          <div class="header-sub">데이터: ${d.week.start} ~ ${d.week.end}</div>
        </div>
      </div>

      <!-- 데이터 섹션 (콤팩트 그리드) -->
      <div class="top-data-grid">
        <div class="compact-stats">
          <div class="c-stat-row">
            <span class="c-stat-icon">😴</span>
            <span class="c-stat-label">평균 수면</span>
            <span class="c-stat-value">${fmtMin(avgSleep)}</span>
          </div>
          <div class="c-stat-row mint">
            <span class="c-stat-icon">🌙</span>
            <span class="c-stat-label">평균 취침</span>
            <span class="c-stat-value">${avgBed}</span>
          </div>
          <div class="c-stat-row">
            <span class="c-stat-icon">🌡️</span>
            <span class="c-stat-label">평균 온도</span>
            <span class="c-stat-value">${avgTemp}°C</span>
          </div>
        </div>

        <div>
          <table class="compact-table">
            <thead>
              <tr>
                <th style="padding-left:14px; text-align:left;">요일</th>
                <th>수면 구간 (취침~기상)</th>
                <th>총 수면 시간</th>
                <th>뒤척임 (발생 시각)</th>
                <th>뒤척임 (횟수 / 총 시간)</th>
                <th>온도</th>
              </tr>
            </thead>
            <tbody>
              ${d.daily.map(day => `
                <tr>
                  <td class="td-day">${day.day}</td>
                  <td>${day.bedtime} ~ ${day.wake}</td>
                  <td>${fmtMin(day.sleep)}</td>
                  <td style="color:var(--slate); font-size:10px;">${day.tossTime}</td>
                  <td><span style="color:#D25E4A; font-weight:700;">${day.tossCnt}회</span> <span style="font-size:10.5px">(${day.tossMin}분)</span></td>
                  <td class="${day.temp >= 23 ? 'td-temp-high' : ''}">${day.temp}°</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- ✨ 핵심: 솔루션 -->
      <div class="ai-sol-wrap">
        <div class="ai-sol-title">${d.sleep_guide.title}</div>
        <div class="ai-sol-reason">${d.sleep_guide.reason}</div>
        
        <div class="ai-steps">
          ${d.sleep_guide.steps.map((step, idx) => `
            <div class="ai-step">
              <div class="step-num">${idx + 1}</div>
              <div class="step-text">${step}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- 📉 데이터 맞춤 분석 팁 -->
      <div class="data-tips-wrap">
        ${d.ai_comment.map(tip => `
          <div class="tip-box ${tip.type}">
            <div class="tip-icon">${tip.icon}</div>
            <div class="tip-content">
              <div class="tip-title">${tip.title}</div>
              <div class="tip-text">${tip.text}</div>
            </div>
          </div>
        `).join('')}
      </div>

      <!-- 💡 핵심: 월령별 케어 킥 -->
      <div class="kick-wrap">
        <div class="kick-icon">💡</div>
        <div class="kick-content">
          <div class="kick-title">${d.age_kick.title}</div>
          <div class="kick-text">${d.age_kick.text}</div>
        </div>
      </div>

      <!-- 광고 배너 -->
      <div class="ad">
        <div class="ad-tag">AD</div>
        <div>
          <div class="ad-main">👶 맘스홀릭 프리미엄 백색소음기</div>
          <div class="ad-sub">쉬닥법 성공률을 높여주는 맞춤 주파수 오디오 가이드 탑재</div>
        </div>
        <button class="ad-btn">자세히 보기</button>
      </div>

      <!-- 푸터 -->
      <div class="footer">
        <span>Mom-i © 2026 · 본 리포트의 가이드라인은 의학적 진단을 대체하지 않습니다.</span>
        <span>리포트 생성일: ${d.week.generated}</span>
      </div>

    </div>
  `;
}

renderReport();
