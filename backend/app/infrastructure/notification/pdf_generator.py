"""
pdf_generator.py — 수면 리포트 PDF 생성 (Playwright + Chromium)

프론트엔드와 동일한 디자인의 PDF를 생성한다.
- 모바일 버전: 390px 뷰포트
- PC 버전: 900px 뷰포트
두 버전 모두 A4 형식으로 저장.

폴백: Playwright 실패 시 fpdf2로 대체.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.report.schemas import GenerateReportResponse

logger = logging.getLogger(__name__)

# ── HTML 템플릿 빌더 ──────────────────────────────────────────────────────────

def _build_html(report: "GenerateReportResponse") -> str:
    s   = report.summary
    bt  = report.body_temp
    br  = report.breath

    # 일별 수면 바 차트 (최대값 기준 퍼센트)
    max_sleep = max((d.sleep_h for d in report.daily), default=1) or 1
    max_rest  = max((d.restless_min for d in report.daily), default=1) or 1

    daily_rows = ""
    for d in report.daily:
        sleep_pct = round(d.sleep_h / max_sleep * 100)
        rest_pct  = round(d.restless_min / max_rest * 100)
        daily_rows += f"""
        <div class="day-row">
          <span class="day-label">{d.day}</span>
          <div class="bar-wrap">
            <div class="bar bar-sleep" style="width:{sleep_pct}%"></div>
            <span class="bar-val">{d.sleep_h}h</span>
          </div>
          <div class="bar-wrap">
            <div class="bar bar-rest" style="width:{rest_pct}%"></div>
            <span class="bar-val">{d.restless_min}분</span>
          </div>
        </div>"""

    # AI 코멘트
    comments_html = ""
    for c in report.ai_comment:
        cls = "card-warn" if c.type == "caution" else "card-good"
        comments_html += f"""
        <div class="tip-card {cls}">
          <div class="tip-icon">{c.icon}</div>
          <div class="tip-body">
            <div class="tip-title">{c.title}</div>
            <div class="tip-text">{c.text}</div>
          </div>
        </div>"""

    # 수면 교육법
    guide_html = ""
    if report.sleep_guide:
        steps_html = "".join(
            f'<li class="guide-step">{step}</li>'
            for step in report.sleep_guide.steps
        )
        kick_html = f'<div class="kick-box">⚡ 오늘 바로: {report.sleep_guide.kick_action}</div>' \
                    if report.sleep_guide.kick_action else ""
        guide_html = f"""
        <div class="section">
          <div class="section-title">추천 수면 교육법</div>
          <div class="guide-card">
            <div class="guide-name">{report.sleep_guide.method_name}</div>
            <div class="guide-reason">{report.sleep_guide.reason}</div>
            <ol class="guide-steps">{steps_html}</ol>
            {kick_html}
          </div>
        </div>"""

    # 월령 발달
    age_kick_html = ""
    if report.age_kick:
        wonder = '<span class="wonder-badge">✨ 원더윅스</span>' if report.age_kick.is_wonder_weeks else ""
        age_kick_html = f"""
        <div class="section">
          <div class="section-title">이 시기 발달 이슈</div>
          <div class="dev-card">
            <div class="dev-title">{report.age_kick.title} {wonder}</div>
            <div class="dev-text">{report.age_kick.text}</div>
          </div>
        </div>"""

    # 부모 메시지
    message_html = ""
    if report.parent_message:
        message_html = f'<div class="parent-msg">{report.parent_message}</div>'

    # 호흡 정상 여부
    breath_status = "정상 범위" if br.is_normal else "⚠ 범위 이탈"
    breath_color  = "#24614A" if br.is_normal else "#A26038"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  @import url('file:///usr/share/fonts/truetype/nanum/NanumGothic.ttf');

  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: 'Nanum Gothic', 'NanumGothic', sans-serif;
    background: #F3F0E9;
    color: #1C1C1E;
    font-size: 14px;
    line-height: 1.6;
  }}

  /* ── 헤더 ─────────────────────────────── */
  .header {{
    background: #1C1C1E;
    color: #fff;
    padding: 24px 20px 20px;
    text-align: center;
  }}
  .header-logo {{ font-size: 11px; letter-spacing: 3px; opacity: 0.5; margin-bottom: 8px; }}
  .header-title {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .header-sub {{ font-size: 12px; opacity: 0.6; }}

  /* ── 레이아웃 ─────────────────────────── */
  .container {{ padding: 16px; max-width: 100%; }}
  .section {{ margin-bottom: 20px; }}
  .section-title {{
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #8E8E93;
    margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 1px solid rgba(0,0,0,0.08);
  }}

  /* ── 요약 카드 그리드 ─────────────────── */
  .summary-grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .stat-card {{
    flex: 1 1 calc(33% - 8px);
    background: #fff;
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    min-width: 90px;
  }}
  .stat-value {{ font-size: 22px; font-weight: 700; color: #24614A; }}
  .stat-label {{ font-size: 10px; color: #8E8E93; margin-top: 2px; }}

  /* ── 일별 바 차트 ─────────────────────── */
  .day-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 7px;
  }}
  .day-label {{ width: 24px; font-size: 11px; font-weight: 700; color: #3A3A3C; flex-shrink: 0; }}
  .bar-wrap  {{ flex: 1; display: flex; align-items: center; gap: 6px; }}
  .bar       {{ height: 8px; border-radius: 4px; min-width: 4px; transition: width 0.3s; }}
  .bar-sleep {{ background: #24614A; }}
  .bar-rest  {{ background: #A26038; opacity: 0.7; }}
  .bar-val   {{ font-size: 10px; color: #8E8E93; white-space: nowrap; flex-shrink: 0; }}
  .chart-legend {{
    display: flex; gap: 16px; margin-bottom: 10px; font-size: 11px; color: #8E8E93;
  }}
  .legend-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }}

  /* ── AI 코멘트 카드 ───────────────────── */
  .tip-card {{
    display: flex;
    gap: 12px;
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 8px;
  }}
  .card-good {{ background: #E8EDE4; }}
  .card-warn {{ background: #F0E8D8; }}
  .tip-icon  {{ font-size: 22px; flex-shrink: 0; line-height: 1; }}
  .tip-title {{ font-size: 13px; font-weight: 700; margin-bottom: 4px; }}
  .card-good .tip-title {{ color: #2E4A35; }}
  .card-warn .tip-title {{ color: #7A4F2A; }}
  .tip-text  {{ font-size: 12px; line-height: 1.5; }}
  .card-good .tip-text {{ color: #3D5C44; }}
  .card-warn .tip-text {{ color: #8B5E3C; }}

  /* ── 수면 교육법 ──────────────────────── */
  .guide-card {{
    background: #FAF8F3;
    border-radius: 12px;
    padding: 16px;
    border-left: 4px solid #24614A;
  }}
  .guide-name   {{ font-size: 15px; font-weight: 700; color: #2A2420; margin-bottom: 8px; }}
  .guide-reason {{ font-size: 12px; color: #4A5C50; margin-bottom: 12px; line-height: 1.5; }}
  .guide-steps  {{ padding-left: 18px; }}
  .guide-step   {{ font-size: 12px; color: #2A2420; margin-bottom: 6px; line-height: 1.5; }}
  .kick-box {{
    margin-top: 12px; padding: 10px 12px;
    background: #E5EFEB; border-radius: 8px;
    font-size: 12px; font-weight: 700; color: #24614A;
  }}

  /* ── 발달 이슈 ────────────────────────── */
  .dev-card {{
    background: #FAF8F3;
    border-radius: 12px;
    padding: 16px;
    border-left: 4px solid #8E8E93;
  }}
  .dev-title {{ font-size: 13px; font-weight: 700; color: #2A2420; margin-bottom: 6px; }}
  .dev-text  {{ font-size: 12px; color: #4A5C50; line-height: 1.5; }}
  .wonder-badge {{
    display: inline-block; font-size: 10px; background: #E8EDE4;
    color: #24614A; padding: 2px 8px; border-radius: 20px; margin-left: 6px;
    font-weight: 600;
  }}

  /* ── 호흡/체온 ────────────────────────── */
  .health-grid {{ display: flex; gap: 8px; }}
  .health-card {{
    flex: 1;
    background: #fff;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
  }}
  .health-val   {{ font-size: 18px; font-weight: 700; margin-bottom: 4px; }}
  .health-label {{ font-size: 10px; color: #8E8E93; }}
  .health-status{{ font-size: 11px; font-weight: 600; margin-top: 4px; }}

  /* ── 부모 메시지 ──────────────────────── */
  .parent-msg {{
    background: #E5EFEB;
    border-radius: 12px;
    padding: 16px;
    font-size: 13px;
    color: #2E4A35;
    line-height: 1.6;
    font-style: italic;
    text-align: center;
    margin-bottom: 20px;
  }}

  /* ── 푸터 ─────────────────────────────── */
  .footer {{
    text-align: center;
    font-size: 10px;
    color: #8E8E93;
    padding: 16px 0 24px;
    border-top: 1px solid rgba(0,0,0,0.06);
  }}

  /* ── 인쇄 최적화 ──────────────────────── */
  @media print {{
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-logo">MOM-I AI REPORT</div>
  <div class="header-title">주간 수면 리포트</div>
  <div class="header-sub">{report.week_label} &nbsp;·&nbsp; {str(report.generated_at)[:10]}</div>
</div>

<div class="container">

  <!-- 주간 요약 -->
  <div class="section">
    <div class="section-title">주간 요약</div>
    <div class="summary-grid">
      <div class="stat-card">
        <div class="stat-value">{s.avg_sleep_h}h</div>
        <div class="stat-label">평균 수면</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{s.avg_restless_min}분</div>
        <div class="stat-label">평균 뒤척임</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{s.cry_count}회</div>
        <div class="stat-label">울음 감지</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{s.temp_avg}°C</div>
        <div class="stat-label">실내 온도</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{s.db_max}dB</div>
        <div class="stat-label">최고 소음</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{s.month_sleep_h}h</div>
        <div class="stat-label">월간 평균 수면</div>
      </div>
    </div>
  </div>

  <!-- 일별 수면 -->
  <div class="section">
    <div class="section-title">일별 수면</div>
    <div class="chart-legend">
      <span><span class="legend-dot" style="background:#24614A"></span>수면 시간</span>
      <span><span class="legend-dot" style="background:#A26038"></span>뒤척임</span>
    </div>
    {daily_rows}
  </div>

  <!-- 호흡 / 체온 -->
  <div class="section">
    <div class="section-title">호흡 / 체온</div>
    <div class="health-grid">
      <div class="health-card">
        <div class="health-val" style="color:{breath_color}">{br.breath_avg}<span style="font-size:12px"> 회/분</span></div>
        <div class="health-label">평균 호흡수</div>
        <div class="health-status" style="color:{breath_color}">{breath_status}</div>
        <div class="health-label">{br.normal_range}</div>
      </div>
      <div class="health-card">
        <div class="health-val" style="color:{'#A26038' if bt.status != '정상' else '#24614A'}">{bt.body_temp_avg}°C</div>
        <div class="health-label">체온 상승 (델타)</div>
        <div class="health-status" style="color:{'#A26038' if bt.status != '정상' else '#24614A'}">{bt.status}</div>
      </div>
    </div>
  </div>

  <!-- AI 분석 -->
  <div class="section">
    <div class="section-title">AI 분석</div>
    {comments_html}
  </div>

  {guide_html}
  {age_kick_html}
  {message_html}

</div>

<div class="footer">
  맘아이 리포트 · 앱에서 더 자세한 분석을 확인하세요
</div>

</body>
</html>"""


