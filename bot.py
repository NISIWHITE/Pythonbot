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
PHONE = "+375 29 888 4777"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

# Глобальный словарь для хранения корзин пользователей
baskets = {}

# Четкое сопоставление текста на кнопках с внутренними кодами
SECTION_MAP = {
    "🔧 Техобслуживание": "tech",
    "💻 Компьютерная диагностика": "comp",
    "🛞 Диагностика и ремонт подвески": "susp",
    "📐 Развал схождения": "wheel",
    "❄️ Заправка кондиционера": "ac",
    "⛽ Диагностика и ремонт дизельных форсунок": "diesel"
}

# Для обратного вывода названий в интерфейсе
CODE_TO_NAME = {
    "tech": "Техобслуживание",
    "comp": "Компьютерная диагностика",
    "susp": "Диагностика и ремонт подвески",
    "wheel": "Развал схождения",
    "ac": "Заправка кондиционера",
    "diesel": "Диагностика и ремонт дизельных форсунок"
}

SECTION_ICONS = {
    "tech": "🔧", "comp": "💻", "susp": "🛞", "wheel": "📐", "ac": "❄️", "diesel": "⛽"
}

# ========== 3. СТРУКТУРА УСЛУГ ==========
SERVICES = {
    "tech": {
        "t1": {"full_name": "Замена масла и масляного фильтра", "price": "30 руб.", "price_num": 30, "time": "около часа", "desc": "Замена старого, отработанного масла и грязного фильтра на свежие."},
        "t2": {"full_name": "Замена воздушного фильтра", "price": "20 руб.", "price_num": 20, "time": "около 20-30 минут", "desc": "Установка нового чистого фильтра вместо забитого пылью."},
        "t3": {"full_name": "Замена салонного фильтра", "price": "20 руб.", "price_num": 20, "time": "около 20-40 минут", "desc": "Обновление барьера, который очищает воздух в салоне."},
        "t4": {"full_name": "Замена тормозных колодок", "price": "40 руб.", "price_num": 40, "time": "около часа", "desc": "Установка новых колодок вместо стёртых."},
        "t5": {"full_name": "Замена тормозных дисков", "price": "70 руб.", "price_num": 70, "time": "около часа", "desc": "Установка новых дисков взамен изношенных."}
    },
    "comp": {
        "c1": {"full_name": "Диагностика ЭСУД", "price": "40 руб.", "price_num": 40, "time": "около 40 минут", "desc": "Компьютерная проверка всех электронных систем двигателя."},
        "c2": {"full_name": "Сброс ошибок", "price": "30 руб.", "price_num": 30, "time": "около 30 минут", "desc": "Очистка памяти бортового компьютера от кодов неисправностей после ремонта."}
    },
    "susp": {
        "p1": {"full_name": "Осмотр элементов подвески", "price": "20 руб.", "price_num": 20, "time": "около 30 минут", "desc": "Визуальная и механическая проверка элементов подвески на износ."},
        "p2": {"full_name": "Замена рычагов подвески", "price": "от 50 руб.", "price_num": 50, "time": "от 1 часа", "desc": "Профессиональный демонтаж старых поврежденных рычагов и установка новых."},
        "p3": {"full_name": "Замена сайлентблоков на снятом рычаге", "price": "15 руб.", "price_num": 15, "time": "около 40 минут", "desc": "Качественная выпрессовка старых и запрессовка новых элементов."},
        "p4": {"full_name": "Замена балочных сайлентблоков", "price": "от 120 руб.", "price_num": 120, "time": "около 1.5 часов", "desc": "Замена сайлентблоков задней или передней балки автомобиля."}
    },
    "wheel": {
        "r1": {"full_name": "Регулировка развала схождения 1 оси", "price": "50 руб.", "price_num": 50, "time": "около 30 минут (живая очередь)", "desc": "Настройка углов установки колёс, чтобы машина ехала строго прямо."},
        "r2": {"full_name": "Регулировка развала схождения 2х осей", "price": "55 руб.", "price_num": 55, "time": "около 45 минут (живая очередь)", "desc": "Полная настройка передней и задней оси автомобиля."}
    },
    "ac": {
        "a1": {"full_name": "Заправка кондиционера", "price": "30 руб.", "price_num": 30, "time": "около 30 минут", "desc": "Дозаправка системы охлаждения хладагентом взамен утерянного за сезон."},
        "a2": {"full_name": "Поиск утечки кондиционера", "price": "50 руб.", "price_num": 50, "time": "около часа", "desc": "Диагностика всей системы специальным оборудованием и УФ-фонариком."}
    },
    "diesel": {
        "f1": {"full_name": "Диагностика форсунок Common Rail", "price": "15 руб. за шт.", "price_num": 15, "time": "по запросу", "desc": "Комплексный тест параметров работы высокоточных дизельных форсунок на стенде."},
        "f2": {"full_name": "Диагностика однопружинных форсунок", "price": "6 руб. за шт.", "price_num": 6, "time": "по запросу", "desc": "Проверка давления открытия распылителя и качества факела распыла."},
        "f3": {"full_name": "Диагностика двухпружинных форсунок", "price": "15 руб. за шт.", "price_num": 15, "time": "по запросу", "desc": "Проверка параметров работы двухступенчатых механических дизельных форсунок."},
        "f4": {"full_name": "Ремонт однопружинных форсунок", "price": "35 руб. за шт.", "price_num": 35, "time": "по запросу", "desc": "Разборка, очистка, замена внутренних элементов и точная калибровка."},
        "f5": {"full_name": "Ремонт двухпружинных форсунок", "price": "75 руб. за шт.", "price_num": 75, "time": "по запросу", "desc": "Профессиональное восстановление геометрии и калибровка ступеней впрыска."}
    }
}

