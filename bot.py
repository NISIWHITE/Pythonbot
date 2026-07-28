import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ============================================================
# 1. НАСТРОЙКИ
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

MANAGER_ID = 8967378534
PHONE = "+375 29 888 4777"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

# ============================================================
# 2. ХРАНЕНИЕ ДАННЫХ
# ============================================================
baskets = {}       # {user_id: [service_keys]}
profiles = {}      # {user_id: {"name": "", "car_brand": "", "car_model": "", ...}}
orders_history = {} # {user_id: [{"date": "", "services": [], "total": 0}]}

# ============================================================
# 3. СОСТОЯНИЯ (FSM)
# ============================================================
class ProfileState(StatesGroup):
    waiting_for_name = State()
    waiting_for_car_brand = State()
    waiting_for_car_model = State()
    waiting_for_car_year = State()
    waiting_for_vin = State()
    waiting_for_plate = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_value = State()

class OrderState(StatesGroup):
    waiting_for_phone = State()

# ============================================================
# 4. МЕНЮ И РАЗДЕЛЫ
# ============================================================
SECTION_MAP = {
    "🔧 Техобслуживание": "tech",
    "💻 Компьютерная диагностика": "comp",
    "🛞 Диагностика и ремонт подвески": "susp",
    "📐 Развал схождения": "wheel",
    "❄️ Заправка кондиционера": "ac",
    "⛽ Диагностика и ремонт дизельных форсунок": "diesel"
}

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

