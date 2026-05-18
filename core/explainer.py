"""
Module 11 — Signal Explanation (LLM / Rule-based)
Generates plain-English explanations of why a signal was generated.
Uses local rule-based templates by default.
Optionally calls Claude API if ANTHROPIC_API_KEY is set.
Never uses words: guaranteed, risk-free, sure trade, 100% accuracy.
"""
from __future__ import annotations

from typing import Dict, Any, Optional

from config import settings
from utils.logger import get_logger

log = get_logger("explainer")

FORBIDDEN_PHRASES = [
    "guaranteed profit", "guaranteed", "risk-free", "risk free",
    "sure trade", "100% accuracy", "100 percent", "certain profit",
    "always profitable",
]

SIGNAL_EMOJI = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸", "NO_TRADE": "🚫"}


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based template explainer
# ─────────────────────────────────────────────────────────────────────────────

def _explain_signal(signal: str) -> str:
    return {
        "BUY":      "The system generated a **BUY** signal.",
        "SELL":     "The system generated a **SELL** signal.",
        "HOLD":     "The system recommends **HOLD** — no clear directional edge at this moment.",
        "NO_TRADE": "The system flagged **NO_TRADE** — entry conditions were not met.",
    }.get(signal, f"Signal: {signal}")


def _explain_ml(ml_signal: str, ml_confidence: float, model: str) -> str:
    if not ml_signal:
        return ""
    return (
        f"The ML model ({model}) predicted **{ml_signal}** "
        f"with {ml_confidence:.0%} confidence."
    )


def _explain_ema(ema_trend: str, signal: str) -> str:
    if not ema_trend:
        return ""
    trend_desc = {"up": "uptrend", "down": "downtrend", "neutral": "neutral / sideways"}.get(ema_trend, ema_trend)
    aligned = (signal == "BUY" and ema_trend == "up") or (signal == "SELL" and ema_trend == "down")
    suffix = "✅ aligned with signal" if aligned else "⚠️ conflicts with signal"
    return f"EMA structure shows a **{trend_desc}** — {suffix}."


def _explain_rsi(rsi: float, signal: str) -> str:
    if not rsi:
        return ""
    if rsi > 70:
        return f"RSI is **{rsi:.1f}** — overbought zone; potential reversal risk for longs."
    if rsi < 30:
        return f"RSI is **{rsi:.1f}** — oversold zone; potential reversal risk for shorts."
    return f"RSI is **{rsi:.1f}** — within neutral range."


def _explain_macd(macd_hist: float, signal: str) -> str:
    if macd_hist == 0:
        return ""
    direction = "bullish" if macd_hist > 0 else "bearish"
    aligned = (signal == "BUY" and macd_hist > 0) or (signal == "SELL" and macd_hist < 0)
    suffix = "✅ aligned" if aligned else "⚠️ conflicting"
    return f"MACD histogram is **{macd_hist:.5f}** ({direction}) — {suffix} with signal."


def _explain_structure(structure_label: str, bos: str) -> str:
    labels = {
        "bullish_trending": "bullish trend structure (HH + HL sequence)",
        "bearish_trending": "bearish trend structure (LL + LH sequence)",
        "ranging": "ranging / consolidation market",
        "mixed": "mixed market structure",
        "neutral": "neutral market structure",
    }
    desc = labels.get(structure_label, structure_label)
    bos_desc = ""
    if bos == "bullish":
        bos_desc = " — a **bullish break of structure** was detected."
    elif bos == "bearish":
        bos_desc = " — a **bearish break of structure** was detected."
    return f"Market structure: **{desc}**{bos_desc}"


def _explain_news(news_blocked: bool, news_reason: str, sentiment: float) -> str:
    if news_blocked:
        return f"🚨 Trade was **blocked by news risk**: {news_reason}."
    if abs(sentiment) > 0.2:
        direction = "positive" if sentiment > 0 else "negative"
        return f"News sentiment is **{direction}** ({sentiment:+.2f}) — factored into confidence."
    return "No significant news risk detected at this time."


def _explain_risk(sl_pips: float, tp_pips: float, risk_reward: float, lot_size: float, risk_amount: float) -> str:
    if sl_pips <= 0:
        return ""
    return (
        f"Risk parameters: SL = **{sl_pips:.1f} pips**, TP = **{tp_pips:.1f} pips**, "
        f"RR = **1:{risk_reward:.2f}**, Lot = **{lot_size}**, Risk = **${risk_amount:.2f}**."
    )


