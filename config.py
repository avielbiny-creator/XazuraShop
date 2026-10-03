"""
config.py — настройки бота. Секреты берутся ТОЛЬКО из переменных окружения / .env
(см. .env.example). В коде никаких токенов не хранится.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Не задана переменная окружения {name} (см. .env.example)")
    return v


# ══════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════
BOT_TOKEN    = _req("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "XazuraShopBot").lstrip("@")
ADMIN_IDS    = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

SHOP_NAME         = "Xazura Shop"
SHOP_CHANNEL      = "@XazuraShop"      # тгк
REVIEWS_ACCOUNT   = "@XazuraRep"       # отзывы
SUPPORT_ACCOUNT   = "@Xazura"          # поддержка
REQUIRED_CHANNEL  = "@XazuraShop"      # обязательная подписка (бот должен быть АДМИНОМ этого канала)
REQUIRED_CHANNEL_URL = f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"

# ══════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════
SUPABASE_URL = _req("SUPABASE_URL")
SUPABASE_KEY = _req("SUPABASE_KEY")   # service_role

# ══════════════════════════════════════
# LOLZ MARKET (источник аккаунтов)
# Токен: lolz.live → Настройки → API, права: read + market
# ══════════════════════════════════════
LOLZ_TOKEN     = _req("LOLZ_TOKEN")
LOLZ_BASE_URL  = os.getenv("LOLZ_BASE_URL", "https://api.lzt.market")
# Наценка больше не используется: цена каждой страны задаётся в админке («💲 Цены»)
MARKUP_PERCENT = float(os.getenv("MARKUP_PERCENT", "30"))
# Фильтр спамблока на стороне Lolz: no = только без спамблока
LOLZ_SPAM      = os.getenv("LOLZ_SPAM", "no")
# Происхождение: autoreg (авторег) и self_registration (саморег) — именно так их зовёт Lolz.
# В Supabase (bot_settings.lolz_origins) можно переопределить. Старое "self_registered" лечится автоматически (lolz.normalize_origins).
LOLZ_ORIGINS   = [x.strip() for x in os.getenv("LOLZ_ORIGINS", "autoreg,self_registration").split(",") if x.strip()]
# Сколько аккаунтов (от самого дешёвого) пробуем купить на Lolz, если первые уже разобрали
MAX_BUY_TRIES = 5
GUARANTEE_HOURS = int(os.getenv("GUARANTEE_HOURS", "5"))

# ══════════════════════════════════════
# ПУТИ К ИЗОБРАЖЕНИЯМ
# ══════════════════════════════════════
IMAGES_DIR          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
SHOP_PHOTO_PATH     = os.path.join(IMAGES_DIR, "shop.jpg")
PROFILE_PHOTO_PATH  = os.path.join(IMAGES_DIR, "profile.jpg")
TOPUP_PHOTO_PATH    = os.path.join(IMAGES_DIR, "topup.jpg")
SUB_PHOTO_PATH      = os.path.join(IMAGES_DIR, "sub.jpg")
INFO_PHOTO_PATH     = os.path.join(IMAGES_DIR, "info.jpg")
SUPPORT_PHOTO_PATH  = os.path.join(IMAGES_DIR, "support.jpg")
TELEGRAM_PHOTO_PATH = os.path.join(IMAGES_DIR, "telegram.jpg")
CATALOG_PHOTO_PATH  = os.path.join(IMAGES_DIR, "catalog.jpg")

# ══════════════════════════════════════
# CRYPTO BOT
# ══════════════════════════════════════
CRYPTO_PAY_TOKEN    = os.getenv("CRYPTO_PAY_TOKEN", "")
CRYPTO_PAY_ASSET    = os.getenv("CRYPTO_PAY_ASSET", "USDT").upper()
CRYPTO_PAY_TESTNET  = os.getenv("CRYPTO_PAY_TESTNET", "0") == "1"
CRYPTO_PAY_BASE_URL = ("https://testnet-pay.crypt.bot/api" if CRYPTO_PAY_TESTNET
                       else "https://pay.crypt.bot/api")
CRYPTO_PAY_RETURN_URL       = f"https://t.me/{BOT_USERNAME}"
CRYPTO_RUB_TO_USDT_FALLBACK = 90.0

# ══════════════════════════════════════
# ПЛАТЁГА (СБП)
# ══════════════════════════════════════
PLATEGA_MERCHANT   = os.getenv("PLATEGA_MERCHANT", "ВСТАВЬ_MERCHANT_UUID")
PLATEGA_SECRET     = os.getenv("PLATEGA_SECRET",   "ВСТАВЬ_SECRET_KEY")
PLATEGA_BASE_URL   = "https://platega.io/api/v1"
PLATEGA_RETURN_URL = f"https://t.me/{BOT_USERNAME}"

# ══════════════════════════════════════
# CHECK.GOV.UA — перевірка квитанцій
# ══════════════════════════════════════
# Режим проверки: stub (заглушка, по умолчанию, Playwright не нужен) | playwright (реальная проверка, см. uapay.py)
CHECK_GOV_UA_MODE    = os.getenv("CHECK_GOV_UA_MODE", "stub").strip().lower()
CHECK_GOV_UA_ENABLED = os.getenv("CHECK_GOV_UA_ENABLED", "1") == "1"
CHECK_RECIPIENT_NAME = os.getenv("CHECK_RECIPIENT_NAME", "")
CHECK_CARD_NUMBER    = os.getenv("CHECK_CARD_NUMBER", "")
CHECK_FIXED_PRICE    = float(os.getenv("CHECK_FIXED_PRICE", "0"))
# Курс: сколько ₽ баланса давать за 1 ₴ квитанции. 0 = автозачисление по квитанциям ВЫКЛЮЧЕНО.
CHECK_RATE_TO_RUB    = float(os.getenv("CHECK_RATE_TO_RUB", "0"))

# ══════════════════════════════════════
# ССЫЛКИ
# ══════════════════════════════════════
# Документы (telegra.ph и т.п.). Пусто = строка в боте не показывается. Задаются в .env
DOC_RULES_URL   = os.getenv("DOC_RULES_URL", "").strip()
DOC_PRIVACY_URL = os.getenv("DOC_PRIVACY_URL", "").strip()
DOC_TERMS_URL   = os.getenv("DOC_TERMS_URL", "").strip()

# ══════════════════════════════════════
# СТРАНЫ: ключ → флаг, название, ISO-код для Lolz, телефонный код.
# Цены больше НЕ задаются здесь — берутся живьём с Lolz + наценка.
# Это ЗАПАСНОЙ список: основной лежит в Supabase (таблица shop_countries).
# ══════════════════════════════════════
COUNTRIES: dict[str, dict] = {
    "us": {"flag": "🇺🇸", "name": "США", "iso": "US", "code": "+1"},
    "mm": {"flag": "🇲🇲", "name": "Мьянма", "iso": "MM", "code": "+95"},
    "idn": {"flag": "🇮🇩", "name": "Индонезия", "iso": "ID", "code": "+62"},
    "ind": {"flag": "🇮🇳", "name": "Индия", "iso": "IN", "code": "+91"},
    "bd": {"flag": "🇧🇩", "name": "Бангладеш", "iso": "BD", "code": "+880"},
    "ph": {"flag": "🇵🇭", "name": "Филиппины", "iso": "PH", "code": "+63"},
    "vn": {"flag": "🇻🇳", "name": "Вьетнам", "iso": "VN", "code": "+84"},
    "br": {"flag": "🇧🇷", "name": "Бразилия", "iso": "BR", "code": "+55"},
    "pk": {"flag": "🇵🇰", "name": "Пакистан", "iso": "PK", "code": "+92"},
    "ng": {"flag": "🇳🇬", "name": "Нигерия", "iso": "NG", "code": "+234"},
    "eg": {"flag": "🇪🇬", "name": "Египет", "iso": "EG", "code": "+20"},
    "tr": {"flag": "🇹🇷", "name": "Турция", "iso": "TR", "code": "+90"},
    "kz": {"flag": "🇰🇿", "name": "Казахстан", "iso": "KZ", "code": "+7"},
    "uz": {"flag": "🇺🇿", "name": "Узбекистан", "iso": "UZ", "code": "+998"},
    "ca": {"flag": "🇨🇦", "name": "Канада", "iso": "CA", "code": "+1"},
    "mx": {"flag": "🇲🇽", "name": "Мексика", "iso": "MX", "code": "+52"},
    "co": {"flag": "🇨🇴", "name": "Колумбия", "iso": "CO", "code": "+57"},
    "ar": {"flag": "🇦🇷", "name": "Аргентина", "iso": "AR", "code": "+54"},
    "ke": {"flag": "🇰🇪", "name": "Кения", "iso": "KE", "code": "+254"},
    "th": {"flag": "🇹🇭", "name": "Таиланд", "iso": "TH", "code": "+66"},
    "my": {"flag": "🇲🇾", "name": "Малайзия", "iso": "MY", "code": "+60"},
    "kh": {"flag": "🇰🇭", "name": "Камбоджа", "iso": "KH", "code": "+855"},
    "np": {"flag": "🇳🇵", "name": "Непал", "iso": "NP", "code": "+977"},
    "et": {"flag": "🇪🇹", "name": "Эфиопия", "iso": "ET", "code": "+251"},
    "za": {"flag": "🇿🇦", "name": "ЮАР", "iso": "ZA", "code": "+27"},
    "pe": {"flag": "🇵🇪", "name": "Перу", "iso": "PE", "code": "+51"},
    "gb": {"flag": "🇬🇧", "name": "Великобритания", "iso": "GB", "code": "+44"},
    "de": {"flag": "🇩🇪", "name": "Германия", "iso": "DE", "code": "+49"},
    "ua": {"flag": "🇺🇦", "name": "Украина", "iso": "UA", "code": "+380"},
    "ru": {"flag": "🇷🇺", "name": "Россия", "iso": "RU", "code": "+7"},
}

# ══════════════════════════════════════
# ПРЕМИУМ ЭМОДЗИ
# ══════════════════════════════════════
PEPE         = '<tg-emoji emoji-id="5832260147073780752">🎩</tg-emoji>'
DIAMOND      = '<tg-emoji emoji-id="5262645856108057866">💎</tg-emoji>'
PLANE        = '<tg-emoji emoji-id="5398017375532498315">🛬</tg-emoji>'
USDT         = '<tg-emoji emoji-id="5201692367437974073">💵</tg-emoji>'
QUESTION     = '<tg-emoji emoji-id="5116240346656801621">❓</tg-emoji>'
SPARKLE_BALL = '<tg-emoji emoji-id="5341570033405412393">✨</tg-emoji>'
SPARKLE_STARS= '<tg-emoji emoji-id="5222108309795908493">✨</tg-emoji>'
BULB         = '<tg-emoji emoji-id="5397605449514106279">💡</tg-emoji>'

EMOJI_HEART      = '<tg-emoji emoji-id="5134476056241112076">❤️</tg-emoji>'
EMOJI_CHECK      = '<tg-emoji emoji-id="5123163417326126159">✅</tg-emoji>'
EMOJI_HAT        = '<tg-emoji emoji-id="5961042379212330511">👒</tg-emoji>'
EMOJI_BRAIN      = '<tg-emoji emoji-id="5859416770019856426">🧠</tg-emoji>'
EMOJI_BRIEFCASE  = '<tg-emoji emoji-id="5861996610845675576">💼</tg-emoji>'
EMOJI_SBP        = '<tg-emoji emoji-id="5233317199480891766">💳</tg-emoji>'
EMOJI_CRYPTOBOT  = '<tg-emoji emoji-id="5240072972584102832">💳</tg-emoji>'