# ========== 4. СОСТОЯНИЯ (FSM) ==========
class OrderState(StatesGroup):
    waiting_for_phone = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== 6. ГЛАВНОЕ МЕНЮ ==========
def main_keyboard():
    buttons = [[KeyboardButton(text=text)] for text in SECTION_MAP.keys()]
    buttons.append([KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="🗑 Очистить")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== 7. КОМАНДА /start ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id not in baskets:
        baskets[user_id] = []
        
    await message.answer(
        f"🖐️ *Добро пожаловать в Магнат Сервис!*\n\n"
        f"🚗 Я помогу вам рассчитать стоимость ремонта вашего авто.\n\n"
        f"📞 Телефон: `{PHONE}`\n"
        f"📍 Адрес: `{ADDRESS}`\n\n"
        f"👇 *Выберите раздел из меню ниже:*",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ========== 8. ОБРАБОТКА МЕНЮ ==========
@dp.message(F.text)
async def handle_menu(message: types.Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id
    
    # Проверяем, нажал ли пользователь на категорию услуг
    if text in SECTION_MAP:
        code = SECTION_MAP[text]
        await show_section_services(message, code)
        return
            
    if text == "🛒 Корзина":
        await show_basket_msg(message)
    elif text == "🗑 Очистить":
        baskets[user_id] = []
        await message.answer("🧹 Корзина очищена!", reply_markup=main_keyboard())
    else:
        await message.answer("❓ Пожалуйста, выберите раздел из меню ниже.", reply_markup=main_keyboard())

# Список позиций в подразделе
async def show_section_services(message: types.Message, code: str):
    services = SERVICES[code]
    icon = SECTION_ICONS.get(code, "📌")
    section_name = CODE_TO_NAME.get(code, "Услуги")
    
    buttons = []
    for key, item in services.items():
        buttons.append([InlineKeyboardButton(text=item['full_name'], callback_data=f"view_{key}")])
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="back_to_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        f"{icon} *{section_name}*\n\n"
        f"Выберите интересующую услугу ниже для просмотра подробностей:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ========== 9. КАРТОЧКА ПОЗИЦИИ ==========
@dp.callback_query(F.data.startswith("view_"))
async def view_service(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    
    found_item = None
    found_code = None
    for code, services in SERVICES.items():
        if key in services:
            found_item = services[key]
            found_code = code
            break
            
    if not found_item:
        await callback.answer("Услуга не найдена.")
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Добавить в 🛒", callback_data=f"add_{key}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"sect_{found_code}")]
    ])
    
    await callback.message.edit_text(
        f"🔹 *{found_item['full_name']}*\n\n"
        f"📝 *Описание:* {found_item['desc']}\n\n"
        f"⏱️ *Занимает времени:* {found_item['time']}\n"
        f"💰 *Стоимость работы:* {found_item['price']}\n\n"
        f"Желаете добавить данную позицию в заказ?",
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
    
    service_name = ""
    found_code = ""
    for code, services in SERVICES.items():
        if key in services:
            service_name = services[key]['full_name']
            found_code = code
            break
            
    total = sum_price(user_id)
    
    await callback.answer(f"✅ Добавлено!")
    await callback.message.edit_text(
        f"✅ Услуга *«{service_name}»* добавлена в корзину!\n\n"
        f"📦 Всего в корзине: {len(baskets[user_id])} поз.\n"
        f"💰 Общая сумма: {total} руб.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="go_to_basket")],
            [InlineKeyboardButton(text="🔙 К списку услуг", callback_data=f"sect_{found_code}")]
        ]),
        parse_mode="Markdown"
    )

def sum_price(user_id):
    total = 0
    for key in baskets.get(user_id, []):
        for code, services in SERVICES.items():
            if key in services:
                total += services[key]['price_num']
                break
    return total

# ========== 11. КНОПКИ НАЗАД ==========
@dp.callback_query(F.data.startswith("sect_"))
async def back_to_section(callback: types.CallbackQuery):
    code = callback.data.split("_")[1]
    await show_section_services(callback.message, code)
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📋 Выберите раздел услуг:", reply_markup=main_keyboard())
    await callback.answer()

