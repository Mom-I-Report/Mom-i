'use strict';

// ── 유틸 ──────────────────────────────────────────────────────────────────────
function fmtH(h) {
  if (h == null) return '-';
  const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
  return mm > 0 ? `${hh}h ${mm}m` : `${hh}h`;
}

function md2html(str) {
  return (str || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

// ── 차트 인스턴스 관리 (canvasId → Chart) ──────────────────────────────────────
const _charts = {};

function _destroyChart(id) {
  if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

// ── 레이더 차트 ───────────────────────────────────────────────────────────────
function _radarScores(summary, breath, bodyTemp) {
  const sleep  = Math.min(100, Math.round((summary?.avg_sleep_h     || 0) / 14 * 100));
  const stable = Math.max(0,   Math.round(100 - (summary?.avg_restless_min || 0) / 60 * 100));
  const bScore = breath?.is_normal ? 100 : 45;
  const tScore = { '정상': 100, '미열 주의': 60, '발열 의심': 20 }[bodyTemp?.status] ?? 100;
  return [sleep, stable, bScore, tScore];
}

function _initRadarChart(canvasId, rj) {
  _destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _charts[canvasId] = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['수면', '안정도', '호흡', '체온'],
      datasets: [{
        data: _radarScores(rj.summary, rj.breath, rj.body_temp),
        backgroundColor: 'rgba(124,58,237,0.12)',
        borderColor: '#7C3AED',
        borderWidth: 2,
        pointBackgroundColor: '#7C3AED',
        pointRadius: 3,
      }],
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { display: false },
          grid: { color: '#E9E3FF' },
          pointLabels: { font: { size: 9, family: 'Noto Sans KR', weight: '700' }, color: '#334155' },
        },
      },
      plugins: { legend: { display: false } },
      animation: { duration: 400 },
    },
  });
}

// ── 막대 차트 ──────────────────────────────────────────────────────────────────
function _initBarChart(canvasId, daily) {
  _destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx || !daily.length) return;
  _charts[canvasId] = new Chart(ctx, {
    data: {
      labels: daily.map(d => d.day),
      datasets: [
        {
          type: 'bar',
          label: '수면 (시간)',
          data: daily.map(d => d.sleep_h),
          backgroundColor: 'rgba(124,58,237,0.75)',
          borderRadius: 5,
          yAxisID: 'y',
          order: 2,
        },
        {
          type: 'line',
          label: '뒤척임 (분)',
          data: daily.map(d => d.restless_min),
          borderColor: '#10B981',
          backgroundColor: 'rgba(16,185,129,0.1)',
          borderWidth: 2,
          pointBackgroundColor: '#10B981',
          pointRadius: 4,
          tension: 0.3,
          yAxisID: 'y2',
          order: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y:  { position: 'left',  min: 0, ticks: { font: { size: 10 }, callback: v => v + 'h' },   grid: { color: '#F1F5F9' } },
        y2: { position: 'right', min: 0, ticks: { font: { size: 10 }, callback: v => v + '분' }, grid: { drawOnChartArea: false } },
        x:  { ticks: { font: { size: 11, family: 'Noto Sans KR', weight: '700' } } },
      },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { font: { size: 11, family: 'Noto Sans KR' }, boxWidth: 12, padding: 10 } },
      },
    },
  });
}