def _explain_blocks(blocks: list) -> str:
    if not blocks:
        return ""
    human_readable = {
        "confidence_too_low": "ML confidence was below the minimum threshold",
        "ema_trend_conflict": "EMA trend conflicted with the ML signal",
        "macd_conflict": "MACD histogram conflicted with the signal",
        "rsi_overbought": "RSI entered overbought territory",
        "rsi_oversold": "RSI entered oversold territory",
        "volatility_too_low": "Market volatility was too low for a valid setup",
        "volatility_too_high": "Market volatility was extremely high — risky conditions",
        "spread_too_high": "Spread exceeded the maximum allowed",
        "daily_loss_limit_reached": "Daily loss limit was already reached",
        "max_trades_per_day_reached": "Maximum number of trades for today was reached",
        "max_open_trades_reached": "Maximum number of open trades is already reached",
        "kill_switch_active": "Kill switch was engaged — all trading halted",
        "news_blocked": "A high-impact news event blocked the trade",
        "structure_conflict": "Market structure conflicted with the ML direction",
        "multiple_soft_blocks": "Multiple soft filter conflicts accumulated",
    }
    reasons = []
    for b in blocks:
        key = b.split("(")[0]  # strip parenthetical detail
        reasons.append(human_readable.get(key, b))
    return "**Filters that blocked or reduced confidence:**\n- " + "\n- ".join(reasons)


# ─────────────────────────────────────────────────────────────────────────────
# LLM (Claude) explainer — optional
# ─────────────────────────────────────────────────────────────────────────────

def _llm_explanation(signal_dict: Dict[str, Any]) -> Optional[str]:
    """Call Claude API if key is configured. Returns None on any failure."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = f"""You are a professional trading analyst assistant.
Analyse this trading signal and explain it clearly in 3-4 sentences for a retail trader.
Be factual, concise, and educational.

IMPORTANT RULES:
- NEVER say: guaranteed profit, risk-free, sure trade, 100% accuracy, certain profit
- Always remind the user this is probabilistic, not a guarantee
- Mention which indicators supported and which blocked the signal

Signal data:
{signal_dict}

Respond in plain English without JSON or code blocks."""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Safety: strip any forbidden phrases
        for phrase in FORBIDDEN_PHRASES:
            text = text.replace(phrase, "potentially profitable")
        return text

    except Exception as exc:
        log.debug("LLM explanation failed: {}", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Master explainer
# ─────────────────────────────────────────────────────────────────────────────

def generate_explanation(signal_dict: Dict[str, Any]) -> str:
    """
    Returns a plain-English explanation.
    Tries LLM first (if API key set), falls back to rule-based templates.
    """
    signal = signal_dict.get("signal", "NO_TRADE")
    emoji = SIGNAL_EMOJI.get(signal, "")

    # Try LLM
    llm_text = _llm_explanation(signal_dict)
    if llm_text:
        return f"{emoji} {llm_text}"

    # Rule-based fallback
    lines = [f"## {emoji} Signal Analysis — {signal_dict.get('symbol', '')} {signal_dict.get('timeframe', '')}"]
    lines.append("")
    lines.append(_explain_signal(signal))
    lines.append("")

    ml_line = _explain_ml(
        signal_dict.get("ml_signal", ""),
        float(signal_dict.get("ml_confidence", 0)),
        signal_dict.get("ml_model_used", "unknown"),
    )
    if ml_line:
        lines.append("**ML Layer:**")
        lines.append(ml_line)

    lines.append("")
    lines.append("**Indicator Readings:**")
    ema_line = _explain_ema(signal_dict.get("ema_trend", ""), signal)
    if ema_line:
        lines.append(f"- {ema_line}")

    rsi_line = _explain_rsi(float(signal_dict.get("rsi", 50)), signal)
    if rsi_line:
        lines.append(f"- {rsi_line}")

    macd_line = _explain_macd(float(signal_dict.get("macd_hist", 0)), signal)
    if macd_line:
        lines.append(f"- {macd_line}")

    struct_line = _explain_structure(
        signal_dict.get("structure_label", ""),
        signal_dict.get("bos", ""),
    )
    if struct_line:
        lines.append(f"- {struct_line}")

    lines.append("")
    lines.append("**News & Macro:**")
    news_line = _explain_news(
        bool(signal_dict.get("news_blocked", False)),
        signal_dict.get("news_reason", ""),
        float(signal_dict.get("news_sentiment", 0)),
    )
    lines.append(news_line)

    risk_line = _explain_risk(
        float(signal_dict.get("sl_pips", 0)),
        float(signal_dict.get("tp_pips", 0)),
        float(signal_dict.get("risk_reward", 0)),
        float(signal_dict.get("lot_size", 0)),
        float(signal_dict.get("risk_amount", 0)),
    )
    if risk_line:
        lines.append("")
        lines.append("**Trade Setup:**")
        lines.append(risk_line)

    blocks = signal_dict.get("blocks", [])
    if blocks:
        lines.append("")
        lines.append(_explain_blocks(blocks))

    supports = signal_dict.get("supports", [])
    if supports:
        lines.append("")
        lines.append("**Filters that supported the signal:**")
        for s in supports:
            lines.append(f"- {s}")

    return "\n".join(lines)