# ========== 12. КОРЗИНА ==========
@dp.callback_query(F.data == "go_to_basket")
async def go_to_basket_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    basket = baskets.get(user_id, [])
    
    if not basket:
        await callback.message.edit_text("🛒 Ваша корзина пуста. Выберите услуги в меню!")
        await callback.answer()
        return
        
    text = "🛒 *Ваша корзина (выбранные услуги):*\n\n"
    total = 0
    for key in basket:
        for code, services in SERVICES.items():
            if key in services:
                item = services[key]
                text += f"🔹 *{item['full_name']}*\n"
                text += f"📝 {item['desc']}\n"
                text += f"⏱️ _Время:_ {item['time']}\n"
                text += f"💰 _Цена работы:_ {item['price']}\n"
                text += "—" * 15 + "\n"
                total += item['price_num']
                break
                
    text += f"\n💰 *Итого ориентировочно: {total} руб.*"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="start_checkout")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_basket")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

async def show_basket_msg(message: types.Message):
    user_id = message.from_user.id
    basket = baskets.get(user_id, [])
    
    if not basket:
        await message.answer("🛒 Ваша корзина пуста. Выберите услуги в меню!", reply_markup=main_keyboard())
        return
        
    text = "🛒 *Ваша корзина (выбранные услуги):*\n\n"
    total = 0
    for key in basket:
        for code, services in SERVICES.items():
            if key in services:
                item = services[key]
                text += f"🔹 *{item['full_name']}*\n"
                text += f"📝 {item['desc']}\n"
                text += f"⏱️ _Время:_ {item['time']}\n"
                text += f"💰 _Цена работы:_ {item['price']}\n"
                text += "—" * 15 + "\n"
                total += item['price_num']
                break
                
    text += f"\n💰 *Итого ориентировочно: {total} руб.*"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="start_checkout")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_basket")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "clear_basket")
async def clear_basket_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    baskets[user_id] = []
    await callback.message.edit_text("🧹 Корзина очищена!")
    await callback.message.answer("📋 Выберите раздел:", reply_markup=main_keyboard())
    await callback.answer()

# ========== 13. ОФОРМЛЕНИЕ ЗАКАЗА ==========
@dp.callback_query(F.data == "start_checkout")
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not baskets.get(user_id, []):
        await callback.answer("Ваша корзина пуста.")
        return
        
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], 
        resize_keyboard=True
    )
    
    await callback.message.answer(
        "📱 Пожалуйста, введите ваш *номер телефона* текстом (например, +37529XXXXXXX), "
        "чтобы наш менеджер мог с вами связаться:",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )
    await state.set_state(OrderState.waiting_for_phone)
    await callback.answer()

# ========== ИСПРАВЛЕННЫЙ ОБРАБОТЧИК ТЕЛЕФОНА ==========
@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Обработка отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Оформление отменено.", reply_markup=main_keyboard())
        return
        
    # Проверяем, что введен номер телефона (хоть что-то)
    if not message.text or len(message.text) < 5:
        await message.answer("❌ Пожалуйста, введите корректный номер телефона (например, +37529XXXXXXX)")
        return
        
    user_phone = message.text
    basket = baskets.get(user_id, [])
    
    if not basket:
        await message.answer("❌ Ваша корзина пуста. Оформление отменено.", reply_markup=main_keyboard())
        await state.clear()
        return
    
    text = f"🛒 *Новый заказ!*\n\n"
    text += f"👤 Клиент: {message.from_user.first_name} (@{message.from_user.username or 'без юзернейма'})\n"
    text += f"📞 Телефон: `{user_phone}`\n"
    text += f"🆔 ID: `{user_id}`\n\n"
    text += f"📋 *Выбранные услуги:*\n"
    
    total = 0
    for key in basket:
        for code, services in SERVICES.items():
            if key in services:
                text += f"🔹 {services[key]['full_name']} — {services[key]['price']}\n"
                total += services[key]['price_num']
                break
                
    text += f"\n💰 *Итого: {total} руб.*"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Открыть профиль", url=f"tg://user?id={user_id}")]
    ])
    
    try:
        await bot.send_message(chat_id=MANAGER_ID, text=text, reply_markup=kb, parse_mode="Markdown")
        await message.answer(
            f"✅ *Заказ успешно оформлен!*\n\n"
            f"💰 Общая сумма: *{total} руб.*\n"
            f"📞 Менеджер свяжется с вами по номеру `{user_phone}` в ближайшее время.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        baskets[user_id] = []
    except Exception as e:
        logging.error(f"Ошибка при отправке заказа менеджеру: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке заявки. Пожалуйста, свяжитесь со СТО напрямую по телефону.",
            reply_markup=main_keyboard()
        )
        
    await state.clear()

# ========== 14. FASTAPI СЕРВЕР ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info(f"Ставим Вебхук: {WEBHOOK_URL}")
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    yield
    await bot.delete_webhook()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "working", "message": "Магнат Сервис Бот работает!"}

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