// ── 리포트 본문 렌더링 ─────────────────────────────────────────────────────────
// container : DOM 요소 (innerHTML 교체됨)
// rj        : report_json { summary, breath, body_temp, daily, trend, ai_comment, sleep_guide, age_kick }
// opts      : { radarId, barId, showTrend }
function renderReportBody(container, rj, opts) {
  const radarId   = opts?.radarId   || 'radarChart';
  const barId     = opts?.barId     || 'barChart';
  const showTrend = opts?.showTrend ?? false;

  const summary    = rj.summary    || {};
  const breath     = rj.breath     || {};
  const bodyTemp   = rj.body_temp  || {};
  const daily      = rj.daily      || [];
  const trend      = rj.trend      || null;
  const aiComment  = rj.ai_comment  || [];
  const sleepGuide = rj.sleep_guide || null;
  const ageKick    = rj.age_kick    || null;

  const tempColor = { '정상': 'mint', '미열 주의': 'amber', '발열 의심': '' }[bodyTemp.status] || '';

  function trendBadge(val, unit) {
    if (!showTrend || val == null || val === 0) return '';
    const sign  = val > 0 ? '+' : '';
    const color = val > 0 ? '#10B981' : val < 0 ? '#DC2626' : '#64748B';
    return `<span style="font-size:10px;color:${color};margin-left:4px">${sign}${val}${unit}</span>`;
  }

  container.innerHTML = `
    <div>
      <div class="section-label">주간 요약</div>
      <div class="overview-row">
        <div class="radar-wrap"><canvas id="${radarId}"></canvas></div>
        <div class="stat-stack">
          <div class="c-stat-row">
            <span class="c-stat-icon">😴</span>
            <span class="c-stat-label">평균 수면</span>
            <span class="c-stat-value">${fmtH(summary.avg_sleep_h)}${trendBadge(trend?.sleep_vs_last_week, 'h')}</span>
          </div>
          <div class="c-stat-row">
            <span class="c-stat-icon">🔄</span>
            <span class="c-stat-label">뒤척임</span>
            <span class="c-stat-value">${summary.avg_restless_min ?? '-'}분${trendBadge(trend?.restless_vs_last_week, '분')}</span>
          </div>
          <div class="c-stat-row">
            <span class="c-stat-icon">😢</span>
            <span class="c-stat-label">울음 감지</span>
            <span class="c-stat-value">${summary.cry_count ?? '-'}회${trendBadge(trend?.cry_vs_last_week, '회')}</span>
          </div>
          <div class="c-stat-row mint">
            <span class="c-stat-icon">💨</span>
            <span class="c-stat-label">평균 호흡수</span>
            <span class="c-stat-value">${breath.breath_avg ?? '-'}회/분</span>
          </div>
          <div class="c-stat-row ${tempColor}">
            <span class="c-stat-icon">🌡️</span>
            <span class="c-stat-label">평균 체온 · ${bodyTemp.status ?? '-'}</span>
            <span class="c-stat-value">${bodyTemp.body_temp_avg ?? '-'}°C</span>
          </div>
        </div>
      </div>
    </div>

    ${daily.length ? `
    <div>
      <div class="section-label">일별 수면</div>
      <div class="daily-section"><canvas id="${barId}" height="160"></canvas></div>
    </div>` : ''}

    ${sleepGuide ? `
    <div class="ai-sol-wrap">
      <div class="ai-badge">✨ AI 추천 솔루션</div>
      <div class="ai-sol-title">${sleepGuide.title}</div>
      <div class="ai-sol-reason">${md2html(sleepGuide.reason)}</div>
      <div class="ai-steps">
        ${sleepGuide.steps.map((s, i) => `
          <div class="ai-step">
            <div class="step-num">${i + 1}</div>
            <div class="step-text">${md2html(s)}</div>
          </div>`).join('')}
      </div>
      ${sleepGuide.kick_action ? `
      <div class="kick-action-wrap">
        <span class="kick-action-icon">👉</span>
        <span class="kick-action-text">${md2html(sleepGuide.kick_action)}</span>
      </div>` : ''}
    </div>` : ''}

    ${aiComment.length ? `
    <div>
      <div class="section-label">AI 코멘트</div>
      <div class="data-tips-wrap">
        ${aiComment.map(t => `
          <div class="tip-box ${t.type}">
            <div class="tip-icon">${t.icon}</div>
            <div>
              <div class="tip-title">${t.title}</div>
              <div class="tip-text">${md2html(t.text)}</div>
            </div>
          </div>`).join('')}
      </div>
    </div>` : ''}

    ${ageKick ? `
    <div class="kick-wrap">
      <div class="kick-icon">💡</div>
      <div>
        <div class="kick-title">${ageKick.title}</div>
        <div class="kick-text">${md2html(ageKick.text)}</div>
      </div>
    </div>` : ''}
  `;

  _initRadarChart(radarId, rj);
  _initBarChart(barId, daily);
}
