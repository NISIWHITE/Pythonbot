import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ========== 1. НАСТРОЙКИ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

MANAGER_ID = 896122548
PHONE = "+375 (29) 162-86-28"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

baskets = {}
users = {}

# ========== 2. БАЗА ДАННЫХ УСЛУГ ==========
SERVICES = {
    "Техобслуживание": {
        "t1": {"full_name": "Замена масла, масляного фильтра", "price": 30, "time": "около часа", "desc": "Замена старого, отработанного масла и грязного фильтра."},
        "t2": {"full_name": "Замена воздушного фильтра", "price": 20, "time": "20-30 минут", "desc": "Установка нового чистого фильтра вместо забитого пылью."},
        "t3": {"full_name": "Замена салонного фильтра", "price": 20, "time": "20-40 минут", "desc": "Обновление барьера, который очищает воздух в салоне."},
        "t4": {"full_name": "Замена тормозных колодок (комплект 4шт)", "price": 40, "time": "около часа", "desc": "Установка новых колодок вместо стёртых."},
        "t5": {"full_name": "Замена тормозных дисков (комплект 4шт)", "price": 70, "time": "около часа", "desc": "Установка новых дисков взамен изношенных."}
    },
    "Компьютерная диагностика": {
        "c1": {"full_name": "Диагностика ЭСУ", "price": 40, "time": "около 40 минут", "desc": "Компьютерная проверка всех электронных систем двигателя."},
        "c2": {"full_name": "Сброс ошибок", "price": 30, "time": "около 30 минут", "desc": "Очистка памяти бортового компьютера от кодов неисправностей."}
    },
    "Диагностика и ремонт подвески": {
        "p1": {"full_name": "Осмотр элементов подвески", "price": 20, "time": "около 30 минут", "desc": "Визуальная и механическая проверка всех элементов подвески."},
        "p2": {"full_name": "Замена рычагов подвески", "price": 50, "time": "от 1 часа", "desc": "Замена изношенных рычагов подвески на новые."},
        "p3": {"full_name": "Замена сайлентблоков на снятом рычаге", "price": 15, "time": "около 40 минут", "desc": "Замена резиновых втулок на снятом рычаге."},
        "p4": {"full_name": "Замена балочных сайлентблоков", "price": 120, "time": "около 1.5 часов", "desc": "Замена сайлентблоков задней балки."}
    },
    "Развал схождения": {
        "r1": {"full_name": "Регулировка развала схождения 1 оси", "price": 50, "time": "около 30 минут", "desc": "Настройка угла установки колёс на одной оси."},
        "r2": {"full_name": "Регулировка развала схождения 2х осей", "price": 55, "time": "около 45 минут", "desc": "Настройка углов установки колёс на обеих осях."}
    },
    "Заправка кондиционера": {
        "a1": {"full_name": "Заправка кондиционера", "price": 30, "time": "около 30 минут", "desc": "Дозаправка системы охлаждения хладагентом."},
        "a2": {"full_name": "Поиск утечки кондиционера", "price": 50, "time": "около часа", "desc": "Диагностика всей системы специальным оборудованием."}
    },
    "Диагностика и ремонт дизельных форсунок": {
        "f1": {"full_name": "Диагностика форсунок Common Rail", "price": 15, "time": "по запросу", "desc": "Профессиональная диагностика форсунок Common Rail."},
        "f2": {"full_name": "Диагностика однопружинных форсунок", "price": 6, "time": "по запросу", "desc": "Проверка состояния однопружинных механических форсунок."},
        "f3": {"full_name": "Диагностика двухпружинных форсунок", "price": 15, "time": "по запросу", "desc": "Проверка состояния двухпружинных механических форсунок."},
        "f4": {"full_name": "Ремонт однопружинных форсунок", "price": 35, "time": "по запросу", "desc": "Профессиональный ремонт однопружинных форсунок."},
        "f5": {"full_name": "Ремонт двухпружинных форсунок", "price": 75, "time": "по запросу", "desc": "Профессиональный ремонт двухпружинных форсунок."}
    }
}

