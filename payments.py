"""
payments.py — Crypto Bot + Платёга (СБП)
"""
from __future__ import annotations
import asyncio
import uuid
import hashlib
import hmac
import json
import aiohttp
from aiogram import Bot
from aiogram.enums import ParseMode

from config import (
    CRYPTO_PAY_TOKEN, CRYPTO_PAY_ASSET, CRYPTO_PAY_BASE_URL,
    CRYPTO_PAY_RETURN_URL, CRYPTO_RUB_TO_USDT_FALLBACK,
    PLATEGA_MERCHANT, PLATEGA_SECRET, PLATEGA_BASE_URL, PLATEGA_RETURN_URL,
    BOT_USERNAME,
)
from database import db


# ══════════════════════════════════════
# CRYPTO BOT
# ══════════════════════════════════════

async def crypto_create_invoice(amount_rub: float, user_id: int):
    """Создаёт счёт Crypto Bot в рублях через fiat-режим (или USDT fallback)."""
    if not CRYPTO_PAY_TOKEN:
        return None, None

    base = {
        "description": f"Xazura Shop: пополнение (ID: {user_id})",
        "hidden_message": "Спасибо! Баланс пополнен автоматически.",
        "paid_btn_name": "openBot",
        "paid_btn_url": CRYPTO_PAY_RETURN_URL,
        "payload": str(user_id),
        "allow_comments": False,
        "allow_anonymous": True,
    }

    # Попытка 1: fiat RUB (CryptoBot сам конвертирует)
    fiat_payload = {**base, "currency_type": "fiat", "fiat": "RUB",
                    "amount": f"{amount_rub:.2f}", "accepted_assets": CRYPTO_PAY_ASSET}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{CRYPTO_PAY_BASE_URL}/createInvoice",
                              json=fiat_payload,
                              headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}) as resp:
                data = await resp.json()
                if data.get("ok"):
                    res = data["result"]
                    return res.get("invoice_id"), res.get("bot_invoice_url")
    except Exception as e:
        print(f"[CryptoBot fiat] {e}")

    # Попытка 2: crypto USDT по запасному курсу
    amount_usdt = round(amount_rub / CRYPTO_RUB_TO_USDT_FALLBACK, 2)
    crypto_payload = {**base, "currency_type": "crypto",
                      "asset": CRYPTO_PAY_ASSET, "amount": f"{amount_usdt:.2f}"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{CRYPTO_PAY_BASE_URL}/createInvoice",
                              json=crypto_payload,
                              headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}) as resp:
                data = await resp.json()
                if data.get("ok"):
                    res = data["result"]
                    return res.get("invoice_id"), res.get("bot_invoice_url")
    except Exception as e:
        print(f"[CryptoBot usdt] {e}")

    return None, None


async def crypto_check_invoice(invoice_id: int) -> str | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{CRYPTO_PAY_BASE_URL}/getInvoices",
                params={"invoice_ids": str(invoice_id)},
                headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN},
            ) as resp:
                data = await resp.json()
                items = data.get("result", {}).get("items", [])
                return items[0]["status"] if items else None
    except Exception as e:
        print(f"[CryptoBot check] {e}")
        return None


# ══════════════════════════════════════
# ПЛАТЁГА (СБП)
# Документация: platega.io/docs
# Нужны: PLATEGA_MERCHANT и PLATEGA_SECRET в config.py / .env
# ══════════════════════════════════════

def platega_is_configured() -> bool:
    return (bool(PLATEGA_MERCHANT) and "ВСТАВЬ" not in PLATEGA_MERCHANT
            and bool(PLATEGA_SECRET) and "ВСТАВЬ" not in PLATEGA_SECRET)


def _platega_sign(params: dict) -> str:
    """HMAC-SHA256 подпись параметров платежа.
    Поле 'sign' исключается из подписи (если вдруг уже есть в словаре).
    """
    filtered = {k: v for k, v in params.items() if k != "sign"}
    payload = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    return hmac.new(PLATEGA_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def platega_create_payment(amount_rub: float, user_id: int):
    """
    Создаёт платёж через Платёгу (platega.io).
    Возвращает (order_id, pay_url) или (None, None).

    API Платёги:
      POST /api/v1/create
      Поля: merchant_uuid, amount (в копейках!), order_id, description, success_url, sign
      Ответ: {"id": ..., "url": "https://platega.io/pay/..."}
    """
    if not platega_is_configured():
        return None, None

    order_id = str(uuid.uuid4())
    # amount передаётся в КОПЕЙКАХ (рубли × 100)
    amount_kopecks = str(int(round(amount_rub * 100)))
    params = {
        "merchant_uuid": PLATEGA_MERCHANT,
        "amount":        amount_kopecks,
        "order_id":      order_id,
        "description":   f"Xazura Shop: пополнение (ID: {user_id})",
        "success_url":   PLATEGA_RETURN_URL,
    }
    params["sign"] = _platega_sign(params)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{PLATEGA_BASE_URL}/create",
                json=params,
                headers={"Content-Type": "application/json"},
            ) as resp:
                data = await resp.json()
                # Платёга возвращает {"id": "...", "url": "https://..."}
                # либо {"error": "...", "message": "..."}
                pay_url = data.get("url") or data.get("payment_url") or data.get("link")
                if pay_url:
                    return order_id, pay_url
                print(f"[Платёга] create error: {data}")
    except Exception as e:
        print(f"[Платёга] exception: {e}")

    return None, None


