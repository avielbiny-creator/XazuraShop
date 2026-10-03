"""
handlers/topup.py — пополнение: сумма (кнопкой или числом) → метод → оплата.
Ссылка на оплату — единственная inline-кнопка (reply-кнопки не умеют открывать URL).
"""
import re
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode

from config import EMOJI_SBP, EMOJI_CRYPTOBOT, ADMIN_IDS
from database import db
from payments import crypto_create_invoice, platega_create_payment, platega_is_configured
import uapay
import keyboards as K
from keyboards import B_TOPUP, B_SBP, B_CRYPTO, B_RECEIPT, B_BACK
import texts as T
from utils import TOPUP_PHOTO, answer_screen

router = Router()


class TopUp(StatesGroup):
    amount = State()
    method = State()


@router.message(F.text == B_TOPUP)
async def on_topup_menu(msg: Message, state: FSMContext):
    await state.set_state(TopUp.amount)
    await state.update_data(screen="topup_amount")
    await answer_screen(msg, T.txt_topup(), K.kb_topup_amounts(), TOPUP_PHOTO())


def _parse_amount(text: str) -> float | None:
    t = re.sub(r"[^\d.,]", "", text or "").replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v >= 10 else None


@router.message(TopUp.amount, F.text)
async def on_amount(msg: Message, state: FSMContext):
    if msg.text == B_BACK:          # перехватывает навигация, но на всякий случай
        await state.set_state(None)
        from handlers.shop import show_main
        return await show_main(msg, state)
    amount = _parse_amount(msg.text)
    if amount is None:
        return await msg.answer("❌ Введите сумму числом (минимум 10 ₽):")
    await state.update_data(topup_amount=amount, screen="topup_method")
    await state.set_state(TopUp.method)
    await answer_screen(msg, T.txt_payment_method(amount),
                        K.kb_payment_method(db.is_check_gov_ua_enabled()))


@router.message(TopUp.method, F.text == B_CRYPTO)
async def on_crypto(msg: Message, state: FSMContext, bot: Bot):
    amount = (await state.get_data()).get("topup_amount")
    if not amount:
        return await on_topup_menu(msg, state)
    uid = msg.from_user.id
    inv_id, pay_url = await crypto_create_invoice(amount, uid)
    if not inv_id or not pay_url:
        return await msg.answer("❌ Не удалось создать счёт Crypto Bot. Попробуйте позже или выберите СБП.")
    await state.set_state(None)
    db.add_pending(str(inv_id), uid, amount, "crypto")
    await msg.answer(
        f"{EMOJI_CRYPTOBOT} <b>ОПЛАТА ЧЕРЕЗ CRYPTO BOT</b>\n\n🪙 Сумма: <b>{amount:.1f} ₽</b>\n\n"
        "Нажмите кнопку, оплатите — баланс пополнится автоматически.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {amount:.0f} ₽", url=pay_url)]]))
    await msg.answer("Меню ⬇️", reply_markup=K.kb_main_menu(uid in ADMIN_IDS))


@router.message(TopUp.method, F.text == B_SBP)
async def on_sbp(msg: Message, state: FSMContext, bot: Bot):
    amount = (await state.get_data()).get("topup_amount")
    if not amount:
        return await on_topup_menu(msg, state)
    if not platega_is_configured():
        return await msg.answer("⚠️ Оплата по СБП временно недоступна. Выберите Crypto Bot.")
    uid = msg.from_user.id
    order_id, pay_url = await platega_create_payment(amount, uid)
    if not order_id or not pay_url:
        return await msg.answer("❌ Не удалось создать платёж СБП. Попробуйте позже или выберите Crypto Bot.")
    await state.set_state(None)
    db.add_pending(order_id, uid, amount, "sbp")
    await msg.answer(
        f"{EMOJI_SBP} <b>ОПЛАТА ПО СБП (Платёга)</b>\n\n🪙 Сумма: <b>{amount:.1f} ₽</b>\n\n"
        "Нажмите кнопку, оплатите — баланс пополнится автоматически.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {amount:.0f} ₽ по СБП", url=pay_url)]]))
    await msg.answer("Меню ⬇️", reply_markup=K.kb_main_menu(uid in ADMIN_IDS))


@router.message(TopUp.method, F.text == B_RECEIPT)
async def on_receipt(msg: Message, state: FSMContext):
    """Передаёт управление существующему модулю checkgov (он работает на inline-кнопках)."""
    await state.set_state(None)
    if uapay.is_stub():                          # заглушка: оплата из Украины пока не подключена
        await msg.answer(uapay.STUB_TEXT_RU, parse_mode=ParseMode.HTML)
        return await msg.answer("Меню ⬇️", reply_markup=K.kb_main_menu(msg.from_user.id in ADMIN_IDS))
    await msg.answer(
        "🧾 Оплата по квитанции: нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Начать проверку квитанции", callback_data="checkgov_start")]]))
    await msg.answer("Меню ⬇️", reply_markup=K.kb_main_menu(msg.from_user.id in ADMIN_IDS))
