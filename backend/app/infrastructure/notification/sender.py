"""
notification/sender.py — SMS / 이메일 알림 발송

SMS   : Coolsms(Solapi) HMAC-SHA256 인증 — httpx 비동기
Email : Gmail SMTP
"""
import hashlib
import hmac
import logging
import smtplib
import asyncio
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Literal, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def detect_contact_type(contact: str) -> Literal["sms", "email"]:
    """'@' 포함이면 이메일, 아니면 SMS(전화번호)로 판단."""
    return "email" if "@" in contact else "sms"


# ── 이메일 ────────────────────────────────────────────────────────────────────

def _smtp_send(to: str, msg: MIMEMultipart) -> None:
    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        smtp.sendmail(settings.EMAIL_USER, to, msg.as_string())


# ── SMS (Coolsms/Solapi) ─────────────────────────────────────────────────────

def _coolsms_auth_header() -> str:
    date   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    salt   = uuid.uuid4().hex
    sig    = hmac.new(
        settings.COOLSMS_API_SECRET.encode(),
        (date + salt).encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"HMAC-SHA256 apiKey={settings.COOLSMS_API_KEY}, date={date}, salt={salt}, signature={sig}"


async def send_sms(contact: str, message: str) -> None:
    if not settings.COOLSMS_API_KEY or not settings.COOLSMS_SENDER:
        logger.warning("[알림-SMS] COOLSMS_API_KEY 또는 COOLSMS_SENDER 미설정 — 발송 생략")
        return

    to = contact.replace("-", "").replace(" ", "")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.solapi.com/messages/v4/send",
                headers={"Authorization": _coolsms_auth_header()},
                json={"message": {
                    "to":   to,
                    "from": settings.COOLSMS_SENDER.replace("-", ""),
                    "text": message,
                }},
            )
        resp.raise_for_status()
        logger.info("[알림-SMS] 발송 완료 to=%s", contact)
    except Exception as e:
        logger.error("[알림-SMS] 발송 실패 to=%s: %s", contact, e)


# ── 메시지 빌더 ───────────────────────────────────────────────────────────────

def build_sms_message(ser_no: str, week_label: str, avg_sleep_h: float) -> str:
    return (
        f"[맘아이] {week_label} 수면 리포트가 생성됐어요!\n"
        f"이번 주 평균 수면: {avg_sleep_h}시간\n"
        f"앱에서 자세한 내용을 확인하세요."
    )


def build_email_subject(week_label: str) -> str:
    return f"[맘아이] {week_label} 주간 수면 리포트"


def build_email_body(week_label: str, avg_sleep_h: float, avg_restless_min: int) -> str:
    return (
        f"안녕하세요!\n\n"
        f"{week_label} 주간 수면 리포트가 생성됐습니다.\n\n"
        f"■ 평균 수면 시간: {avg_sleep_h}시간\n"
        f"■ 평균 뒤척임: {avg_restless_min}분\n\n"
        f"맘아이 앱에서 AI 분석 전체 내용을 확인하세요."
    )


# ── 통합 발송 ─────────────────────────────────────────────────────────────────

async def notify_report_ready(
    contacts: List[str],
    ser_no: str,
    week_label: str,
    avg_sleep_h: float,
    avg_restless_min: int,
    report=None,
) -> None:
    """
    리포트 생성 완료 후 연락처 목록에 알림 발송.
    contacts : EMTAKE shared_report_list — 전화번호 or 이메일 문자열 배열.
    report   : GenerateReportResponse — 이메일에 PDF 첨부용 (없으면 텍스트만 발송).
    """
    if not contacts:
        return

    sms_text   = build_sms_message(ser_no, week_label, avg_sleep_h)
    email_subj = build_email_subject(week_label)
    email_body = build_email_body(week_label, avg_sleep_h, avg_restless_min)

    email_contacts = [c for c in contacts if detect_contact_type(c) == "email"]
    label = week_label.replace(' ', '_')

    # PDF 생성 (이메일 수신자가 있을 때만)
    mobile_pdf = pc_pdf = None
    if report and email_contacts:
        try:
            from app.infrastructure.notification.pdf_generator import generate_report_pdfs
            mobile_pdf, pc_pdf = await generate_report_pdfs(report)
            logger.info("[알림] PDF 생성 완료 (모바일 %dKB / PC %dKB)", len(mobile_pdf)//1024, len(pc_pdf)//1024)
        except Exception as e:
            logger.error("[알림] Playwright PDF 실패, fpdf2 폴백: %s", e)
            try:
                from app.infrastructure.notification.pdf_generator import generate_report_pdf_fallback
                mobile_pdf = await generate_report_pdf_fallback(report)
                pc_pdf = mobile_pdf
            except Exception as e2:
                logger.error("[알림] fpdf2 폴백도 실패, 텍스트만 발송: %s", e2)

    for contact in contacts:
        if detect_contact_type(contact) == "sms":
            await send_sms(contact, sms_text)
        else:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = email_subj
            msg["From"]    = settings.EMAIL_USER
            msg["To"]      = contact
            msg.attach(MIMEText(email_body, "plain", "utf-8"))

            if mobile_pdf:
                p = MIMEBase("application", "pdf")
                p.set_payload(mobile_pdf)
                encoders.encode_base64(p)
                p.add_header("Content-Disposition", "attachment", filename=f"맘아이_{label}_모바일.pdf")
                msg.attach(p)
            if pc_pdf and pc_pdf is not mobile_pdf:
                p = MIMEBase("application", "pdf")
                p.set_payload(pc_pdf)
                encoders.encode_base64(p)
                p.add_header("Content-Disposition", "attachment", filename=f"맘아이_{label}_PC.pdf")
                msg.attach(p)

            try:
                await asyncio.to_thread(_smtp_send, contact, msg)
                logger.info("[알림-EMAIL] 발송 완료 to=%s%s", contact,
                            f" (PDF 모바일+PC 첨부)" if mobile_pdf and pc_pdf and pc_pdf is not mobile_pdf else
                            " (PDF 첨부)" if mobile_pdf else "")
            except Exception as e:
                logger.error("[알림-EMAIL] 발송 실패 to=%s: %s", contact, e)
