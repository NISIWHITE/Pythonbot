import os
import logging
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from fastapi import FastAPI, Request, Response

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# ============================================================
# 1. НАСТРОЙКИ И КОНСТАНТЫ
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = "https://pythonbot-7nyc.onrender.com"

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# Ссылки на социальные сети и сайт
TIKTOK_URL = "https://www.tiktok.com/@magnatservice?_r=1&_t=ZS-98BrfZbrF33"
INSTAGRAM_URL = "https://www.instagram.com/autoservice_magnat"
WEBSITE_URL = "https://stomagnat.by/"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Временные базы данных в оперативной памяти
profiles = {}
baskets = {}

# Данные об услугах (Прайс-лист)
SERVICES = {
    "tech_maintenance": {
        "oil_change": {"full_name": "Замена масла в двигателе", "desc": "Включает слив старого масла, замену фильтра и залив нового.", "time": "30-40 мин", "price": "от 30 руб.", "price_num": 30},
        "filters_change": {"full_name": "Замена фильтров (воздушный, салонный)", "desc": "Рекомендуется менять каждые 10 000 км.", "time": "20 мин", "price": "от 15 руб.", "price_num": 15},
    },
    "brake_system": {
        "pads_replacement": {"full_name": "Замена тормозных колодок", "desc": "Обеспечивает безопасность торможения.", "time": "40-50 мин", "price": "от 40 руб.", "price_num": 40},
        "discs_replacement": {"full_name": "Замена тормозных дисков", "desc": "Выполняется при износе или деформации дисков.", "time": "1-1.5 часа", "price": "от 70 руб.", "price_num": 70},
    }
}

# ============================================================
# 2. FSM СОСТОЯНИЯ
# ============================================================
class ProfileState(StatesGroup):
    waiting_for_name = State()
    waiting_for_car_brand = State()

# ============================================================
# 3. КЛАВИАТУРЫ
# ============================================================
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛠️ Услуги и цены"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="📱 Наши соцсети"), KeyboardButton(text="👤 Профиль")]
        ],
        resize_keyboard=True
    )

def categories_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Тех. обслуживание", callback_data="cat_tech_maintenance")],
        [InlineKeyboardButton(text="🛑 Тормозная система", callback_data="cat_brake_system")]
    ])
    return kb

# ============================================================
# 4. /start — СОЗДАНИЕ ИЛИ ВХОД В ПРОФИЛЬ
# ============================================================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()  # Сбрасываем любые зависшие старые состояния
    user_id = message.from_user.id
    
    if user_id not in baskets:
        baskets[user_id] = []
        
    if user_id not in profiles:
        profiles[user_id] = {}
        await message.answer(
            f"🖐️ *Добро пожаловать в Магнат Сервис!*\n\n"
            f"Давайте познакомимся! Я создам ваш профиль.\n\n"
            f"✏️ *Введите ваше имя:*",
            parse_mode="Markdown"
        )
        await state.set_state(ProfileState.waiting_for_name)
        return
    
    await message.answer("🚀 Рады видеть вас снова!", reply_markup=main_keyboard())

# ============================================================
# 5. ЗАПОЛНЕНИЕ ПРОФИЛЯ
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

@dp.message(ProfileState.waiting_for_car_brand)
async def process_car_brand(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    profiles[user_id]["car_brand"] = message.text
    await state.clear()
    
    await message.answer(
        f"🎉 *Профиль успешно создан!*\n\n"
        f"👤 Имя: {profiles[user_id]['name']}\n"
        f"🚗 Авто: {profiles[user_id]['car_brand']}\n\n"
        f"Используйте меню ниже для навигации.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ============================================================
# 6. ОБРАБОТКА ОСНОВНОГО МЕНЮ
# ============================================================
@dp.message(lambda msg: msg.text == "🛠️ Услуги и цены")
async def show_services(message: types.Message):
    await message.answer("📂 *Выберите категорию услуг:*", reply_markup=categories_keyboard(), parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "📱 Наши соцсети")
async def show_socials(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 TikTok", url=TIKTOK_URL)],
        [InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton(text="🌐 Наш сайт (stomagnat.by)", url=WEBSITE_URL)]
    ])
    await message.answer("📱 *Мы в социальных сетях и интернете:*\n\nПодписывайтесь, чтобы следить за акциями и новостями нашего автосервиса!", reply_markup=kb, parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "👤 Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id not in profiles or not profiles[user_id]:
        await message.answer("❌ Профиль не найден. Напишите /start, чтобы создать его.")
        return
    
    await message.answer(
        f"👤 *Ваш профиль:*\n\n"
        f"📝 *Имя:* {profiles[user_id].get('name', 'Не указано')}\n"
        f"🚗 *Автомобиль:* {profiles[user_id].get('car_brand', 'Не указан')}",
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.text == "🛒 Корзина")
async def show_basket_menu(message: types.Message):
    await show_basket_msg(message)

# ============================================================
# 7. ОБРАБОТКА ВЫБОРА УСЛУГ
# ============================================================
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def process_category(callback_query: types.CallbackQuery):
    category = callback_query.data.split("_", 1)[1]
    if category not in SERVICES:
        await callback_query.answer("Категория не найдена.")
        return
    
    inline_kb = []
    for code, service in SERVICES[category].items():
        inline_kb.append([InlineKeyboardButton(text=service["full_name"], callback_data=f"srv_{code}")])
        
    await callback_query.message.edit_text(
        "📝 *Выберите конкретную услугу для просмотра деталей:*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_kb),
        parse_mode="Markdown"
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("srv_"))
async def process_service_details(callback_query: types.CallbackQuery):
    srv_code = callback_query.data.split("_", 1)[1]
    
    target_service = None
    for cat, services in SERVICES.items():
        if srv_code in services:
            target_service = services[srv_code]
            break
            
    if not target_service:
        await callback_query.answer("Услуга не найдена.")
        return
        
    text = (
        f"🛠️ *{target_service['full_name']}*\n\n"
        f"📝 *Описание:* {target_service['desc']}\n"
        f"⏱️ *Примерное время:* {target_service['time']}\n"
        f"💰 *Стоимость:* {target_service['price']}\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Добавить в корзину", callback_data=f"add_{srv_code}")],
        [InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_cats")]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "back_to_cats")
async def back_to_categories(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("📂 *Выберите категорию услуг:*", reply_markup=categories_keyboard(), parse_mode="Markdown")
    await callback_query.answer()

# ============================================================
# 8. ЛОГИКА КОРЗИНЫ
# ============================================================
@dp.callback_query(lambda c: c.data.startswith("add_"))
async def add_to_basket(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    srv_code = callback_query.data.split("_", 1)[1]
    
    if user_id not in baskets:
        baskets[user_id] = []
        
    baskets[user_id].append(srv_code)
    await callback_query.answer("✅ Услуга добавлена в корзину!")

@dp.callback_query(lambda c: c.data == "clear_basket")
async def clear_basket(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    baskets[user_id] = []
    await callback_query.message.edit_text("🗑️ Корзина очищена.")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "start_checkout")
async def start_checkout(callback_query: types.CallbackQuery):
    await callback_query.message.answer("🎉 Спасибо за заказ! Наш менеджер свяжется с вами в ближайшее время для подтверждения записи.")
    await callback_query.answer()

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

# ============================================================
# 9. ЗАПУСК ВЕБ-СЕРВЕРА FASTAPI И ВЕБХУКА
# ============================================================
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

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return Response(status_code=200)
    except Exception as e:
        logging.error(f"Ошибка обработки вебхука: {e}")
        return Response(status_code=500)
