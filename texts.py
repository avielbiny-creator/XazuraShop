"""
texts.py — все тексты экранов.
"""
from config import (
    PEPE, DIAMOND, PLANE, USDT, QUESTION, SPARKLE_BALL, SPARKLE_STARS,
    EMOJI_HEART, EMOJI_CHECK, EMOJI_HAT, EMOJI_BRAIN, EMOJI_BRIEFCASE,
    SHOP_CHANNEL, REVIEWS_ACCOUNT, SUPPORT_ACCOUNT,
    DOC_RULES_URL, DOC_PRIVACY_URL, DOC_TERMS_URL,
    BOT_USERNAME, GUARANTEE_HOURS,
)
import html
import countries as C


def _docs_lines() -> str:
    """Ссылки на документы — только те, что заданы в .env (иначе строки нет)."""
    rows = []
    if DOC_RULES_URL:
        rows.append(f"{EMOJI_HAT} <b>Правила магазина</b> — <a href=\"{DOC_RULES_URL}\">тут</a>")
    if DOC_PRIVACY_URL:
        rows.append(f"{EMOJI_BRAIN} <b>Политика конфиденциальности</b> — <a href=\"{DOC_PRIVACY_URL}\">тут</a>")
    if DOC_TERMS_URL:
        rows.append(f"{EMOJI_BRIEFCASE} <b>Пользовательское соглашение</b> — <a href=\"{DOC_TERMS_URL}\">тут</a>")
    return "\n".join(rows)


def txt_shop() -> str:
    docs = f"\n{_docs_lines()}" if _docs_lines() else ""
    return (
        f"{PEPE} <b>XAZURA SHOP</b> — твой надёжный поставщик в мире Telegram\n\n"
        f"{EMOJI_CHECK} <b>Физ. акки</b>\n• Автовыдача 24/7\n"
        f"• Живой подбор аккаунтов в реальном времени\n• Быстрая выдача кода\n\n"
        f"{EMOJI_HEART} Канал — {SHOP_CHANNEL}\n"
        f"{EMOJI_HEART} Отзывы — {REVIEWS_ACCOUNT}\n"
        f"{EMOJI_HEART} Поддержка — {SUPPORT_ACCOUNT}"
        f"{docs}"
    )


def txt_subscribe(first_name: str) -> str:
    return (f"Привет, {html.escape(first_name)}!\n\nЧтобы пользоваться ботом — подпишись на канал "
            f"{SHOP_CHANNEL} и нажми кнопку «✅ Я подписался».")


def txt_catalog() -> str:
    return f"{DIAMOND} <b>КАТАЛОГ</b>\n\nВыберите категорию:"


def txt_countries() -> str:
    return (f"{DIAMOND} <b>TELEGRAM АККАУНТЫ</b>\n\n"
            f"Выберите страну — цена указана на кнопке.\n"
            f"Новорег · без спамблока · автовыдача 24/7")


def txt_no_products() -> str:
    return (f"{DIAMOND} <b>TELEGRAM АККАУНТЫ</b>\n\n❌ Сейчас нет доступных товаров. "
            f"Загляните позже.")


def txt_confirm(ci: dict, price: int, discount: float = 0) -> str:
    final = price - discount
    disc = f"\n🏷 Скидка промокода: -{discount:.0f} ₽ (к оплате {final:.0f} ₽)" if discount else ""
    return (
        f"{QUESTION} <b>Вы действительно хотите купить аккаунт "
        f"{ci['flag']} {ci['name']} новорег без спамблока за {price} ₽?</b>\n\n"
        f"🌍 Страна: {ci['name']} [{ci['code']}]\n"
        f"🆕 Тип: новорег\n"
        f"🛡 Спамблок: нет\n"
        f"💰 Цена: <b>{price} ₽</b>{disc}\n\n"
        f"✅ Гарантия {GUARANTEE_HOURS} ч · авто-выдача · мгновенный код\n"
        f"⚠️ Используйте VPN/Proxy соответствующей страны"
    )


TXT_NO_ACCOUNT = "❌ <b>Нет аккаунта.</b>\n\nСейчас нет подходящего аккаунта. Попробуйте позже."
TXT_NO_ACCOUNTS = "❌ <b>Аккаунтов нету.</b>\n\nПо этой стране сейчас ничего нет в наличии. Попробуйте позже."