# ========== 3. ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== 4. КЛАВИАТУРЫ ==========
def main_keyboard():
    buttons = [[KeyboardButton(text=section)] for section in SERVICES.keys()]
    buttons.append([KeyboardButton(text="🛒 Моя корзина"), KeyboardButton(text="🧹 Очистить корзину")])
    buttons.append([KeyboardButton(text="📞 Поделиться номером", request_contact=True)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== 5. ХЭНДЛЕРЫ КЛИЕНТА ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"username": message.from_user.username or "без юзернейма", "first_name": message.from_user.first_name or "без имени"}
    baskets[user_id] = []
    await state.clear()
    await message.answer(
        f"🖐️ Привет! Я помогу рассчитать стоимость работ по ремонту твоего авто.\n\n"
        f"📞 Телефон: {PHONE}\n📍 Адрес: {ADDRESS}\n\n"
        f"Выбери раздел из меню ниже, чтобы посмотреть услуги.",
        reply_markup=main_keyboard()
    )

@dp.message(F.text.in_(SERVICES.keys()))
async def select_section(message: types.Message):
    section = message.text
    await message.answer(f"📋 Раздел *{section}*. Выберите услугу:", parse_mode="Markdown")
    
    for key, item in SERVICES[section].items():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➕ Добавить за {item['price']} руб", callback_data=f"add_{key}")]
        ])
        await message.answer(
            f"🔹 *{item['full_name']}*\n⏱️ Время: {item['time']}\n📝 {item['desc']}",
            reply_markup=kb, parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("add_"))
async def add_to_basket(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    user_id = callback.from_user.id
    if user_id not in baskets:
        baskets[user_id] = []
    baskets[user_id].append(key)
    await callback.answer("✅ Добавлено в корзину!")

@dp.message(F.text == "🛒 Моя корзина")
async def show_basket(message: types.Message):
    user_id = message.from_user.id
    basket = baskets.get(user_id, [])
    if not basket:
        await message.answer("🛒 Ваша корзина пуста.")
        return

    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    for key in basket:
        for section, services in SERVICES.items():
            if key in services:
                text += f"• {services[key]['full_name']} — {services[key]['price']} руб.\n"
                total += services[key]['price']

    text += f"\n💰 *Итого работа: {total} руб.*"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🧹 Очистить корзину")
async def clear_basket(message: types.Message):
    baskets[message.from_user.id] = []
    await message.answer("🧹 Корзина полностью очищена.", reply_markup=main_keyboard())

@dp.callback_query(F.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    basket = baskets.get(user_id, [])
    if not basket:
        await callback.answer("Корзина пуста.")
        return

    text = f"🛒 *Новый заказ!*\n👤 Клиент: {callback.from_user.first_name} (@{callback.from_user.username or 'link'})\n🆔 ID: {user_id}\n\n📋 *Услуги:*\n"
    total = 0
    for key in basket:
        for section, services in SERVICES.items():
            if key in services:
                text += f"• {services[key]['full_name']} — {services[key]['price']} руб.\n"
                total += services[key]['price']
    text += f"\n💰 *Итого: {total} руб.*"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📞 Позвонить", url=f"tg://user?id={user_id}")]])

    try:
        await bot.send_message(chat_id=MANAGER_ID, text=text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка менеджеру: {e}")

    await callback.message.answer(f"📞 *Спасибо!* Заказ на сумму *{total} руб.* отправлен менеджеру.", reply_markup=main_keyboard(), parse_mode="Markdown")
    baskets[user_id] = []
    await callback.answer()

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users: users[user_id] = {}
    users[user_id]["phone"] = message.contact.phone_number
    await message.answer("✅ Телефон сохранен!", reply_markup=main_keyboard())
    try:
        await bot.send_message(chat_id=MANAGER_ID, text=f"📞 Контакт: {message.from_user.first_name}\n📱 `{message.contact.phone_number}`", parse_mode="Markdown")
    except: pass

@dp.message(Command("users"))
async def list_users(message: types.Message):
    if message.from_user.id != MANAGER_ID: return
    if not users: return await message.answer("Пусто.")
    text = "👥 *Пользователи:*\n"
    for uid, data in users.items():
        text += f"• {data.get('first_name')} — 📞 {data.get('phone', 'нет')}\n"
    await message.answer(text, parse_mode="Markdown")

# ========== 6. FASTAPI & LIFESPAN (WEBHOOK) ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info(f"Ставим Вебхук: {WEBHOOK_URL}")
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    yield
    await bot.delete_webhook()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root(): return {"status": "working"}

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return Response(status_code=200)
    except Exception as e:
        logging.error(f"Ошибка вебхука: {e}")
        return Response(status_code=500)