# ── Playwright PDF 생성 ───────────────────────────────────────────────────────

async def _render_pdf(html: str, viewport_width: int) -> bytes:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_viewport_size({"width": viewport_width, "height": 1200})
        await page.set_content(html, wait_until="domcontentloaded")
        pdf = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()
        return pdf


async def generate_report_pdfs(report: "GenerateReportResponse") -> tuple[bytes, bytes]:
    """
    모바일(390px)과 PC(860px) 두 버전의 PDF를 동시에 생성해 반환한다.
    Returns: (mobile_pdf_bytes, pc_pdf_bytes)
    """
    html = _build_html(report)
    mobile_pdf, pc_pdf = await asyncio.gather(
        _render_pdf(html, viewport_width=390),
        _render_pdf(html, viewport_width=860),
    )
    return mobile_pdf, pc_pdf


# ── fpdf2 폴백 ────────────────────────────────────────────────────────────────

FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

def _fallback_pdf_sync(report: "GenerateReportResponse") -> bytes:
    """Playwright 실패 시 fpdf2로 간단한 PDF 생성."""
    from fpdf import FPDF
    s = report.summary
    pdf = FPDF()
    pdf.add_font("Nanum", "", FONT_PATH)
    pdf.add_font("Nanum", "B", FONT_PATH)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_font("Nanum", "B", 14)
    pdf.set_text_color(26, 26, 46)
    pdf.cell(0, 10, f"맘아이 수면 리포트 — {report.week_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Nanum", "", 11)
    pdf.ln(4)
    pdf.cell(0, 7, f"평균 수면: {s.avg_sleep_h}h  /  뒤척임: {s.avg_restless_min}분  /  울음: {s.cry_count}회", new_x="LMARGIN", new_y="NEXT")
    for c in report.ai_comment:
        pdf.ln(4)
        pdf.set_font("Nanum", "B", 10)
        pdf.cell(0, 6, f"{c.icon} {c.title}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Nanum", "", 9)
        pdf.multi_cell(0, 5, c.text)
    return bytes(pdf.output())


async def generate_report_pdf_fallback(report: "GenerateReportResponse") -> bytes:
    return await asyncio.to_thread(_fallback_pdf_sync, report)