def txt_support() -> str:
    return (
        f"{DIAMOND} <b>ПОДДЕРЖКА</b>\n\n"
        f"Возник вопрос или проблема с аккаунтом? Напишите нам:\n\n"
        f"{EMOJI_HEART} Поддержка — {SUPPORT_ACCOUNT}\n"
        f"{EMOJI_HEART} Канал — {SHOP_CHANNEL}\n"
        f"{EMOJI_HEART} Отзывы — {REVIEWS_ACCOUNT}"
    )


def txt_nofunds(bal: float, need: float) -> str:
    return (f"❌ <b>Недостаточно средств</b>\n\n🪙 Баланс: {bal:.1f} ₽\n"
            f"{USDT} К оплате: {need:.1f} ₽\n❌ Не хватает: {need - bal:.2f} ₽")


def txt_topup() -> str:
    return (f"{USDT} <b>ПОПОЛНИТЬ БАЛАНС</b>\n\nВыберите сумму кнопкой "
            f"или введите свою (минимум 10 ₽):")


def txt_payment_method(amount: float) -> str:
    return f"{QUESTION} <b>Выберите способ оплаты</b>\n\n🪙 Сумма: <b>{amount:.1f} ₽</b>"


def txt_purchase_ready(ci: dict, phone: str, guar: str) -> str:
    return (
        f"{SPARKLE_STARS} <b>ПОКУПКА УСПЕШНА!</b>\n\n"
        f"{ci['flag']} <b>{ci['name']} [{ci['code']}]</b>\n\n"
        f"📱 <b>Ваш номер:</b> <code>{html.escape(str(phone))}</code>\n"
        f"⏰ Гарантия до: {guar}\n\n"
        f"1) Откройте Telegram и введите номер\n"
        f"2) Нажмите «🔑 Получить код» в меню ⬇️"
    )


def txt_purchase_code(ci: dict, phone: str, code: str, guar: str) -> str:
    return (
        f"{SPARKLE_STARS} <b>КОД ПОЛУЧЕН</b>\n\n"
        f"{ci['flag']} <b>{ci['name']} [{ci['code']}]</b>\n\n"
        f"📱 <b>Номер:</b> <code>{html.escape(str(phone))}</code>\n"
        f"🔑 <b>Код:</b> <code>{html.escape(str(code))}</code>\n\n"
        f"⏰ Гарантия до: {guar}"
    )


def txt_acc_detail(p: dict) -> str:
    ci = C.get(p["country_code"]) or {"flag": "🌍", "name": "?"}
    return (
        f"{PEPE} <b>XAZURA SHOP</b>\n{ci['flag']} <b>{ci['name']}</b>\n"
        f"{PLANE} Покупка: {str(p['purchase_date']).split()[0]}\n\n"
        f"📱 Номер: <code>{html.escape(str(p['phone_number']))}</code>\n"
        f"⏰ Гарантия до: {p['guaranteed_until']}\n\n"
        f"Нажмите «🔑 Получить код» для актуального кода."
    )


def txt_my_accounts(purchases: list[dict]) -> str:
    if not purchases:
        return f"{PEPE} <b>МОИ АККАУНТЫ</b>\n\nУ вас пока нет покупок."
    return f"{PEPE} <b>МОИ АККАУНТЫ</b>\n\nВыберите аккаунт кнопкой в меню ⬇️"


def txt_profile(u: dict) -> str:
    reg = str(u.get("reg_date", "")).split()[0]
    return (
        f"{DIAMOND} <b>ПРОФИЛЬ</b>\n\n"
        f"Аккаунт: @{u.get('username') or 'не указан'}\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"💰 Баланс: {float(u.get('balance', 0)):.1f} ₽\n"
        f"📅 Регистрация: {reg}\n"
        f"✅ Статус: {u.get('status', 'Активен')}"
    )


def txt_useful_info() -> str:
    docs = f"\n\n{_docs_lines()}" if _docs_lines() else ""
    return (
        f"📚 <b>Информация</b>\n\n"
        f"{DIAMOND} <b>Поддержка:</b> {SUPPORT_ACCOUNT}\n"
        f"{EMOJI_HEART} <b>Канал:</b> {SHOP_CHANNEL}\n"
        f"{EMOJI_HEART} <b>Отзывы:</b> {REVIEWS_ACCOUNT}"
        f"{docs}"
    )


def txt_referral(u: dict) -> str:
    return (
        f"{SPARKLE_STARS} <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n\n"
        f"Пригласи друга и получай бонус.\n\n"
        f"🔗 <b>Твоя ссылка:</b>\nhttps://t.me/{BOT_USERNAME}?start={u['user_id']}\n\n"
        f"💰 За каждую покупку приглашённого — <b>5 ₽</b> на баланс."
    )
