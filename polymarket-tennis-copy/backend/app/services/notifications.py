"""Notification providers.

Modular by design: adding a channel means adding a :class:`Notifier` subclass.
Delivery failures never propagate into the analytics pipeline -- a broken webhook
must not stop ingestion -- and credentials never appear in messages, logs or
error records (see :mod:`app.logging_setup` for the scrubbing pipeline).

Language in alert bodies is deliberately measured. No "lock", "guaranteed", or
"risk-free" phrasing appears anywhere, and every alert carries the
not-financial-advice notice.
"""

from __future__ import annotations

import json
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from email.message import EmailMessage
from enum import StrEnum

import httpx

from ..config import Settings, get_settings
from ..logging_setup import get_logger

log = get_logger(__name__)

DISCLAIMER = (
    "Analytical signal only -- not financial advice. Historical results do not "
    "guarantee future performance. Paper results may differ materially from real "
    "execution."
)


class NotificationType(StrEnum):
    """Alert categories. Each can be routed and muted independently."""

    NEW_QUALIFYING_ENTRY = "new_qualifying_entry"
    MULTI_WALLET_CONSENSUS = "multi_wallet_consensus"
    POSITION_INCREASE = "position_increase"
    WALLET_EXIT = "wallet_exit"
    SIGNAL_EXPIRED = "signal_expired"
    PAPER_TRADE_ENTRY = "paper_trade_entry"
    PAPER_TRADE_EXIT = "paper_trade_exit"
    DAILY_SUMMARY = "daily_summary"
    WALLET_DOWNGRADE = "wallet_downgrade"
    PIPELINE_FAILURE = "pipeline_failure"


@dataclass(slots=True)
class Notification:
    """A channel-agnostic message."""

    type: NotificationType
    title: str
    body: str
    # Structured mirror of the message, for the in-app feed and audit trail.
    payload: dict = field(default_factory=dict)
    severity: str = "info"
    url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def payload_json(self) -> str:
        return json.dumps(self.payload, default=str, sort_keys=True)


@dataclass(slots=True)
class DeliveryResult:
    channel: str
    delivered: bool
    error: str | None = None
    attempts: int = 1


class Notifier(ABC):
    """One delivery channel."""

    channel: str = "abstract"

    @abstractmethod
    def is_configured(self) -> bool:
        """True when this channel has enough configuration to deliver."""

    @abstractmethod
    def send(self, notification: Notification) -> DeliveryResult:
        """Attempt delivery. Must never raise."""


class InAppNotifier(Notifier):
    """Always-available channel. Persistence is handled by the alert service."""

    channel = "in_app"

    def is_configured(self) -> bool:
        return True

    def send(self, notification: Notification) -> DeliveryResult:
        # Nothing to transmit: the alert row itself is the delivery.
        return DeliveryResult(channel=self.channel, delivered=True)


class DiscordNotifier(Notifier):
    """Discord incoming webhook."""

    channel = "discord"

    # Discord rejects embeds whose description exceeds this.
    MAX_DESCRIPTION = 4000

    def __init__(self, webhook_url: str | None = None, timeout: float = 10.0) -> None:
        self.webhook_url = webhook_url or get_settings().discord_webhook_url
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, notification: Notification) -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult(self.channel, False, "discord webhook not configured")

        colour = {
            "info": 0x3498DB,
            "success": 0x2ECC71,
            "warning": 0xF39C12,
            "error": 0xE74C3C,
        }.get(notification.severity, 0x95A5A6)

        fields = [
            {"name": str(k), "value": str(v)[:1024], "inline": True}
            for k, v in list(notification.payload.items())[:24]
            if v is not None
        ]

        body = {
            "username": "Tennis Copy Trade",
            "embeds": [
                {
                    "title": notification.title[:256],
                    "description": notification.body[: self.MAX_DESCRIPTION],
                    "color": colour,
                    "fields": fields,
                    "footer": {"text": DISCLAIMER[:2048]},
                    "timestamp": notification.created_at.isoformat(),
                }
            ],
        }
        if notification.url:
            body["embeds"][0]["url"] = notification.url

        try:
            response = httpx.post(self.webhook_url, json=body, timeout=self.timeout)
            if response.status_code >= 400:
                # Never echo the URL: it is itself the credential.
                return DeliveryResult(
                    self.channel, False, f"discord returned {response.status_code}"
                )
            return DeliveryResult(self.channel, True)
        except Exception as exc:  # noqa: BLE001 - delivery must never propagate
            return DeliveryResult(self.channel, False, f"{type(exc).__name__}: {exc}")


