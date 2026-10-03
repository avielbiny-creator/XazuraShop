"""
handlers/checkgov.py — перевірка оплати через check.gov.ua (див. uapay.py: за замовчуванням заглушка)

Як працює:
1. Клієнт обирає банк
2. Вводить код квитанції
3. Бот перевіряє через check.gov.ua
4. Якщо підтверджено — зараховує баланс + сповіщає адміна
"""
from __future__ import annotations
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode

import json
import re
from config import ADMIN_IDS, CHECK_RECIPIENT_NAME, CHECK_CARD_NUMBER, CHECK_RATE_TO_RUB
from database import db
from payments import check_gov_ua_verify
import uapay
from utils import safe_edit, safe_edit_or_answer, is_banned

router = Router()

BANKS = {
    "monobank":   "🟡 Monobank",
    "privatbank": "🟢 ПриватБанк",
    "oschadbank": "🔵 Ощадбанк",
    "ukrsibbank": "🟠 УкрСибБанк",
    "pumb":       "🔴 ПУМБ",
    "raiffeisen": "⚪️ Райффайзен",
}


def _configured() -> bool:
    """Автозачисление безопасно только если известен получатель (кому должны были платить) и курс."""
    return bool((CHECK_RECIPIENT_NAME or re.sub(r"\D", "", CHECK_CARD_NUMBER)) and CHECK_RATE_TO_RUB > 0)


def _recipient_ok(result: dict) -> bool:
    """Квитанция должна быть оплатой ИМЕННО на наши реквизиты (иначе подойдёт любая чужая квитанция)."""
    hay = (str(result.get("recipient") or "") + " " +
           json.dumps(result.get("raw_data") or {}, ensure_ascii=False)).lower()
    if CHECK_RECIPIENT_NAME and CHECK_RECIPIENT_NAME.strip().lower() in hay:
        return True
    card = re.sub(r"\D", "", CHECK_CARD_NUMBER)
    return len(card) >= 12 and card in re.sub(r"\D", "", hay)


class CheckGovState(StatesGroup):
    choosing_bank   = State()
    entering_amount = State()
    entering_code   = State()


def kb_choose_bank() -> InlineKeyboardMarkup:
    rows = []
    for code, label in BANKS.items():
        rows.append([InlineKeyboardButton(
            text=label, callback_data=f"cgov_bank:{code}"
        )])
    rows.append([InlineKeyboardButton(text="← Скасувати", callback_data="cgov_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Скасувати", callback_data="cgov_cancel")]
    ])


# ── Точка входу ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "checkgov_start")
async def cgov_start(cb: CallbackQuery, state: FSMContext):
    if is_banned(cb.from_user.id):
        return await cb.answer("Заблоковано", show_alert=True)

    if uapay.is_stub():                      # заглушка: способ ещё не подключён
        await cb.message.answer(uapay.STUB_TEXT_UA, parse_mode=ParseMode.HTML)
        return await cb.answer()

    if not db.is_check_gov_ua_enabled() or not _configured():
        await cb.answer(
            "⚠️ Автоперевірка квитанцій тимчасово вимкнена адміністратором.",
            show_alert=True
        )
        return

    await state.set_state(CheckGovState.choosing_bank)
    await safe_edit_or_answer(
        cb,
        "💳 <b>ОПЛАТА ПО КВИТАНЦІЇ</b>\n\nОберіть ваш банк:",
        reply_markup=kb_choose_bank()
    )
    await cb.answer()


@router.callback_query(F.data == "cgov_cancel")
async def cgov_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_or_answer(cb, "❌ Скасовано.", reply_markup=None)
    await cb.answer()


# ── Вибір банку ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cgov_bank:"))
async def cgov_bank_chosen(cb: CallbackQuery, state: FSMContext):
    if is_banned(cb.from_user.id):
        return await cb.answer("Заблоковано", show_alert=True)

    bank_code = cb.data.split(":")[1]
    bank_label = BANKS.get(bank_code, bank_code)

    await state.update_data(bank=bank_code, bank_label=bank_label)
    await state.set_state(CheckGovState.entering_code)

    await safe_edit_or_answer(
        cb,
        f"✅ Банк: <b>{bank_label}</b>\n\n"
        f"Тепер надішліть <b>код квитанції</b>.\n\n"
        f"Де взяти:\n"
        f"• <b>Monobank</b>: квитанція → «Поділитися» → скопіювати код\n"
        f"• <b>ПриватБанк</b>: квитанція → «Поділитися» → код\n\n"
        f"Формат: <code>XXXX-XXXX-XXXX-XXXX</code>",
        reply_markup=kb_cancel()
    )
    await cb.answer()


