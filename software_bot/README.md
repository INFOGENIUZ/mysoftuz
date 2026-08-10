# 💻 TELEGRAM SOFTWARE STORE BOT — 1-BOSQICH

Rasmiy va tarqatishga ruxsat etilgan kompyuter dasturlarini Telegram bot orqali topish, ko'rish va yuklab olish imkonini beruvchi bot loyihasi.

---

## 🏗 Loyiha Arxitekturasi

Ushbu 1-bosqichda loyihaning eng yuqori sifatli (production-ready) modullik, xavfsizlik va SOLID tamoyillariga asoslangan fondatsiyasi yaratildi:

```text
software_bot/
│
├── app/
│   ├── __init__.py
│   ├── bot.py                  # Bot, Dispatcher, Middlewares va Polling ni boshqarish
│   ├── config.py               # Pydantic Settings orqali .env faylni xavfsiz o'qish
│   ├── logging_config.py       # Professional va xavfsiz (secret leak-free) logging
│   │
│   ├── database/               # Async SQLAlchemy 2.x va aiosqlite tizimi
│   │   ├── __init__.py
│   │   ├── base.py             # DeclarativeBase
│   │   ├── engine.py           # Async Engine va SessionMaker
│   │   └── models/             # Barcha SQLAlchemy jadvallari
│   │       ├── __init__.py
│   │       ├── user.py         # Foydalanuvchilar jadvali
│   │       ├── admin.py        # Adminlar jadvali
│   │       ├── category.py     # Kategoriyalar jadvali
│   │       ├── program.py      # Dasturlar jadvali
│   │       ├── download.py     # Yuklab olishlar tarixi
│   │       └── bot_setting.py  # Bot sozlamalari
│   │
│   ├── handlers/               # Handlerlar va Routerlar
│   │   ├── __init__.py
│   │   ├── user/
│   │   │   ├── __init__.py
│   │   │   └── start.py        # Foydalanuvchi /start buyrug'i
│   │   └── admin/
│   │       ├── __init__.py
│   │       └── start.py        # Admin /admin buyrug'i
│   │
│   ├── keyboards/              # Telegram tugmalari
│   │   ├── __init__.py
│   │   ├── user/
│   │   │   ├── __init__.py
│   │   │   └── main_kb.py      # User ReplyKeyboard
│   │   └── admin/
│   │       ├── __init__.py
│   │       └── main_kb.py      # Admin ReplyKeyboard
│   │
│   ├── services/               # Biznes mantiq (Service Layer)
│   │   ├── __init__.py
│   │   ├── user_service.py     # Foydalanuvchilar bilan ishlash
│   │   ├── category_service.py # Kategoriyalar servisi
│   │   ├── program_service.py  # Dasturlar servisi
│   │   └── download_service.py # Yuklab olishlar servisi
│   │
│   ├── states/                 # FSM Holatlari
│   │   ├── __init__.py
│   │   ├── admin_category.py   # Admin Kategoriya FSM
│   │   └── admin_program.py    # Admin Dastur FSM
│   │
│   ├── middlewares/            # Middlewares
│   │   ├── __init__.py
│   │   └── admin.py            # AdminMiddleware
│   │
│   ├── filters/                # Maxsus filtrlar
│   │   ├── __init__.py
│   │   └── admin.py            # IsAdminFilter
│   │
│   └── utils/                  # Yordamchi instrumentlar
│       ├── __init__.py
│       ├── pagination.py       # Paginatsiya yordamchisi
│       └── validators.py       # Validatsiya funksiyalari
│
├── data/                       # Bazani saqlash papkasi (software_bot.db)
│   └── .gitkeep
├── tests/
│   └── __init__.py
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── run.py                      # Botni ishga tushirish nuqtasi
```

---

## ⚡️ O'rnatish va Ishga tushirish

### 1. Virtual Muhitni Yaratish va Faollashtirish

Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Kutubxonalarni O'rnatish

```bash
pip install -r requirements.txt
```

### 3. Environment Variables Sozlash

Loyihada `.env` faylini yaratib, quyidagi o'zgaruvchilarni kiriting:

```env
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_IDS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///data/software_bot.db
```

### 4. Botni Ishga Tushirish

```bash
python run.py
```

---

## 🔍 Self-Check & Quality Controls
- **SQLAlchemy 2.x async engine**: `init_db()` ishga tushganda `data/software_bot.db` va barcha jadvallar (`users`, `admins`, `categories`, `programs`, `downloads`, `bot_settings`) avtomatik yaratiladi.
- **Xavfsiz Logging**: Loglarda bot tokenlari yoki maxfiy ma'lumotlar oshkor qilinmaydi.
- **Pydantic Settings**: Vergul bilan ajratilgan admin ID larni `list[int]` turiga avtomatik o'tkazadi.
- **Strict UI Rules**: User va Admin uchun mos ravishda ajratilgan va standartlashtirilgan ReplyKeyboard tugmalari.
