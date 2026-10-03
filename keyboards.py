"""
keyboards.py — ВСЕ кнопки бота: это меню (ReplyKeyboard), которое
находится там же, где поле ввода текста.
Тексты кнопок вынесены в константы B_* — по ним работают хендлеры.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import countries as C

# ── Тексты кнопок ──────────────────────────────────────────
B_CATALOG    = "🛍 Каталог"
B_TG         = "✈️ Telegram аккаунты"
B_SUPPORT    = "🆘 Поддержка"
B_PROFILE    = "👤 Профиль"
B_TOPUP      = "💵 Пополнить"
B_ADMIN      = "🛠 Админ-панель"
B_BACK       = "← Назад"
B_HOME       = "🏠 Главное меню"
B_CANCEL     = "❌ Отмена"
B_BUY        = "✅ Подтвердить"
B_GETCODE    = "🔑 Получить код"
B_RESET      = "🔄 Сбросить сессию"
B_RESET_YES  = "✅ Да, сбросить"
B_REPLACE    = "📝 Заявка на замену"
B_MYACC      = "📱 Мои аккаунты"
B_HISTORY    = "🧾 История пополнений"
B_PROMO      = "🎟 Промокод"
B_REFERRAL   = "👥 Рефералы"
B_INFO       = "📚 Информация"
B_SBP        = "💳 СБП"
B_CRYPTO     = "🪙 Crypto Bot"
B_RECEIPT    = "🧾 Квитанция (Mono / Приват)"

# админ
A_STATS      = "📊 Статистика"
A_PRICES     = "💲 Цены"
A_LOLZ_BAL   = "💰 Баланс Lolz"
A_GIVE       = "💵 Начислить баланс"
A_USER       = "👤 Пользователь"
A_PROMO      = "🎟 Создать промокод"
A_BROADCAST  = "📢 Рассылка"
A_CGOV       = "🧾 Автопроверка квитанций"
A_BC_SEND    = "✅ Отправить всем"
A_BAN        = "🚫 Заблокировать"
A_UNBAN      = "✅ Разблокировать"
A_PROMO_BAL  = "💰 На баланс"
A_PROMO_DISC = "🏷 Скидка на покупку"


def _kb(rows: list[list[str]], placeholder: str | None = None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def kb_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [[B_CATALOG], [B_PROFILE, B_TOPUP], [B_SUPPORT]]
    if is_admin:
        rows.append([B_ADMIN])
    return _kb(rows)


def kb_catalog() -> ReplyKeyboardMarkup:
    return _kb([[B_TG], [B_BACK]])


def country_button(key: str, with_price: bool = True) -> str:
    """Кнопка товара: «🇺🇸 США · 49 ₽». Без цены — только «🇺🇸 США» (для админских списков)."""
    c = C.get(key)
    base = f"{c['flag']} {c['name']}"
    return f"{base} · {C.price(key)} ₽" if with_price else base


def kb_countries() -> ReplyKeyboardMarkup:
    btns = [country_button(k) for k in C.for_sale()]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append([B_BACK])
    return _kb(rows)


def kb_confirm(price: float) -> ReplyKeyboardMarkup:
    return _kb([[f"{B_BUY} · {price:g} ₽"], [B_CANCEL]])      # :g → «45 ₽», а не «45.0 ₽»


def kb_purchased() -> ReplyKeyboardMarkup:
    return _kb([[B_GETCODE], [B_RESET, B_REPLACE], [B_MYACC, B_HOME]])


def kb_reset_confirm() -> ReplyKeyboardMarkup:
    return _kb([[B_RESET_YES], [B_CANCEL]])


def kb_nofunds() -> ReplyKeyboardMarkup:
    return _kb([[B_TOPUP], [B_BACK]])


def kb_profile() -> ReplyKeyboardMarkup:
    return _kb([[B_MYACC], [B_HISTORY, B_PROMO], [B_REFERRAL, B_INFO], [B_BACK]])


def kb_accounts(labels: list[str]) -> ReplyKeyboardMarkup:
    rows = [[l] for l in labels]
    rows.append([B_BACK])
    return _kb(rows)


def kb_back_only() -> ReplyKeyboardMarkup:
    return _kb([[B_BACK]])


def kb_cancel_only() -> ReplyKeyboardMarkup:
    return _kb([[B_CANCEL]])


def kb_topup_amounts() -> ReplyKeyboardMarkup:
    return _kb([["100 ₽", "300 ₽"], ["500 ₽", "1000 ₽"], [B_BACK]],
               placeholder="Или введите сумму")


def kb_payment_method(receipt_enabled: bool) -> ReplyKeyboardMarkup:
    rows = [[B_SBP, B_CRYPTO]]
    if receipt_enabled:
        rows.append([B_RECEIPT])
    rows.append([B_BACK])
    return _kb(rows)


# ── Админ ──────────────────────────────────────────────────
def kb_admin_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [A_STATS, A_LOLZ_BAL],
        [A_GIVE, A_USER],
        [A_PROMO, A_PRICES],
        [A_BROADCAST, A_CGOV],
        [B_HOME],
    ])


def kb_admin_prices() -> ReplyKeyboardMarkup:
    """Все активные страны: «🇺🇸 США · 49 ₽» или «🇧🇩 Бангладеш · —» (цена не задана → клиентам не видна)."""
    btns = []
    for k in C.all_countries():
        p = C.price(k)
        btns.append(f"{country_button(k, False)} · {p} ₽" if p else f"{country_button(k, False)} · —")
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append(["← В админку"])
    return _kb(rows)


def kb_admin_back() -> ReplyKeyboardMarkup:
    return _kb([["← В админку"]])


def kb_admin_user() -> ReplyKeyboardMarkup:
    return _kb([[A_BAN, A_UNBAN], ["← В админку"]])


def kb_admin_promo_type() -> ReplyKeyboardMarkup:
    return _kb([[A_PROMO_BAL, A_PROMO_DISC], ["← В админку"]])


def kb_admin_broadcast_confirm() -> ReplyKeyboardMarkup:
    return _kb([[A_BC_SEND], ["← В админку"]])
