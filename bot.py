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
PHONE = "+375 (29) 162-86-28"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

# Глобальный словарь для хранения корзин пользователей
baskets = {}

# ========== 2. КРАСИВЫЕ ИКОНКИ ДЛЯ РАЗДЕЛОВ ==========
SECTION_ICONS = {
    "Техобслуживание": "🔧",
    "Компьютерная диагностика": "💻",
    "Диагностика и ремонт подвески": "🛞",
    "Развал схождения": "📐",
    "Заправка кондиционера": "❄️",
    "Диагностика и ремонт дизельных форсунок": "⛽"
}

# ========== 3. ПОЛНАЯ СТРУКТУРА УСЛУГ И ОПИСАНИЙ ==========
SERVICES = {
    "Техобслуживание": {
        "t1": {
            "full_name": "Замена масла и масляного фильтра", 
            "price": "30 руб.", 
            "price_num": 30,
            "time": "около часа с момента начала работы", 
            "desc": "Замена старого, отработанного масла и грязного фильтра на свежие, чтобы двигатель работал тише, мягче и прослужил намного дольше без дорогого ремонта."
        },
        "t2": {
            "full_name": "Замена воздушного фильтра", 
            "price": "20 руб.", 
            "price_num": 20,
            "time": "около 20-30 минут с момента начала работы", 
            "desc": "Установка нового чистого фильтра вместо забитого пылью, чтобы двигатель получал больше кислорода, лучше разгонялся и тратил меньше топлива."
        },
        "t3": {
            "full_name": "Замена салонного фильтра", 
            "price": "20 руб.", 
            "price_num": 20,
            "time": "около 20-40 минут с момента начала работы", 
            "desc": "Обновление барьера, который очищает воздух в салоне от пыли, аллергенов и выхлопных газов, чтобы в машине всегда было свежо, а кондиционер не источал неприятный запах."
        },
        "t4": {
            "full_name": "Замена тормозных колодок", 
            "price": "40 руб.", 
            "price_num": 40,
            "time": "около часа с момента начала работы", 
            "desc": "Установка новых колодок вместо стёртых, чтобы машина тормозила чётко, быстро и безопасно, без скрипов и вибраций при нажатии на педаль."
        },
        "t5": {
            "full_name": "Замена тормозных дисков", 
            "price": "70 руб.", 
            "price_num": 70,
            "time": "около часа с момента начала работы", 
            "desc": "Установка новых дисков взамен изношенных или с бороздами, чтобы торможение стало ровным, без вибраций и биения в педаль, а колодки прилегали идеально."
        }
    },
    "Компьютерная диагностика": {
        "c1": {
            "full_name": "Диагностика ЭСУД", 
            "price": "40 руб.", 
            "price_num": 40,
            "time": "около 40 минут с момента начала работы", 
            "desc": "Компьютерная проверка всех электронных систем двигателя, которая считывает скрытые ошибки и показания датчиков, чтобы точно понять, почему машина тупит, перерасходует топливо или горит «чек», без лишних догадок и разбора мотора."
        },
        "c2": {
            "full_name": "Сброс ошибок", 
            "price": "30 руб.", 
            "price_num": 30,
            "time": "около 30 минут с момента начала работы", 
            "desc": "Очистка памяти бортового компьютера от кодов неисправностей после ремонта, чтобы погасить «чек» на приборной панели и проверить, решилась ли проблема, без помех от старых записей."
        }
    },
    "Диагностика и ремонт подвески": {
        "p1": {
            "full_name": "Осмотр элементов подвески на износ и повреждения", 
            "price": "20 руб.", 
            "price_num": 20,
            "time": "около 30 минут", 
            "desc": "Визуальная и механическая проверка элементов подвески, сайлентблоков, амортизаторов и зазоров для выявления скрытых дефектов."
        },
        "p2": {
            "full_name": "Замена рычагов подвески", 
            "price": "от 50 руб. (в зависимости от рычага)", 
            "price_num": 50,
            "time": "от 1 часа", 
            "desc": "Профессиональный демонтаж старых поврежденных рычагов подвески и установка новых деталей."
        },
        "p3": {
            "full_name": "Замена сайлентблоков на снятом рычаге", 
            "price": "15 руб.", 
            "price_num": 15,
            "time": "около 40 минут", 
            "desc": "Качественная выпрессовка старых изношенных резинометаллических втулок и запрессовка новых элементов на прессе."
        },
        "p4": {
            "full_name": "Замена балочных сайлентблоков", 
            "price": "от 120 руб.", 
            "price_num": 120,
            "time": "около 1.5 часов", 
            "desc": "Замена сайлентблоков задней или передней балки автомобиля при потере упругости соединений."
        }
    },
    "Развал схождения": {
        "r1": {
            "full_name": "Регулировка развала схождения 1 оси", 
            "price": "50 руб.", 
            "price_num": 50,
            "time": "около 30 минут с момента начала работы. Настройка происходит по живой очереди.", 
            "desc": "Развал-схождение — это настройка углов установки колёс, чтобы машина ехала строго прямо, руль не уводил в сторону, а шины изнашивались равномерно, без быстрого съедания резины с одной стороны."
        },
        "r2": {
            "full_name": "Регулировка развала схождения 2х осей", 
            "price": "55 руб.", 
            "price_num": 55,
            "time": "около 45 минут с момента начала работы. Настройка происходит по живой очереди.", 
            "desc": "Развал-схождение — это настройка углов установки колёс, чтобы машина ехала строго прямо, руль не уводил в сторону, а шины изнашивались равномерно, без быстрого съедания резины с одной стороны."
        }
    },
    "Заправка кондиционера": {
        "a1": {
            "full_name": "Заправка кондиционера", 
            "price": "30 руб.", 
            "price_num": 30,
            "time": "около 30 минут с момента начала работы", 
            "desc": "Заправка кондиционера — это дозаправка системы охлаждения хладагентом взамен утерянного за сезон, чтобы кондиционер снова дул ледяным воздухом, быстрее охлаждал салон в жару и работал без перегрузок, что к тому же снижает расход топлива."
        },
        "a2": {
            "full_name": "Поиск утечки кондиционера", 
            "price": "50 руб.", 
            "price_num": 50,
            "time": "около часа с момента начала работы", 
            "desc": "Поиск утечки кондиционера — это диагностика всей системы специальным оборудованием и ультрафиолетовым фонариком, чтобы точно найти место, откуда уходит хладагент, и устранить причину, а не просто заправлять систему каждое лето."
        }
    },
    "Диагностика и ремонт дизельных форсунок": {
        "f1": {"full_name": "Диагностика форсунок системы Common Rail", "price": "15 руб. за штуку", "price_num": 15, "time": "по запросу", "desc": "Комплексный тест параметров работы высокоточных дизельных форсунок системы Common Rail на стенде."},
        "f2": {"full_name": "Диагностика однопружинных механических форсунок", "price": "6 руб. за штуку", "price_num": 6, "time": "по запросу", "desc": "Проверка давления открытия распылителя и качества факела распыла топлива."},
        "f3": {"full_name": "Диагностика двухпружинных механических форсунок", "price": "15 руб. за штуку", "price_num": 15, "time": "по запросу", "desc": "Проверка параметров работы двухступенчатых механических дизельных форсунок."},
        "f4": {"full_name": "Ремонт и настройка однопружинных механических форсунок", "price": "35 руб. за штуку", "price_num": 35, "time": "по запросу", "desc": "Разборка, очистка, замена внутренних элементов и точная калибровка давления открытия."},
        "f5": {"full_name": "Ремонт и настройка двухпружинных механических форсунок", "price": "75 руб. за штуку", "price_num": 75, "time": "по запросу", "desc": "Профессиональное восстановление геометрии и калибровка ступеней впрыска двухпружинной форсунки."}
    }
}

