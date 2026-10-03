"""
uapay.py — оплата из Украины (квитанции банков через check.gov.ua).

Режим задаётся переменной окружения CHECK_GOV_UA_MODE:

  stub        (по умолчанию) — ЗАГЛУШКА. Ничего не проверяет и не зачисляет, не требует
                               Playwright/Chromium, ничего системного не ставится.
                               Клиент видит «скоро будет доступно».
  playwright  — реальная проверка через headless-браузер. Нужно отдельно:
                  pip install -r requirements-optional.txt
                  playwright install chromium
                (--with-deps не используем: он ставит системные пакеты через apt)

Контракт для любого провайдера — одна async-функция, возвращающая dict:
    {"ok": bool, "paid": bool, "amount": float|None, "recipient": str, "raw_data": dict, "error": str?}
Хочешь подключить другой способ (API эквайринга и т.п.) — добавь функцию в PROVIDERS ниже,
остальной код (handlers/checkgov.py) трогать не нужно.
"""
from __future__ import annotations

import json as _json
import logging
import re as _re

from config import CHECK_GOV_UA_MODE

log = logging.getLogger("uapay")

# Код ошибки, по которому handlers/checkgov.py понимает, что это заглушка.
ERR_STUB = "ua_pay_stub"

STUB_TEXT_RU = (
    "🇺🇦 <b>Оплата из Украины (по квитанции)</b>\n\n"
    "Этот способ пока в разработке и скоро будет доступен.\n"
    "А сейчас пополните баланс через <b>СБП</b> или <b>Crypto Bot</b>."
)
STUB_TEXT_UA = (
    "🇺🇦 <b>Оплата з України (за квитанцією)</b>\n\n"
    "Цей спосіб поки що в розробці й скоро буде доступний.\n"
    "А зараз поповніть баланс через <b>СБП</b> або <b>Crypto Bot</b>."
)


def is_stub() -> bool:
    """True, если реальная проверка квитанций не включена (работает заглушка)."""
    return CHECK_GOV_UA_MODE != "playwright"


# ───────────────────────── провайдеры ─────────────────────────
async def _verify_stub(receipt_code: str, bank: str = "monobank") -> dict:
    """Заглушка: честно говорит «не поддерживается», денег не зачисляет."""
    log.info("[uapay] stub: проверка квитанции пропущена (code=%s bank=%s)", receipt_code, bank)
    return {"ok": False, "paid": False, "amount": None, "recipient": "", "raw_data": {}, "error": ERR_STUB}


async def _verify_playwright(receipt_code: str, bank: str = "monobank") -> dict:
    """Реальная проверка через check.gov.ua (Playwright импортируется только здесь, лениво)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"ok": False, "error": "playwright_not_installed"}

    result = {"ok": False, "paid": False, "amount": None, "recipient": None, "raw_data": {}}

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as e:           # браузер не скачан / нет системных библиотек
            log.error("[uapay] Chromium не запускается: %r (playwright install --with-deps chromium)", e)
            return {"ok": False, "error": "playwright_browser_missing"}

        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/152.0.0.0 Safari/537.36",
            locale="uk-UA",
        )
        page = await ctx.new_page()
        api_response_data: dict = {}

        async def on_response(response):
            if "api/handler" in response.url and response.status == 200:
                try:
                    text = await response.text()
                    api_response_data.update({"raw": text})
                    try:
                        api_response_data.update({"json": _json.loads(text)})
                    except Exception:
                        pass
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto("https://check.gov.ua/", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            try:
                await page.select_option("select", value=bank, timeout=3000)
            except Exception:
                try:
                    await page.click(f"text={bank}", timeout=3000)
                except Exception:
                    pass

            inp = page.locator("input[type='text'], input[placeholder*='код'], input[placeholder*='квитанц']").first
            await inp.fill(receipt_code)
            btn = page.locator("button[type='submit'], button:has-text('Перевірити')").first
            await btn.click()

            for _ in range(40):                      # ждём ответ до ~20 сек
                await page.wait_for_timeout(500)
                if api_response_data.get("raw"):
                    break
        except Exception as e:
            result["error"] = str(e)
            await browser.close()
            return result

        await browser.close()

    if not api_response_data.get("raw"):
        result["error"] = "no_response"
        return result

    result["ok"] = True
    data = api_response_data.get("json", {})
    result["raw_data"] = data

    raw_text = api_response_data.get("raw", "")
    status = str(data.get("status") or data.get("state") or data.get("result") or "")
    result["paid"] = (
        status.lower() in ["paid", "оплачено", "success", "ok", "true", "1"]
        or "Оплачена" in raw_text or "Оплачено" in raw_text
        or data.get("paid") in [True, 1, "true"]
    )

    raw_amount = data.get("amount") or data.get("sum") or data.get("total")
    if raw_amount is not None:
        try:
            a = float(str(raw_amount).replace(",", "."))
            result["amount"] = round(a / 100 if a > 5000 else a, 2)
        except Exception:
            pass
    if not result["amount"]:
        m = _re.search(r"(\d+[.,]\d{2})", raw_text)
        if m:
            try:
                result["amount"] = float(m.group(1).replace(",", "."))
            except Exception:
                pass

    result["recipient"] = (
        data.get("recipient") or data.get("receiver")
        or data.get("recipientName") or data.get("name") or ""
    )
    return result


PROVIDERS = {
    "stub": _verify_stub,
    "playwright": _verify_playwright,
}


async def verify_receipt(receipt_code: str, bank: str = "monobank") -> dict:
    """Единая точка входа: выбирает провайдера по CHECK_GOV_UA_MODE (неизвестный режим = stub)."""
    provider = PROVIDERS.get(CHECK_GOV_UA_MODE, _verify_stub)
    return await provider(receipt_code, bank)