# ── Введення коду квитанції ──────────────────────────────────────────────
@router.message(
    CheckGovState.entering_code,
    F.text.regexp(r'^[A-Za-zА-ЯҐЄІЇа-яґєії0-9]{4}[-\s][A-Za-zА-ЯҐЄІЇа-яґєії0-9]{4}[-\s][A-Za-zА-ЯҐЄІЇа-яґєії0-9]{4}[-\s][A-Za-zА-ЯҐЄІЇа-яґєії0-9]{4}$')
)
async def cgov_code_entered(msg: Message, state: FSMContext, bot: Bot):
    if is_banned(msg.from_user.id):
        return

    code = msg.text.strip().upper().replace(" ", "-")
    data = await state.get_data()
    bank = data.get("bank", "monobank")
    bank_label = data.get("bank_label", bank)
    user_id = msg.from_user.id

    if not _configured():
        await state.clear()
        return await msg.answer("⚠️ Оплата по квитанції тимчасово недоступна. Зверніться до підтримки.")

    # Перевірка на повторне використання (швидка; остаточний захист — claim_receipt нижче)
    if db.is_receipt_used(code):
        await msg.answer(
            "❌ <b>Цей код вже використано раніше.</b>\n\n"
            "Кожна квитанція може бути використана лише один раз.",
            parse_mode=ParseMode.HTML
        )
        return

    await state.clear()

    status_msg = await msg.answer(
        f"🔍 <b>Перевіряємо квитанцію...</b>\n\n"
        f"🏦 Банк: {bank_label}\n"
        f"🔑 Код: <code>{code}</code>\n\n"
        f"⏳ Це займе 15-30 секунд, зачекайте...",
        parse_mode=ParseMode.HTML
    )

    # Запускаємо перевірку
    try:
        result = await check_gov_ua_verify(code, bank)
    except Exception as e:
        logging.exception(f"check_gov_ua_verify error: {e}")
        await status_msg.edit_text(
            "⚠️ <b>Помилка під час перевірки.</b>\n\n"
            "Спробуйте пізніше або зверніться до підтримки.",
            parse_mode=ParseMode.HTML
        )
        return

    logging.info(f"[checkgov] user={user_id} code={code} result={result}")

    # ── Помилка з'єднання ───────────────────────────────────────────────
    if not result.get("ok"):
        err = result.get("error", "")
        if err == uapay.ERR_STUB:
            text = uapay.STUB_TEXT_UA
        elif err in ("playwright_not_installed", "playwright_browser_missing"):
            text = (
                "⚠️ <b>Сервіс перевірки не налаштований.</b>\n"
                "Зверніться до адміністратора."
            )
        else:
            text = (
                "⚠️ <b>Не вдалося перевірити квитанцію.</b>\n\n"
                "Можливі причини:\n"
                "• Сайт check.gov.ua тимчасово недоступний\n"
                "• Невірний код квитанції\n\n"
                "Спробуйте ще раз або зверніться до підтримки."
            )
        await status_msg.edit_text(text, parse_mode=ParseMode.HTML)
        return

    # ── Не оплачено ─────────────────────────────────────────────────────
    if not result.get("paid"):
        await status_msg.edit_text(
            "❌ <b>Квитанція не підтверджена.</b>\n\n"
            "Статус: не оплачено або квитанція не знайдена.\n\n"
            "Переконайтеся що:\n"
            "• Ви обрали правильний банк\n"
            "• Код введено вірно\n"
            "• Платіж вже пройшов (не в очікуванні)",
            parse_mode=ParseMode.HTML
        )
        return

    # ── Оплачено ────────────────────────────────────────────────────────
    amount = float(result.get("amount") or 0)
    recipient = result.get("recipient") or ""
    raw_data = result.get("raw_data", {})

    if not _recipient_ok(result):
        await status_msg.edit_text(
            "❌ <b>Квитанція не підходить.</b>\n\n"
            "Платіж зроблено не на наші реквізити. Якщо ви платили нам — зверніться до підтримки.",
            parse_mode=ParseMode.HTML)
        return
    if amount < 10:
        await status_msg.edit_text(
            "⚠️ <b>Не вдалося визначити суму платежу.</b>\n\nЗверніться до підтримки з кодом квитанції.",
            parse_mode=ParseMode.HTML)
        return

    # Займаємо квитанцію АТОМАРНО до зарахування: два паралельні запити не зарахують її двічі
    if not db.claim_receipt(code, user_id, amount):
        await status_msg.edit_text("❌ <b>Цей код вже використано раніше.</b>", parse_mode=ParseMode.HTML)
        return

    credited = round(amount * CHECK_RATE_TO_RUB, 2)
    db.add_balance(user_id, credited)
    db.add_topup(user_id, credited, f"check.gov.ua ({bank_label})")
    bal = db.balance(user_id)

    await status_msg.edit_text(
        f"✅ <b>Оплату підтверджено!</b>\n\n"
        f"💰 Квитанція: <b>{amount:.2f} ₴</b>\n"
        f"➕ Зараховано: <b>{credited:.2f} ₽</b>\n"
        f"💼 Поточний баланс: <b>{bal:.2f} ₽</b>\n\n"
        f"Дякуємо за оплату! 🎉",
        parse_mode=ParseMode.HTML
    )

    # ── Сповіщення адміністратора ────────────────────────────────────────
    username = msg.from_user.username
    uname_str = f"@{username}" if username else f"ID:{user_id}"
    full_name = msg.from_user.full_name or ""

    admin_text = (
        f"💳 <b>НОВА ОПЛАТА (check.gov.ua)</b>\n\n"
        f"👤 Користувач: {uname_str} ({full_name})\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🏦 Банк: {bank_label}\n"
        f"🔑 Квитанція: <code>{code}</code>\n"
        f"💰 Сума: <b>{amount:.2f} ₴</b> → {credited:.2f} ₽\n"
        f"📋 Одержувач: {recipient or '—'}\n"
        f"💼 Баланс клієнта: {bal:.2f} ₽"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
        except Exception:
            pass


@router.message(CheckGovState.entering_code)
async def cgov_invalid_code(msg: Message, state: FSMContext):
    """Невірний формат коду"""
    await msg.answer(
        "❌ Невірний формат коду.\n\n"
        "Код має виглядати так: <code>XXXX-XXXX-XXXX-XXXX</code>\n\n"
        "Скопіюйте код з додатку банку та надішліть ще раз.",
        parse_mode=ParseMode.HTML
    )