# ============================================================
# 5. УСЛУГИ
# ============================================================
SERVICES = {
    "tech": {
        "t1": {"full_name": "Замена масла и масляного фильтра", "price": "30 руб.", "price_num": 30, "time": "около часа", "desc": "Замена старого, отработанного масла и грязного фильтра на свежие."},
        "t2": {"full_name": "Замена воздушного фильтра", "price": "20 руб.", "price_num": 20, "time": "около 20-30 минут", "desc": "Установка нового чистого фильтра вместо забитого пылью."},
        "t3": {"full_name": "Замена салонного фильтра", "price": "20 руб.", "price_num": 20, "time": "около 20-40 минут", "desc": "Обновление барьера, который очищает воздух в салоне."},
        "t4": {"full_name": "Замена тормозных колодок", "price": "40 руб.", "price_num": 40, "time": "около часа", "desc": "Установка новых колодок вместо стёртых."},
        "t5": {"full_name": "Замена тормозных дисков", "price": "70 руб.", "price_num": 70, "time": "около часа", "desc": "Установка новых дисков взамен изношенных."}
    },
    "comp": {
        "c1": {"full_name": "Диагностика ЭСУ", "price": "30 руб.", "price_num": 30, "time": "около 40 минут", "desc": "Компьютерная проверка всех электронных систем двигателя."},
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

# ============================================================
# 6. ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# 7. ГЛАВНОЕ МЕНЮ
# ============================================================
def main_keyboard():
    buttons = [[KeyboardButton(text=text)] for text in SECTION_MAP.keys()]
    buttons.append([KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="🗑 Очистить")])
    buttons.append([KeyboardButton(text="📞 Поделиться номером", request_contact=True)])
    buttons.append([KeyboardButton(text="👤 Мой профиль")])
    buttons.append([KeyboardButton(text="📜 Мои заказы")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def show_main_menu(message: types.Message, state: FSMContext):
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

# ============================================================
# 8. /start — СОЗДАНИЕ ПРОФИЛЯ
# ============================================================
# ============================================================
# 8. /start — СОЗДАНИЕ ИЛИ ВХОД В ПРОФИЛЬ
# ============================================================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    # ПРИНУДИТЕЛЬНО чистим старые зависшие состояния FSM
    await state.clear()
    
    user_id = message.from_user.id
    
    # Инициализируем корзину, если её нет
    if user_id not in baskets:
        baskets[user_id] = []
        
    # Если профиля нет в памяти — запускаем анкетирование
    if user_id not in profiles:
        profiles[user_id] = {} # Сразу создаем пустой подсловарь
        await message.answer(
            f"🖐️ *Добро пожаловать в Магнат Сервис!*\n\n"
            f"Давайте познакомимся! Я создам ваш профиль.\n\n"
            f"✏️ *Введите ваше имя:*",
            parse_mode="Markdown"
        )
        await state.set_state(ProfileState.waiting_for_name)
        return
    
    # Если профиль уже есть — просто показываем главное меню
    await show_main_menu(message, state)

# ============================================================
# 9. ЗАПОЛНЕНИЕ ПРОФИЛЯ
# ============================================================
@dp.message(ProfileState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    profiles[user_id]["name"] = message.text
    
    await message.answer(
        f"✅ Отлично, {message.text}!\n\n"
        f"🚗 *Теперь укажите марку вашего автомобиля:*\n"
        f"(например, Toyota, BMW, Volkswagen)",
        parse_mode="Markdown"
    )
    await state.set_state(ProfileState.waiting_for_car_brand)
# ============================================================
# 10. ПРОФИЛЬ
# ============================================================
@dp.message(Command("profile"))
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id not in profiles:
        await message.answer("❌ Профиль не найден. Напишите /start, чтобы создать его.")
        return
    
    profile_text = (
        f"👤 *Ваш профиль:*\n\n"
        f"👤 Имя: {profiles[user_id].get('name', 'не указано')}\n"
        f"🚗 Марка: {profiles[user_id].get('car_brand', 'не указана')}\n"
        f"📐 Модель: {profiles[user_id].get('car_model', 'не указана')}\n"
        f"📅 Год: {profiles[user_id].get('car_year', 'не указан')}\n"
        f"🔢 VIN: {profiles[user_id].get('vin', 'не указан')}\n"
        f"🔢 Госномер: {profiles[user_id].get('plate', 'не указан')}\n"
        f"📞 Телефон: {profiles[user_id].get('phone', 'не указан')}\n\n"
        f"📜 Заказов: {len(orders_history.get(user_id, []))}\n\n"
        f"Для изменения данных нажмите '✏️ Редактировать профиль' в меню"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(F.text == "👤 Мой профиль")
async def profile_button(message: types.Message):
    await show_profile(message)

@dp.message(F.text == "✏️ Редактировать профиль")
async def edit_profile_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in profiles:
        await message.answer("❌ Профиль не найден. Напишите /start, чтобы создать его.")
        return
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Изменить имя")],
            [KeyboardButton(text="✏️ Изменить марку")],
            [KeyboardButton(text="✏️ Изменить модель")],
            [KeyboardButton(text="✏️ Изменить год")],
            [KeyboardButton(text="✏️ Изменить VIN")],
            [KeyboardButton(text="✏️ Изменить госномер")],
            [KeyboardButton(text="🔙 Назад в меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("✏️ Что хотите изменить?", reply_markup=kb)
    await state.set_state(ProfileState.waiting_for_edit_choice)

@dp.message(ProfileState.waiting_for_edit_choice)
async def process_edit_choice(message: types.Message, state: FSMContext):
    field_map = {
        "✏️ Изменить имя": "name",
        "✏️ Изменить марку": "car_brand",
        "✏️ Изменить модель": "car_model",
        "✏️ Изменить год": "car_year",
        "✏️ Изменить VIN": "vin",
        "✏️ Изменить госномер": "plate"
    }
    
    if message.text == "🔙 Назад в меню":
        await state.clear()
        await show_main_menu(message, state)
        return
    
    if message.text in field_map:
        await state.update_data(edit_field=field_map[message.text])
        await message.answer(
            f"✏️ Введите новое значение для *{message.text.replace('✏️ Изменить ', '')}*:",
            parse_mode="Markdown"
        )
        await state.set_state(ProfileState.waiting_for_edit_value)

@dp.message(ProfileState.waiting_for_edit_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    field = data.get("edit_field")
    
    if field:
        profiles[user_id][field] = message.text
        await message.answer(f"✅ Поле успешно обновлено!")
    
    await state.clear()
    await show_profile(message)

# ============================================================
# 11. ИСТОРИЯ ЗАКАЗОВ
# ============================================================
@dp.message(F.text == "📜 Мои заказы")
async def show_orders_button(message: types.Message):
    await show_orders(message)

@dp.message(Command("orders"))
async def show_orders(message: types.Message):
    user_id = message.from_user.id
    orders = orders_history.get(user_id, [])
    
    if not orders:
        await message.answer("📭 У вас пока нет заказов.", reply_markup=main_keyboard())
        return
    
    text = f"📜 *Ваши заказы:*\n\n"
    for i, order in enumerate(reversed(orders[-5:]), 1):
        text += f"{i}. {order['date']} — {order['total']} руб.\n"
        text += f"   Услуг: {len(order['services'])}\n"
    
    text += f"\nВсего заказов: {len(orders)}"
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard())

# ============================================================
# 12. ОБРАБОТКА МЕНЮ
# ============================================================
@dp.message(F.text)
async def handle_menu(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith("ProfileState:"):
        return
    if current_state == OrderState.waiting_for_phone:
        return
    
    text = message.text
    user_id = message.from_user.id
    
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
        f"{icon} *{section_name}*\n\nВыберите интересующую услугу ниже для просмотра подробностей:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ============================================================
# 13. КАРТОЧКА УСЛУГИ
# ============================================================
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

# ===========================================================
# ========== ДОПИШИ ЭТО В САМЫЙ КОНЕЦ ФАЙЛА bot.py ==========

# Вспомогательная функция для подсчета суммы (нужна для корзины)
def sum_price(user_id):
    total = 0
    for key in baskets.get(user_id, []):
        for code, services in SERVICES.items():
            if key in services:
                total += services[key]['price_num']
                break
    return total

# Функция для отображения сообщения корзины
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

# Настройка жизненного цикла FastAPI (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info(f"Ставим Вебхук: {WEBHOOK_URL}")
    await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    yield
    await bot.delete_webhook()
    await bot.session.close()

# ВОТ ЭТА ПЕРЕМЕННАЯ, КОТОРУЮ ИЩЕТ RENDER:
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
