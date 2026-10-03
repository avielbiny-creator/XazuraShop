"""
handlers/admin.py — компактная админ-панель (тоже кнопками в меню).
Пул аккаунтов / цены по странам / огр. товар больше не нужны: аккаунты берутся с Lolz,
цена каждой страны — фиксированная, задаётся здесь («💲 Цены»).
"""
import asyncio
import json
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.filters import Command

import lolz
import countries as C
from config import ADMIN_IDS
from database import db
import keyboards as K
from keyboards import (
    B_ADMIN, A_STATS, A_LOLZ_BAL, A_GIVE, A_USER, A_PROMO, A_PRICES, A_BROADCAST, A_CGOV,
    A_BC_SEND, A_BAN, A_UNBAN, A_PROMO_BAL, A_PROMO_DISC, B_HOME,
)

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))   # весь роутер только для админов

TO_ADMIN = "← В админку"


class Adm(StatesGroup):
    give_id = State()
    give_amount = State()
    user_query = State()
    user_actions = State()
    promo_type = State()
    promo_code = State()
    promo_value = State()
    promo_uses = State()
    price_pick = State()
    price_value = State()
    bc_text = State()
    bc_confirm = State()


async def show_admin(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("🛠 <b>АДМИН-ПАНЕЛЬ</b>", parse_mode=ParseMode.HTML, reply_markup=K.kb_admin_menu())


@router.message(F.text == B_HOME)
async def on_home_from_admin(msg: Message, state: FSMContext):
    """Выход из любого админ-диалога в главное меню."""
    from handlers.shop import show_main
    await show_main(msg, state)


@router.message(F.text == B_ADMIN)
@router.message(Command("admin"))
@router.message(F.text == TO_ADMIN)
async def on_admin(msg: Message, state: FSMContext):
    await show_admin(msg, state)


# ── Статистика / Lolz ─────────────────────────────────────
@router.message(F.text == A_STATS)
async def on_stats(msg: Message):
    s = db.stats()
    await msg.answer(
        f"📊 <b>СТАТИСТИКА</b>\n\n👥 Пользователей: {s['users']}\n🛒 Покупок: {s['purchases']}\n"
        f"💰 Выручка: {s['revenue']:.0f} ₽\n💲 Стран в продаже: {len(C.for_sale(force=True))}",
        parse_mode=ParseMode.HTML)


@router.message(F.text == A_LOLZ_BAL)
async def on_lolz_balance(msg: Message):
    try:
        bal = await lolz.my_balance()
        await msg.answer(f"💰 Баланс на Lolz Market: <b>{bal:.2f} ₽</b>\n"
                         f"Пополняйте его заранее — с него бот покупает аккаунты.",
                         parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.answer(f"❌ Не удалось получить баланс Lolz: {e}")


@router.message(Command("lolz_debug"))
async def on_lolz_debug(msg: Message):
    """Диагностика: показывает реальные поля Lolz, чтобы проверить фильтры страны/спамблока."""
    await msg.answer("Запрашиваю Lolz…")
    try:
        params = await lolz.raw_get("/telegram/params")
        keys = json.dumps(params, ensure_ascii=False)[:1500]
        await msg.answer(f"<b>/telegram/params</b>\n<pre>{keys}</pre>", parse_mode=ParseMode.HTML)
        # Тест поиска: США — без фильтров / только спам=no / текущие настройки бота.
        try:
            lines = []
            for title, kw in (
                ("без фильтров", {"origins": [], "spam": ""}),
                ("спам=no", {"origins": [], "spam": "no"}),
                ("как в боте", {}),
            ):
                r = await lolz.probe_search("US", **kw)
                lines.append(f"{title}: всего {r['total']}, на 1-й стр. {r['returned']}")
            used = ", ".join(lolz.normalize_origins(db.get_lolz_origins())) or "—"
            await msg.answer("<b>Тест поиска (США)</b>\n<pre>" + "\n".join(lines) +
                             f"\norigin в боте: {used}</pre>", parse_mode=ParseMode.HTML)
        except Exception as e:
            await msg.answer(f"❌ Тест поиска: {e!r}")
        data = await lolz.raw_get("/telegram", {"order_by": "price_to_up", "currency": "rub"})
        items = data.get("items") or []
        if items:
            it = items[0]
            keep = {k: v for k, v in it.items()
                    if k.startswith("telegram") or k in ("item_id", "title", "price", "item_state", "loginData")}
            await msg.answer(f"<b>Пример аккаунта</b>\n<pre>{json.dumps(keep, ensure_ascii=False, indent=1)[:3000]}</pre>",
                             parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.answer(f"❌ {e!r}")


# ── Начислить баланс ──────────────────────────────────────
@router.message(F.text == A_GIVE)
async def on_give(msg: Message, state: FSMContext):
    await state.set_state(Adm.give_id)
    await msg.answer("Введите Telegram ID пользователя:", reply_markup=K.kb_admin_back())


@router.message(Adm.give_id, F.text)
async def on_give_id(msg: Message, state: FSMContext):
    if not msg.text.strip().lstrip("-").isdigit() or not db.find_user_by_id(int(msg.text)):
        return await msg.answer("❌ Пользователь не найден. Введите ID ещё раз:")
    await state.update_data(target=int(msg.text))
    await state.set_state(Adm.give_amount)
    await msg.answer("Сумма (₽, можно отрицательную для списания):")


@router.message(Adm.give_amount, F.text)
async def on_give_amount(msg: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(msg.text.replace(",", "."))
    except ValueError:
        return await msg.answer("❌ Введите число:")
    target = (await state.get_data())["target"]
    db.add_balance(target, amount)
    await msg.answer(f"✅ Баланс {target}: {db.balance(target):.1f} ₽", reply_markup=K.kb_admin_menu())
    if amount > 0:
        try:
            await bot.send_message(target, f"💰 Вам начислено +{amount:.0f} ₽")
        except Exception:
            pass
    await state.clear()


# ── Пользователь: поиск / бан ─────────────────────────────
@router.message(F.text == A_USER)
async def on_user(msg: Message, state: FSMContext):
    await state.set_state(Adm.user_query)
    await msg.answer("Введите ID или @username:", reply_markup=K.kb_admin_back())


@router.message(Adm.user_query, F.text)
async def on_user_query(msg: Message, state: FSMContext):
    q = msg.text.strip()
    u = db.find_user_by_id(int(q)) if q.isdigit() else db.find_user_by_username(q.lstrip("@"))
    if not u:
        return await msg.answer("❌ Не найден. Попробуйте ещё раз:")
    await state.update_data(target=u["user_id"])
    await state.set_state(Adm.user_actions)
    await msg.answer(
        f"👤 <b>{u['user_id']}</b> @{u.get('username') or '—'}\n💰 {float(u.get('balance', 0)):.1f} ₽\n"
        f"🛒 Покупок: {u.get('purchases_count', 0)}\n📅 {u.get('reg_date', '')}\n✅ {u.get('status')}",
        parse_mode=ParseMode.HTML, reply_markup=K.kb_admin_user())


@router.message(Adm.user_actions, F.text.in_({A_BAN, A_UNBAN}))
async def on_user_action(msg: Message, state: FSMContext):
    target = (await state.get_data())["target"]
    db.set_user_status(target, "Заблокирован" if msg.text == A_BAN else "Активен")
    await msg.answer("✅ Готово", reply_markup=K.kb_admin_menu())
    await state.clear()


# ── Промокод ──────────────────────────────────────────────
@router.message(F.text == A_PROMO)
async def on_promo(msg: Message, state: FSMContext):
    await state.set_state(Adm.promo_type)
    await msg.answer("Тип промокода:", reply_markup=K.kb_admin_promo_type())


@router.message(Adm.promo_type, F.text.in_({A_PROMO_BAL, A_PROMO_DISC}))
async def on_promo_type(msg: Message, state: FSMContext):
    await state.update_data(ptype="balance" if msg.text == A_PROMO_BAL else "discount")
    await state.set_state(Adm.promo_code)
    await msg.answer("Введите код (например SUMMER):", reply_markup=K.kb_admin_back())


@router.message(Adm.promo_code, F.text)
async def on_promo_code(msg: Message, state: FSMContext):
    await state.update_data(code=msg.text.strip())
    await state.set_state(Adm.promo_value)
    await msg.answer("Сумма в ₽ (бонус на баланс / скидка):")


@router.message(Adm.promo_value, F.text)
async def on_promo_value(msg: Message, state: FSMContext):
    try:
        v = float(msg.text.replace(",", "."))
    except ValueError:
        return await msg.answer("❌ Введите число:")
    await state.update_data(value=v)
    await state.set_state(Adm.promo_uses)
    await msg.answer("Сколько активаций максимум?")


@router.message(Adm.promo_uses, F.text)
async def on_promo_uses(msg: Message, state: FSMContext):
    if not msg.text.strip().isdigit():
        return await msg.answer("❌ Введите целое число:")
    d = await state.get_data()
    db.add_promo(d["code"], d["value"], int(msg.text), ptype=d["ptype"])
    await msg.answer(f"✅ Промокод <b>{d['code']}</b> создан.", parse_mode=ParseMode.HTML,
                     reply_markup=K.kb_admin_menu())
    await state.clear()


# ── Цены по странам ───────────────────────────────────────
def _price_key_by_button(text: str) -> str | None:
    for k in C.all_countries():
        base = K.country_button(k, with_price=False)
        if text == base or text.startswith(base + " · "):
            return k
    return None


async def _show_price_list(msg: Message, note: str = ""):
    C.for_sale(force=True)      # свежие страны и цены
    await msg.answer(
        f"{note}💲 <b>ЦЕНЫ ПО СТРАНАМ</b>\n\nВыберите страну, чтобы задать цену (₽).\n"
        f"«—» = цена не задана → клиенты эту страну не видят.",
        parse_mode=ParseMode.HTML, reply_markup=K.kb_admin_prices())


@router.message(F.text == A_PRICES)
async def on_prices(msg: Message, state: FSMContext):
    await state.set_state(Adm.price_pick)
    await _show_price_list(msg)


@router.message(Adm.price_pick, F.text)
async def on_price_pick(msg: Message, state: FSMContext):
    key = _price_key_by_button(msg.text)
    if not key:
        return await msg.answer("Выберите страну кнопкой ⬇️")
    ci = C.get(key)
    cur = C.price(key)
    await state.update_data(price_key=key)
    await state.set_state(Adm.price_value)
    await msg.answer(
        f"{ci['flag']} <b>{ci['name']}</b>\nСейчас: {f'{cur} ₽' if cur else 'не задана'}\n\n"
        f"Введите цену в ₽ (целое число). <b>0</b> — скрыть страну от клиентов.\n"
        f"Например: 49",
        parse_mode=ParseMode.HTML, reply_markup=K.kb_admin_back())


@router.message(Adm.price_value, F.text)
async def on_price_value(msg: Message, state: FSMContext):
    raw = msg.text.strip().replace("₽", "").replace(",", ".").strip()
    try:
        v = float(raw)
        assert v >= 0 and v == int(v) and v <= 1_000_000
    except (ValueError, AssertionError):
        return await msg.answer("❌ Введите целое число ≥ 0 (например 49):")
    key = (await state.get_data())["price_key"]
    ci = C.get(key)
    C.set_price(key, int(v))
    await state.set_state(Adm.price_pick)
    note = (f"✅ {ci['flag']} {ci['name']}: <b>{int(v)} ₽</b>\n\n" if v
            else f"✅ {ci['flag']} {ci['name']}: скрыта от клиентов\n\n")
    await _show_price_list(msg, note)


# ── Рассылка ──────────────────────────────────────────────
@router.message(F.text == A_BROADCAST)
async def on_bc(msg: Message, state: FSMContext):
    await state.set_state(Adm.bc_text)
    await msg.answer("Отправьте текст рассылки (HTML разрешён):", reply_markup=K.kb_admin_back())


@router.message(Adm.bc_text, F.text)
async def on_bc_text(msg: Message, state: FSMContext):
    await state.update_data(bc=msg.text)
    await state.set_state(Adm.bc_confirm)
    await msg.answer(f"Предпросмотр:\n\n{msg.text}\n\nОтправить всем?",
                     parse_mode=ParseMode.HTML, reply_markup=K.kb_admin_broadcast_confirm())


@router.message(Adm.bc_confirm, F.text == A_BC_SEND)
async def on_bc_send(msg: Message, state: FSMContext, bot: Bot):
    text = (await state.get_data())["bc"]
    await state.clear()
    ok = fail = 0
    for uid in db.get_all_user_ids():
        try:
            await bot.send_message(uid, text, parse_mode=ParseMode.HTML)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await msg.answer(f"📢 Готово: доставлено {ok}, ошибок {fail}", reply_markup=K.kb_admin_menu())


# ── check.gov.ua ──────────────────────────────────────────
@router.message(F.text == A_CGOV)
async def on_cgov(msg: Message):
    new = not db.is_check_gov_ua_enabled()
    db.set_check_gov_ua_enabled(new)
    await msg.answer(f"🧾 Автопроверка квитанций: {'✅ включена' if new else '❌ выключена'}")