class TelegramNotifier(Notifier):
    """Telegram Bot API."""

    channel = "telegram"
    MAX_LENGTH = 4096

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, notification: Notification) -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult(self.channel, False, "telegram not configured")

        lines = [f"*{_escape_markdown(notification.title)}*", "", notification.body]
        if notification.payload:
            lines.append("")
            lines.extend(
                f"- {k}: {v}"
                for k, v in list(notification.payload.items())[:20]
                if v is not None
            )
        lines += ["", f"_{DISCLAIMER}_"]
        text = "\n".join(lines)[: self.MAX_LENGTH]

        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                return DeliveryResult(
                    self.channel, False, f"telegram returned {response.status_code}"
                )
            return DeliveryResult(self.channel, True)
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(self.channel, False, f"{type(exc).__name__}: {exc}")


class EmailNotifier(Notifier):
    """SMTP email."""

    channel = "email"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        s = self.settings
        return bool(s.smtp_host and s.smtp_from and s.smtp_to)

    def send(self, notification: Notification) -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult(self.channel, False, "smtp not configured")

        s = self.settings
        message = EmailMessage()
        message["Subject"] = notification.title[:200]
        message["From"] = s.smtp_from
        message["To"] = s.smtp_to

        details = "\n".join(
            f"  {k}: {v}" for k, v in notification.payload.items() if v is not None
        )
        message.set_content(
            f"{notification.body}\n\n{details}\n\n---\n{DISCLAIMER}\n"
        )

        try:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
                smtp.ehlo()
                if s.smtp_port in (587, 25):
                    try:
                        smtp.starttls()
                        smtp.ehlo()
                    except smtplib.SMTPNotSupportedError:
                        # Server without TLS: continue only because these are
                        # non-secret operational alerts.
                        log.warning("notifications.smtp_no_tls")
                if s.smtp_username and s.smtp_password:
                    smtp.login(s.smtp_username, s.smtp_password)
                smtp.send_message(message)
            return DeliveryResult(self.channel, True)
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(self.channel, False, f"{type(exc).__name__}: {exc}")


def _escape_markdown(text: str) -> str:
    for char in ("_", "*", "[", "]", "`"):
        text = text.replace(char, f"\\{char}")
    return text


class NotificationDispatcher:
    """Fans a notification out to every configured channel."""

    def __init__(self, notifiers: list[Notifier] | None = None) -> None:
        settings = get_settings()
        self.enabled = settings.notifications_enabled
        if notifiers is not None:
            self.notifiers = notifiers
        else:
            self.notifiers = [
                InAppNotifier(),
                DiscordNotifier(),
                TelegramNotifier(),
                EmailNotifier(),
            ]

    def configured_channels(self) -> list[str]:
        return [n.channel for n in self.notifiers if n.is_configured()]

    def dispatch(self, notification: Notification) -> list[DeliveryResult]:
        if not self.enabled:
            log.debug("notifications.disabled", type=notification.type.value)
            return []

        results: list[DeliveryResult] = []
        for notifier in self.notifiers:
            if not notifier.is_configured():
                continue
            result = notifier.send(notification)
            results.append(result)
            if result.delivered:
                log.info(
                    "notifications.delivered",
                    channel=result.channel,
                    type=notification.type.value,
                )
            else:
                log.warning(
                    "notifications.failed",
                    channel=result.channel,
                    type=notification.type.value,
                    error=result.error,
                )
        return results


# ------------------------------------------------------------------ builders


def _fmt_price(value: Decimal | None) -> str:
    return f"${value}" if value is not None else "n/a"


