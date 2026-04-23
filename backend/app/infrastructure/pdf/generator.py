"""
reportlab 기반 PDF 리포트 생성기
HTML 연동이 완성된 이후 PDF 출력 경로로 사용
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os

# ── 한글 폰트 등록 (Windows 기본 맑은 고딕 사용) ──
_FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
_FONT_REGISTERED = False

def _register_font():
    global _FONT_REGISTERED
    if not _FONT_REGISTERED and os.path.exists(_FONT_PATH):
        pdfmetrics.registerFont(TTFont("MalgunGothic", _FONT_PATH))
        _FONT_REGISTERED = True

BLUE   = colors.HexColor("#4f86f7")
LIGHT  = colors.HexColor("#eef3ff")
GRAY   = colors.HexColor("#888888")
BORDER = colors.HexColor("#e8edf5")


def _styles():
    _register_font()
    base = "MalgunGothic" if _FONT_REGISTERED else "Helvetica"

    return {
        "brand": ParagraphStyle("brand", fontName=base, fontSize=18, textColor=BLUE, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", fontName=base, fontSize=10, textColor=GRAY),
        "section": ParagraphStyle("section", fontName=base, fontSize=11, textColor=colors.HexColor("#444444"),
                                  spaceBefore=12, spaceAfter=6, fontWeight="bold"),
        "body": ParagraphStyle("body", fontName=base, fontSize=10, textColor=colors.HexColor("#333333"),
                               leading=16),
        "small": ParagraphStyle("small", fontName=base, fontSize=8, textColor=GRAY),
        "insight": ParagraphStyle("insight", fontName=base, fontSize=10, textColor=colors.HexColor("#333333"),
                                  leading=17, leftIndent=12),
    }


def generate_pdf(data: dict) -> bytes:
    """
    GenerateReportResponse 기반 data 예시 (baby_name 없음 — ser_no 식별):
    {
        "ser_no": "MT-00123",
        "week_label": "2026년 4월 2주차",
        "generated_at": "2026-04-14T10:00:00",
        "summary": {
            "avg_sleep_h": 9.2,
            "avg_restless_min": 18,
            "cry_count": 3,
            "leave_count": 1,
            "temp_avg": 23.1, "temp_max": 24.5, "temp_min": 21.8,
            "db_max": 62, "db_avg": 45
        },
        "daily": [
            {"day": "월", "sleep_h": 9.5, "restless_min": 20},
            ...  (7일치)
        ],
        "trend": {
            "sleep_vs_last_week": 0.3,
            "restless_vs_last_week": -5,
            "cry_vs_last_week": -1
        },  # 첫 주차이면 None
        "ai_comment": "이번 주 아기는 평균 9시간 이상의 안정된 수면을 보여주었습니다..."
    }

    NOTE: 이 모듈은 향후 PDF 출력 경로 구현을 위한 스켈레톤입니다.
    현재 API는 JSON으로 리포트를 반환하며, PDF 기능은 아직 라우터에 연결되어 있지 않습니다.
    연결 시 아래 필드 매핑을 참고하세요:
        data["summary"]["avg_sleep_h"]  →  avg_sleep_h
        data["daily"]                   →  daily_sleep (label → day 키 변경 필요)
        data["trend"]                   →  Optional, None 처리 필요
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )
    s = _styles()
    W = A4[0] - 40*mm  # 사용 가능 폭

    story = []

    # ── 헤더 ──
    header_data = [[
        Paragraph("Mom-i", s["brand"]),
        Paragraph(f"<b>아기 (SN: {data.get('ser_no', '')})</b><br/>{data['week_label']} | 생성일: {data.get('generated_at', '')[:10]}", s["body"]),
    ]]
    header_tbl = Table(header_data, colWidths=[W * 0.5, W * 0.5])
    header_tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, BLUE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 10))

    # ── 요약 카드 ──
    story.append(Paragraph("■ 이번 주 수면 요약", s["section"]))
    card_data = [[
        f"평균 수면\n{data['avg_sleep_h']}h",
        f"평균 뒤척임\n{data['avg_restless_min']}min",
        f"울음 이벤트\n{data['cry_count']}회",
        f"카메라 이탈\n{data['leave_count']}회",
    ]]
    card_tbl = Table(card_data, colWidths=[W / 4] * 4, rowHeights=42)
    card_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), LIGHT),
        ("BACKGROUND", (1, 0), (-1, 0), colors.HexColor("#f7f9fc")),
        ("TEXTCOLOR", (0, 0), (0, 0), BLUE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
        ("BOX", (0, 0), (0, 0), 0.5, BLUE),
        ("BOX", (1, 0), (-1, 0), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
    ]))
    story.append(card_tbl)
    story.append(Spacer(1, 12))

    # ── 일별 수면 바 (텍스트 표) ──
    story.append(Paragraph("■ 일별 수면 현황", s["section"]))
    days = data.get("daily_sleep", [])
    if days:
        bar_header = [d["label"] for d in days]
        bar_vals   = [f"{d['sleep_h']}h\n({d['restless_min']}min)" for d in days]
        bar_tbl = Table([bar_header, bar_vals], colWidths=[W / len(days)] * len(days), rowHeights=[18, 24])
        bar_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ff")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), BLUE),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("GRID",       (0, 0), (-1, -1), 0.3, BORDER),
        ]))
        story.append(bar_tbl)
    story.append(Spacer(1, 12))

    # ── 환경 지표 ──
    story.append(Paragraph("■ 수면 환경 지표", s["section"]))
    env_data = [[
        f"평균 온도\n{data['temp_avg']}°C",
        f"최고/최저 온도\n{data['temp_max']}° / {data['temp_min']}°",
        f"최대 소음\n{data['db_max']} dB",
    ]]
    env_tbl = Table(env_data, colWidths=[W / 3] * 3, rowHeights=40)
    env_tbl.setStyle(TableStyle([
        ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",(0, 0), (-1, -1), 10),
        ("BOX",     (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",(0, 0), (-1, -1), 0.3, BORDER),
    ]))
    story.append(env_tbl)
    story.append(Spacer(1, 12))

    # ── 이벤트 ──
    story.append(Paragraph("■ 특이 이벤트", s["section"]))
    events_str = "　".join(data.get("events", []))
    story.append(Paragraph(events_str or "특이 이벤트 없음", s["body"]))
    story.append(Spacer(1, 12))

    # ── AI 인사이트 ──
    story.append(Paragraph("■ AI 인사이트", s["section"]))
    insight_tbl = Table(
        [[Paragraph(data.get("ai_comment", ""), s["insight"])]],
        colWidths=[W],
    )
    insight_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LINEBEFORE",   (0, 0), (0, -1), 3, BLUE),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(insight_tbl)

    # ── 푸터 ──
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=W, color=BORDER))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Mom-i © 2025 — 본 리포트는 AI 분석 결과로, 의학적 진단을 대체하지 않습니다.　|　카메라 SN: {data.get('ser_no', '')}",
        s["small"]
    ))

    doc.build(story)
    return buf.getvalue()
