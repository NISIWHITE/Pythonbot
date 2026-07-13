import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ========== 1. НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

MANAGER_ID = 8967378534
PHONE = "+375 (29) 888-47-77"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

baskets = {}
users = {}

# ========== 2. КРАСИВЫЕ ИКОНКИ ДЛЯ РАЗДЕЛОВ ==========
SECTION_ICONS = {
    "Техобслуживание": "🔧",
    "Компьютерная диагностика": "💻",
    "Диагностика и ремонт подвески": "🛞",
    "Развал схождения": "📐",
    "Заправка кондиционера": "❄️",
    "Диагностика и ремонт дизельных форсунок": "⛽"
}

# ========== 3. УСЛУГИ ==========
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

# ========== 4. СОСТОЯНИЯ ==========
class Form(StatesGroup):
    waiting_section = State()

# ========== 5. БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== 6. КРАСИВОЕ ГЛАВНОЕ МЕНЮ ==========
def main_keyboard():
    buttons = []
    for section in SERVICES.keys():
        icon = SECTION_ICONS.get(section, "📌")
        buttons.append([KeyboardButton(text=f"{icon} {section}")])
    buttons.append([KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="🗑 Очистить")])
    buttons.append([KeyboardButton(text="📞 Поделиться номером", request_contact=True)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== 7. КОМАНДА /start ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {
            "username": message.from_user.username or "без юзернейма",
            "first_name": message.from_user.first_name or "без имени"
        }
    baskets[user_id] = []
    await state.clear()
    
    await message.answer(
        f"🖐️ *Добро пожаловать в Магнат Сервис!*\n\n"
        f"🚗 Я помогу вам рассчитать стоимость ремонта вашего авто.\n\n"
        f"📞 Телефон: `{PHONE}`\n"
        f"📍 Адрес: `{ADDRESS}`\n\n"
        f"👇 *Выберите раздел из меню ниже:*",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ========== 8. ВЫБОР РАЗДЕЛА ==========
@dp.message(F.text)
async def handle_menu(message: types.Message, state: FSMContext):
    text = message.text
    
    for section in SERVICES.keys():
        icon = SECTION_ICONS.get(section, "📌")
        if text == section or text == f"{icon} {section}":
            await show_section_services(message, section)
            return
    
    if text == "🛒 Корзина":
        await show_basket(message)
    elif text == "🗑 Очистить":
        baskets[message.from_user.id] = []
        await message.answer("🧹 Корзина очищена!", reply_markup=main_keyboard())
    else:
        await message.answer(
            "❓ Пожалуйста, выберите раздел из меню ниже.",
            reply_markup=main_keyboard()
        )

async def show_section_services(message: types.Message, section: str):
    services = SERVICES[section]
    icon = SECTION_ICONS.get(section, "📌")
    
    buttons = []
    for i, (key, item) in enumerate(services.items(), 1):
        buttons.append([InlineKeyboardButton(
            text=f"{i}. {item['full_name']} — {item['price']} руб.",
            callback_data=f"view_{key}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        f"{icon} *{section}*\n\n"
        f"Выберите услугу:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ========== 9. ПРОСМОТР УСЛУГИ ==========
@dp.callback_query(F.data.startswith("view_"))
async def view_service(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    
    found_item = None
    found_section = None
    for section, services in SERVICES.items():
        if key in services:
            found_item = services[key]
            found_section = section
            break
    
    if not found_item:
        await callback.answer("Услуга не найдена.")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Добавить ({found_item['price']} руб)", callback_data=f"add_{key}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_{found_section}")]
    ])
    
    await callback.message.edit_text(
        f"🔹 *{found_item['full_name']}*\n\n"
        f"📝 Описание: {found_item['desc']}\n\n"
        f"⏱️ Время: {found_item['time']}\n"
        f"💰 Цена: *{found_item['price']} руб.*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== 10. ДОБАВЛЕНИЕ В КОРЗИНУ ==========
@dp.callback_query(F.data.startswith("add_"))
async def add_to_basket(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if user_id not in baskets:
        baskets[user_id] = []
    
    baskets[user_id].append(key)
    
    service_name = key
    found_section = "Техобслуживание"  # Дефолтное значение безопасности
    for section, services in SERVICES.items():
        if key in services:
            service_name = services[key]['full_name']
            found_section = section
            break
    
    total = sum_price(user_id)
    
    await callback.answer(f"✅ Добавлено: {service_name}!")
    await callback.message.edit_text(
        f"✅ *{service_name}* добавлен в корзину!\n\n"
        f"📦 В корзине: {len(baskets[user_id])} позиций\n"
        f"💰 Сумма: {total} руб.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="go_to_basket")],
            [InlineKeyboardButton(text="🔙 Назад к услугам", callback_data=f"back_{found_section}")]
        ]),
        parse_mode="Markdown"
    )

def sum_price(user_id):
    total = 0
    for key in baskets.get(user_id, []):
        for section, services in SERVICES.items():
            if key in services:
                total += services[key]['price']
                break
    return total

# ========== 11. НАЗАД ==========
@dp.callback_query(F.data.startswith("back_"))
async def back_to_section(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]
    await show_section_services(callback.message, section)
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🖐️ *Главное меню*\n\n"
        "Выберите раздел из меню ниже:",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback.message.answer(
        "📋 Выберите раздел:",
        reply_markup=main_keyboard()
    )
    await callback.answer()

# ========== 12. КОРЗИНА ==========
@dp.callback_query(F.data == "go_to_basket")
async def go_to_basket(callback: types.CallbackQuery):
    await show_basket(callback.message)
    await callback.answer()

async def show_basket(message: types.Message):
    user_id = message.from_user.id
    basket = baskets.get(user_id, [])
    
    if not basket:
        await message.answer("🛒 Корзина пуста.", reply_markup=main_keyboard())
        return
    
    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    for i, key in enumerate(basket, 1):
        for section, services in SERVICES.items():
            if key in services:
                text += f"{i}. {services[key]['full_name']} — {services[key]['price']} руб.\n"
                total += services[key]['price']
                break
    
    text += f"\n💰 *Итого: {total} руб.*"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_basket")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "clear_basket")
async def clear_basket_callback(callback: types.CallbackQuery):
    baskets[callback.from_user.id] = []
    await callback.message.edit_text("🧹 Корзина очищена!")
    await callback.message.answer("📋 Выберите раздел:", reply_markup=main_keyboard())
    await callback.answer()

# ========== 13. ОФОРМЛЕНИЕ ЗАКАЗА ==========
@dp.callback_query(F.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    basket = baskets.get(user_id, [])
    
    if not basket:
        await callback.answer("Корзина пуста.")
        return
    
    text = f"🛒 *Новый заказ!*\n\n"
    text += f"👤 Клиент: {callback.from_user.first_name} (@{callback.from_user.username or 'без юзернейма'})\n"
    text += f"🆔 ID: `{user_id}`\n\n"
    text += f"📋 *Услуги:*\n"
    
    total = 0
    for i, key in enumerate(basket, 1):
        for section, services in SERVICES.items():
            if key in services:
                text += f"{i}. {services[key]['full_name']} — {services[key]['price']} руб.\n"
                total += services[key]['price']
                break
    
    text += f"\n💰 *Итого: {total} руб.*"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Позвонить клиенту", url=f"tg://user?id={user_id}")]
    ])
    
    try:
        await bot.send_message(chat_id=MANAGER_ID, text=text, reply_markup=kb, parse_mode="Markdown")
        await callback.message.edit_text(
            f"✅ *Заказ оформлен!*\n\n"
            f"💰 Сумма: *{total} руб.*\n\n"
            f"📞 Менеджер свяжется с вами в ближайшее время.",
            reply_markup=None,
            parse_mode="Markdown"
        )
        await callback.message.answer("📋 Выберите раздел:", reply_markup=main_keyboard())
    except Exception as e:
        logging.error(f"Ошибка менеджеру: {e}")
        await callback.message.answer("❌ Ошибка при отправке заказа. Попробуйте позже.")
    
    baskets[user_id] = []
    await callback.answer()

# ========== 14. КОНТАКТ ==========
@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {}
    users[user_id]["phone"] = message.contact.phone_number
    await message.answer("✅ Телефон сохранён!", reply_markup=main_keyboard())
    
    try:
        await bot.send_message(
            chat_id=MANAGER_ID,
            text=f"📞 *Новый контакт!*\n\n"
                 f"👤 {message.from_user.first_name} (@{message.from_user.username or 'без юзернейма'})\n"
                 f"📱 `{message.contact.phone_number}`",
            parse_mode="Markdown"
        )
    except:
        pass

# ========== 15. АДМИН-КОМАНДЫ ==========
@dp.message(Command("users"))
async def list_users(message: types.Message):
    if message.from_user.id != MANAGER_ID:
        return
    if not users:
        await message.answer("📭 Нет пользователей.")
        return
    
    text = "👥 *Список пользователей:*\n\n"
    for uid, data in users.items():
        phone = data.get('phone', 'не указан')
        text += f"• {data.get('first_name', 'Без имени')} (@{data.get('username', '')}) — 📞 {phone}\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id != MANAGER_ID:
        return
    
    total_users = len(users)
    active_baskets = len([b for b in baskets.values() if b])
    
    await message.answer(
        f"📊 *Статистика бота:*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🛒 Активных корзин: {active_baskets}",
        parse_mode="Markdown"
    )

# ========== 16. FASTAPI ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info(f"Ставим Вебхук: {WEBHOOK_URL}")
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    yield
    await bot.delete_webhook()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# Хэндлер для обычного перехода в браузере (GET)
@app.get("/")
async def root():
    return {"status": "working", "message": "Магнат Сервис Бот работает!"}

# Хэндлер для пинга от Render (HEAD), чтобы сервер не уходил в бесконечный рестарт
@app.head("/")
async def root_head():
    return Response(status_code=200)

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