# ========== 4. СОСТОЯНИЯ (FSM) ==========
class OrderState(StatesGroup):
    waiting_for_phone = State()

# ========== 5. БОТ И ДИСПЕТЧЕР ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== 6. КРАСИВОЕ ГЛАВНОЕ МЕНЮ ==========
def main_keyboard():
    buttons = []
    for section in SERVICES.keys():
        icon = SECTION_ICONS.get(section, "📌")
        buttons.append([KeyboardButton(text=f"{icon} {section}")])
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

# ========== 8. ОБРАБОТКА ТЕКСТОВЫХ НАЖАТИЙ МЕНЮ ==========
@dp.message(F.text)
async def handle_menu(message: types.Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id
    
    for section in SERVICES.keys():
        icon = SECTION_ICONS.get(section, "📌")
        if text == section or text == f"{icon} {section}":
            await show_section_services(message, section)
            return
            
    if text == "🛒 Корзина":
        await show_basket_msg(message)
    elif text == "🗑 Очистить":
        baskets[user_id] = []
        await message.answer("🧹 Корзина очищена!", reply_markup=main_keyboard())
    else:
        await message.answer(
            "❓ Пожалуйста, выберите раздел из меню ниже.",
            reply_markup=main_keyboard()
        )

# ПОДРАЗДЕЛЫ: Только чистые названия на кнопках
async def show_section_services(message: types.Message, section: str):
    services = SERVICES[section]
    icon = SECTION_ICONS.get(section, "📌")
    
    buttons = []
    for i, (key, item) in enumerate(services.items(), 1):
        buttons.append([InlineKeyboardButton(
            text=f"{i}. {item['full_name']}",
            callback_data=f"view_{key}"
        )])
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="back_to_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        f"{icon} *{section}*\n\n"
        f"Выберите интересующую услугу ниже для просмотра подробностей и добавления:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ========== 9. КАРТОЧКА ПОЗИЦИИ (ТУТ ОПИСАНИЕ) ==========
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
        [InlineKeyboardButton(text="✅ Добавить в 🛒", callback_data=f"add_{key}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"back_{found_section}")]
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
    found_section = ""
    for section, services in SERVICES.items():
        if key in services:
            service_name = services[key]['full_name']
            found_section = section
            break
            
    total = sum_price(user_id)
    
    await callback.answer(f"✅ Добавлено!")
    await callback.message.edit_text(
        f"✅ Услуга *«{service_name}»* добавлена в корзину!\n\n"
        f"📦 Всего в корзине: {len(baskets[user_id])} поз.\n"
        f"💰 Общая сумма: {total} руб.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="go_to_basket")],
            [InlineKeyboardButton(text="🔙 К списку услуг", callback_data=f"back_{found_section}")]
        ]),
        parse_mode="Markdown"
    )

def sum_price(user_id):
    total = 0
    for key in baskets.get(user_id, []):
        for section, services in SERVICES.items():
            if key in services:
                total += services[key]['price_num']
                break
    return total

# ========== 11. КНОПКИ НАЗАД ==========
@dp.callback_query(F.data.startswith("back_"))
async def back_to_section(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]
    await show_section_services(callback.message, section)
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📋 Выберите раздел услуг:", reply_markup=main_keyboard())
    await callback.answer()

# ========== 12. ПРОСМОТР И ОЧИСТКА КОРЗИНЫ (ИСПРАВЛЕНО!) ==========
@dp.callback_query(F.data == "go_to_basket")
async def go_to_basket_callback(callback: types.CallbackQuery):
    # Метод исправлен — теперь он вызывает правильный генератор сообщения корзины
    user_id = callback.from_user.id
    basket = baskets.get(user_id, [])
    
    if not basket:
        await callback.message.edit_text("🛒 Ваша корзина пуста. Выберите услуги в меню!", reply_markup=main_keyboard())
        await callback.answer()
        return
        
    text = "🛒 *Ваша корзина (выбранные услуги):*\n\n"
    total = 0
    for i, key in enumerate(basket, 1):
        for section, services in SERVICES.items():
            if key in services:
                # ВНУТРИ КОРЗИНЫ ТЕПЕРЬ ПОЛНОЕ ОПИСАНИЕ И ДЕТАЛИ ПОЗИЦИИ!
                item = services[key]
                text += f"*{i}. {item['full_name']}*\n"
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
    for i, key in enumerate(basket, 1):
        for section, services in SERVICES.items():
            if key in services:
                item = services[key]
                text += f"*{i}. {item['full_name']}*\n"
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

# ========== 13. ОФОРМЛЕНИЕ ЗАКАЗА (ТЕЛЕФОН ТЕКСТОМ) ==========
@dp.callback_query(F.data == "start_checkout")
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not baskets.get(user_id, []):
        await callback.answer("Ваша корзина пуста.")
        return
        
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена оформления")]], 
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

@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "❌ Отмена оформления":
        await state.clear()
        await message.answer("❌ Оформление отменено.", reply_markup=main_keyboard())
        return
        
    user_phone = message.text
    basket = baskets.get(user_id, [])
    
    # Сборка сообщения менеджеру СТО
    text = f"🛒 *Новый заказ!*\n\n"
    text += f"👤 Клиент: {message.from_user.first_name} (@{message.from_user.username or 'без юзернейма'})\n"
    text += f"📞 Телефон: `{user_phone}`\n"
    text += f"🆔 ID: `{user_id}`\n\n"
    text += f"📋 *Выбранные услуги:*\n"
    
    total = 0
    for i, key in enumerate(basket, 1):
        for section, services in SERVICES.items():
            if key in services:
                text += f"{i}. {services[key]['full_name']} — {services[key]['price']}\n"
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
        baskets[user_id] = []  # Очистка корзины только после успешной отправки!
    except Exception as e:
        logging.error(f"Ошибка при отправке заказа менеджеру: {e}")
        await message.answer("❌ Произошла ошибка при отправке заявки. Пожалуйста, свяжитесь со СТО напрямую по телефону.", reply_markup=main_keyboard())
        
    await state.clear()

# ========== 14. FASTAPI С СЕРВЕРОМ ==========
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
