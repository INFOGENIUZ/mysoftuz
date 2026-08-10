# 🚀 Vercel Serverga Joylash Bo'yicha Yo'riqnoma (Vercel Deployment Guide)

Sizdagi **"Found main.py but it does not export a top-level app, application, or handler variable"** xatosi to'liq tuzatildi va loyiha Vercel Serverless (Webhook) rejimiga tayyorlandi.

---

## 🛠 Nimalar Tayyorlandi va O'zgartirildi?

1. **`api/index.py` yaratildi**: Vercel uchun Serverless FastAPI `app` (entrypoint) va `/api/webhook` endpointi sozlandi.
2. **`vercel.json` fayli yaratildi**: Vercel barcha kelayotgan so'rovlarni `api/index.py` ga yo'naltirishi uchun router sozlamalari yozildi.
3. **`main.py` yangilandi**: Endi u `app` o'zgaruvchisini export qiladi (Vercel talabiga moslab) hamda lokal rejimda polling (`python main.py`) bilan ham ishlashda davom etadi.
4. **`requirements.txt` to'ldirildi**: Vercel avtomatik o'rnatishi uchun `fastapi`, `uvicorn`, `aiogram`, `sqlalchemy`, `aiosqlite` va boshqa barcha kutubxonalar qo'shildi.

---

## 📋 Vercel-ga Joylash Ketma-ketligi

### 1-qadam: Kodni GitHub-ga yuklash (Push qilish)
Loyiha papkasida terminal orqali o'zgarishlarni commit va push qiling:
```bash
git add .
git commit -m "Configure Vercel serverless webhook deployment"
git push origin main
```

### 2-qadam: Vercel-da Loyiha Yaratish va Environment Variable-larni Kiriting
1. [Vercel Dashboard](https://vercel.com/dashboard) ga kiring va **Add New -> Project** bosing.
2. GitHub repozitoriyangizni tanlang (`My Bot` / `mysoftuz`).
3. **Environment Variables** bo'limida quyidagi o'zgaruvchilarni qo'shing:
   - `BOT_TOKEN`: Telegram bot tokeningiz (masalan: `123456789:ABC...`)
   - `ADMIN_IDS`: Admin Telegram ID laringiz (masalan: `123456789,987654321`)
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: `sqlite+aiosqlite:////tmp/software_bot.db` *(Vercel serverless-da SQLite fayli `/tmp` papkasiga yoziladi)*
4. **Deploy** tugmasini bosing.

---

## 🔗 3-qadam: Telegram Webhook-ni Sozlash

Vercel deployment muvaffaqiyatli yakunlangach, Vercel sizga domen beradi (masalan: `https://my-bot-name.vercel.app`).

Bot Telegram-dan xabarlarni Vercel serveringizga qabul qilishi uchun Webhook URL ulashingiz kerak.

Brauzeringizda quyidagi manzillardan birini oching (o'zingizning `BOT_TOKEN` va `VERCEL_DOMAIN` ni qo meb qo'ying):

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_VERCEL_DOMAIN>.vercel.app/api/webhook
```

**Masalan:**
`https://api.telegram.org/bot123456789:ABCdef.../setWebhook?url=https://my-bot-name.vercel.app/api/webhook`

Brauzerda quyidagi javob chiqishi kerak:
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

---

## 🔍 Webhook Holatini Tekshirish

Webhook to'g'ri ishlayotganini tekshirish uchun:
```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

Tabriklaymiz! Endi botingiz Vercel Serverless platformasida 24/7 ishlaydi. 🚀
