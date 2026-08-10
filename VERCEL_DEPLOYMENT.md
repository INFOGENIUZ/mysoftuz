# 🚀 Vercel Deployment & Doimiy Ma'lumotlar Bazasi Yo'riqnomasi

## ⚠️ Nega Turso / SQLite bilan kiritilgan dasturlar Vercel deployida o'chib ketayotgan edi?

Ikki asosiy sabab bor edi:

1. **Koddagi blokirovka (Turso override xatosi):**
   Eski kodda (`engine.py` da) shunday shart yozilgan edi:
   `if "libsql" in db_url: db_url = "sqlite+aiosqlite:////tmp/software_bot.db"`
   Yani siz Turso (`libsql://...`) linkini Vercel-ga kiritganingizda ham, Python kodi Turso-ni **e'tiborsiz qoldirib**, majburiy ravishda Vercel-ning vaqtinchalik `/tmp/software_bot.db` fayliga ulanayotgan edi!

2. **Turso va Async Python mos kelmasligi:**
   Turso (`libsql`) bazasi Python-dagi asinxron SQLAlchemy (`create_async_engine` / `AsyncSession`) bilan rasman ishlamaydi (Async driveri mavjud emas). Vercel serverless konteynerida har safar deploy bo'lganda `/tmp` o'chirilgani uchun lokal SQLite saqlanmaydi.

---

## 💡 Yechim: Doimiy Bulutli Postgres Baza (Neon.tech yoki Supabase) Ulash

Ma'lumotlar har qanday re-deploy va restartlarda **hech qachon o'chib ketmasligi uchun** botimiz asinxron **PostgreSQL** (`asyncpg`) drayveriga to'liq o'tkazildi.

### 1-Usul: Neon.tech (Tavsiya etiladi - 1 daqiqada bepul bazasini olish mumkin)

1. **[Neon.tech](https://neon.tech)** saytiga kiring va GitHub orqali ro'yxatdan o'ting (bepul).
2. Yangi loyiha yarating (masalan: `mysoftuz-db`).
3. Neon sizga **Connection String** beradi. U quyidagicha ko'rinadi:
   `postgres://alex:Password123@ep-cool-name.us-east-2.aws.neon.tech/neondb?sslmode=require`

4. Vercel Dashboard-ga kiring:
   - Loyihangiz sozlamalariga kirib: **Settings -> Environment Variables** bo'limini oching.
   - `DATABASE_URL` o'zgaruvchisini Neon linki bilan yangilang:
     `postgresql+asyncpg://alex:Password123@ep-cool-name.us-east-2.aws.neon.tech/neondb`
   - **Save** bosing.

5. **Deploy** tugmasini bosing (yoki kodingizni GitHub-ga qayta push qiling).

---

### 2-Usul: Supabase (Muqobil bepul variant)

1. **[Supabase.com](https://supabase.com)** saytida bepul loyiha yarating.
2. **Project Settings -> Database** bo'limidan Connection string (URI) ni nusxalang.
3. Vercel-dagi `DATABASE_URL` o'zgaruvchisiga qo'ying:
   `postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres`

---

## 📋 Vercel-dagi Barcha Environment Variable-lar Ro'yxati

Vercel Settings -> Environment Variables bo'limida quyidagilar bo'lishi kerak:

| O'zgaruvchi | Qiymat misoli | Izoh |
| :--- | :--- | :--- |
| `BOT_TOKEN` | `123456789:ABCdefGhIJK...` | Telegram Bot Tokeni |
| `ADMIN_IDS` | `8887751785` | Admin Telegram ID-si |
| `ENVIRONMENT` | `production` | Rejim |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Neon / Supabase doimiy baza URI |

---

## 🔗 Telegram Webhook-ni Qayta Sozlash (Eslatma)

Deploy yakunlangach, Webhook-ni ulang:
```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_VERCEL_DOMAIN>.vercel.app/api/webhook
```

✅ Endi har safar Vercel-da kodni yangilasangiz ham yoki qayta deploy qilsangiz ham, barcha kiritilgan dasturlar va foydalanuvchilar **doimiy saqlanib qoladi**! 🚀