def _fmt_pct(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "n/a"


def build_signal_notification(
    *,
    signal_type: str,
    market_title: str,
    outcome_label: str,
    wallet_count: int,
    independent_groups: int,
    wallet_entry_min: Decimal | None,
    wallet_entry_max: Decimal | None,
    current_price: Decimal | None,
    follower_price: Decimal | None,
    price_deterioration: Decimal | None,
    liquidity: Decimal | None,
    spread: Decimal | None,
    median_copyable_roi: float | None,
    copyability_score: float | None,
    consensus_score: float | None,
    skill_score: float | None,
    estimated_edge: float | None,
    sample_size: int | None,
    signal_age_seconds: int | None,
    data_confidence: float | None,
    risk_flags: list[str],
    explanation: str,
    market_phase: str,
    url: str | None = None,
) -> Notification:
    """Build an alert containing every field the spec requires.

    Deliberately verbose: an alert that omits price deterioration, liquidity, or
    its own risk flags invites a decision the data does not support.
    """
    is_consensus = wallet_count > 1
    entry_range = (
        _fmt_price(wallet_entry_min)
        if wallet_entry_min == wallet_entry_max
        else f"{_fmt_price(wallet_entry_min)}-{_fmt_price(wallet_entry_max)}"
    )

    title = (
        f"{wallet_count} wallets agree: {outcome_label}"
        if is_consensus
        else f"Qualified wallet entry: {outcome_label}"
    )

    payload = {
        "Market": market_title,
        "Outcome": outcome_label,
        "Wallets": f"{wallet_count} ({independent_groups} independent group(s))",
        "Wallet entry": entry_range,
        "Current price": _fmt_price(current_price),
        "Est. follower price": _fmt_price(follower_price),
        "Price deterioration": _fmt_price(price_deterioration),
        "Liquidity": f"${liquidity:,.0f}" if liquidity is not None else "n/a",
        "Spread": _fmt_price(spread),
        "Median copyable ROI": _fmt_pct(median_copyable_roi),
        "Copyability": f"{copyability_score:.0f}/100" if copyability_score is not None else "n/a",
        "Skill score": f"{skill_score:.0f}/100" if skill_score is not None else "n/a",
        "Consensus score": f"{consensus_score:.0f}/100" if consensus_score is not None else None,
        "Est. edge (heuristic)": _fmt_pct(estimated_edge),
        "Sample size": str(sample_size) if sample_size is not None else "n/a",
        "Market status": market_phase,
        "Signal age": f"{signal_age_seconds}s" if signal_age_seconds is not None else "n/a",
        "Data confidence": f"{data_confidence:.0f}/100" if data_confidence is not None else "n/a",
        "Risk flags": ", ".join(risk_flags) if risk_flags else "none",
    }

    return Notification(
        type=(
            NotificationType.MULTI_WALLET_CONSENSUS
            if is_consensus
            else NotificationType.NEW_QUALIFYING_ENTRY
        ),
        title=title,
        body=explanation,
        payload={k: v for k, v in payload.items() if v is not None},
        severity="success" if is_consensus else "info",
        url=url,
    )


def build_pipeline_failure_notification(
    component: str, message: str, job_uid: str | None = None
) -> Notification:
    return Notification(
        type=NotificationType.PIPELINE_FAILURE,
        title=f"Data pipeline failure: {component}",
        body=(
            f"{message}\n\nSignals may be stale or incomplete until this is "
            "resolved. Treat any current alerts with caution."
        ),
        payload={"Component": component, "Job": job_uid or "n/a"},
        severity="error",
    )


def build_daily_summary_notification(stats: dict) -> Notification:
    return Notification(
        type=NotificationType.DAILY_SUMMARY,
        title="Daily paper-trading summary",
        body=(
            "Simulated results for the last 24 hours. These are paper trades: no "
            "real orders were placed, and real execution would differ."
        ),
        payload=stats,
        severity="info",
    )


def build_wallet_downgrade_notification(
    address: str, old_score: float, new_score: float, reasons: list[str]
) -> Notification:
    return Notification(
        type=NotificationType.WALLET_DOWNGRADE,
        title=f"Wallet downgraded: {address[:10]}...",
        body=(
            f"Skill score fell from {old_score:.1f} to {new_score:.1f}. "
            "This wallet may no longer meet alerting standards."
        ),
        payload={"Wallet": address, "Reasons": "; ".join(reasons) or "score decline"},
        severity="warning",
    )