async def platega_check_payment(order_id: str) -> str | None:
    """Проверяет статус платежа. Возвращает 'paid' | 'pending' | 'canceled' | None."""
    if not platega_is_configured():
        return None
    params = {"merchant_uuid": PLATEGA_MERCHANT, "order_id": order_id}
    params["sign"] = _platega_sign(params)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{PLATEGA_BASE_URL}/status",
                              json=params,
                              headers={"Content-Type": "application/json"}) as resp:
                data = await resp.json()
                # Платёга возвращает {"status": "paid"|"pending"|"canceled", ...}
                return data.get("status")
    except Exception as e:
        print(f"[Платёга check] {e}")
        return None


# ══════════════════════════════════════
# ФОНОВЫЙ КОНТРОЛЛЕР ПЛАТЕЖЕЙ
# Один цикл смотрит ВСЕ неоплаченные счета из БД (а не по таску на счёт), поэтому:
#  • перезапуск бота не «теряет» оплаченные счета;
#  • оплата через 10 минут/час после создания счёта тоже зачислится (до 24 ч);
#  • зачисление идёт через claim_pending → двойной зачёт невозможен.
# ══════════════════════════════════════
import time as _time
from datetime import datetime as _dt

PENDING_MAX_AGE_H = 24
_FAST_WINDOW_S = 15 * 60       # первые 15 мин проверяем каждые ~4 сек, дальше раз в минуту


def _pending_age_seconds(p: dict) -> float:
    try:
        return (_dt.now() - _dt.strptime(p.get("created_at", ""), "%d.%m.%Y %H:%M:%S")).total_seconds()
    except (ValueError, TypeError):
        return 0.0


async def _safe_send(bot: Bot, uid: int, text: str):
    try:
        await bot.send_message(uid, text, parse_mode=ParseMode.HTML)
    except Exception:
        pass


async def _credit_payment(bot: Bot, p: dict, label: str):
    uid, amount, pid = int(p["user_id"]), float(p["amount"]), p["payment_id"]
    if not db.claim_pending(pid, "paid"):
        return                                    # уже зачислено другим проходом
    db.add_balance(uid, amount)
    db.add_topup(uid, amount, label)
    bal = db.balance(uid)
    await _safe_send(bot, uid, f"✅ <b>Оплата прошла!</b>\n\n🪙 +{amount:.1f} ₽\n🪙 Баланс: {bal:.1f} ₽")


async def check_pending_once(bot: Bot, last_check: dict[str, float]) -> None:
    """Один проход по открытым счетам. Вынесено отдельно, чтобы тестировать без бесконечного цикла."""
    for p in db.list_open_pending():
        pid = p["payment_id"]
        age = _pending_age_seconds(p)
        if age > PENDING_MAX_AGE_H * 3600:
            if db.claim_pending(pid, "timeout"):
                await _safe_send(bot, int(p["user_id"]), "⏰ Время оплаты истекло. Создайте новый счёт.")
            continue
        interval = 3.5 if age < _FAST_WINDOW_S else 60.0
        if _time.monotonic() - last_check.get(pid, 0.0) < interval:
            continue
        last_check[pid] = _time.monotonic()

        method = p.get("method") or ("crypto" if str(pid).isdigit() else "sbp")
        if method == "crypto":
            status = await crypto_check_invoice(int(pid))
            if status == "paid":
                await _credit_payment(bot, p, "Crypto Bot")
            elif status == "expired" and db.claim_pending(pid, "timeout"):
                await _safe_send(bot, int(p["user_id"]), "⏰ Время оплаты истекло. Создайте новый счёт.")
        else:
            status = await platega_check_payment(pid)
            if status == "paid":
                await _credit_payment(bot, p, "СБП")
            elif status in ("canceled", "cancelled") and db.claim_pending(pid, "canceled"):
                await _safe_send(bot, int(p["user_id"]), "❌ Платёж по СБП отменён.")


async def watch_pending(bot: Bot, tick: float = 3.5) -> None:
    """Бесконечный фоновый цикл. Запускается один раз в main.py."""
    last_check: dict[str, float] = {}
    while True:
        try:
            await check_pending_once(bot, last_check)
        except asyncio.CancelledError:
            raise
        except Exception as e:                    # цикл не должен умирать из-за разовой ошибки
            print(f"[watch_pending] {e!r}")
        await asyncio.sleep(tick)


# ══════════════════════════════════════
# CHECK.GOV.UA (оплата из Украины) — вынесено в uapay.py.
# По умолчанию там ЗАГЛУШКА (Playwright не нужен). Имя check_gov_ua_verify сохранено для handlers/checkgov.py.
# ══════════════════════════════════════
from uapay import verify_receipt as check_gov_ua_verify  # noqa: E402,F401
