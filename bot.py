
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== 1. ТОКЕН ==========
BOT_TOKEN = "8999270734:AAEn2hM5-kgC8XKWtgTpSjwbT4iyGhYbAEc"

# ========== 2. КОНТАКТЫ ==========
PHONE = "+375 (29) 162-86-28"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

# ========== 3. УСЛУГИ ==========
SERVICES = {
    "Техобслуживание": {
        "t1": {
            "full_name": "Замена масла, масляного фильтра",
            "price": 30,
            "time": "около часа",
            "desc": "Замена старого, отработанного масла и грязного фильтра на свежие, чтобы двигатель работал тише, мягче и прослужил намного дольше без дорогого ремонта."
        },
        "t2": {
            "full_name": "Замена воздушного фильтра",
            "price": 20,
            "time": "20-30 минут",
            "desc": "Установка нового чистого фильтра вместо забитого пылью, чтобы двигатель получал больше кислорода, лучше разгонялся и тратил меньше топлива."
        },
        "t3": {
            "full_name": "Замена салонного фильтра",
            "price": 20,
            "time": "20-40 минут",
            "desc": "Обновление барьера, который очищает воздух в салоне от пыли, аллергенов и выхлопных газов, чтобы в машине всегда было свежо, а кондиционер не источал неприятный запах."
        },
        "t4": {
            "full_name": "Замена тормозных колодок (комплект 4шт)",
            "price": 40,
            "time": "около часа",
            "desc": "Установка новых колодок вместо стёртых, чтобы машина тормозила чётко, быстро и безопасно, без скрипов и вибраций при нажатии на педаль."
        },
        "t5": {
            "full_name": "Замена тормозных дисков (комплект 4шт)",
            "price": 70,
            "time": "около часа",
            "desc": "Установка новых дисков взамен изношенных или с бороздами, чтобы торможение стало ровным, без вибраций и биения в педаль, а колодки прилегали идеально."
        }
    },
    "Компьютерная диагностика": {
        "c1": {
            "full_name": "Диагностика ЭСУ",
            "price": 40,
            "time": "около 40 минут",
            "desc": "Компьютерная проверка всех электронных систем двигателя, которая считывает скрытые ошибки и показания датчиков, чтобы точно понять, почему машина тупит, перерасходует топливо или горит «чек», без лишних догадок и разбора мотора."
        },
        "c2": {
            "full_name": "Сброс ошибок",
            "price": 30,
            "time": "около 30 минут",
            "desc": "Очистка памяти бортового компьютера от кодов неисправностей после ремонта, чтобы погасить «чек» на приборной панели и проверить, решилась ли проблема, без помех от старых записей."
        }
    },
    "Диагностика и ремонт подвески": {
        "p1": {
            "full_name": "Осмотр элементов подвески на износ и повреждения",
            "price": 20,
            "time": "около 30 минут",
            "desc": "Визуальная и механическая проверка всех элементов подвески для выявления износа, трещин и повреждений."
        },
        "p2": {
            "full_name": "Замена рычагов подвески",
            "price": 50,
            "time": "от 1 часа (зависит от рычага)",
            "desc": "Замена изношенных рычагов подвески на новые для восстановления правильной геометрии и управляемости автомобиля."
        },
        "p3": {
            "full_name": "Замена сайлентблоков на снятом рычаге",
            "price": 15,
            "time": "около 40 минут",
            "desc": "Замена резиновых втулок (сайлентблоков) на снятом рычаге для устранения стуков и люфтов в подвеске."
        },
        "p4": {
            "full_name": "Замена балочных сайлентблоков",
            "price": 120,
            "time": "около 1.5 часов",
            "desc": "Замена сайлентблоков задней балки для устранения скрипов, стуков и улучшения устойчивости автомобиля на дороге."
        }
    },
    "Развал схождения": {
        "r1": {
            "full_name": "Регулировка развала схождения 1 оси",
            "price": 50,
            "time": "около 30 минут",
            "desc": "Настройка углов установки колёс на одной оси, чтобы машина ехала строго прямо, руль не уводил в сторону, а шины изнашивались равномерно."
        },
        "r2": {
            "full_name": "Регулировка развала схождения 2х осей",
            "price": 55,
            "time": "около 45 минут",
            "desc": "Настройка углов установки колёс на обеих осях для идеальной управляемости и равномерного износа шин."
        }
    },
    "Заправка кондиционера": {
        "a1": {
            "full_name": "Заправка кондиционера",
            "price": 30,
            "time": "около 30 минут",
            "desc": "Дозаправка системы охлаждения хладагентом взамен утерянного за сезон, чтобы кондиционер снова дул ледяным воздухом, быстрее охлаждал салон в жару и работал без перегрузок, что к тому же снижает расход топлива."
        },
        "a2": {
            "full_name": "Поиск утечки в системе кондиционирования",
            "price": 50,
            "time": "около часа",
            "desc": "Диагностика всей системы специальным оборудованием и ультрафиолетовым фонариком, чтобы точно найти место, откуда уходит хладагент, и устранить причину, а не просто заправлять систему каждое лето."
        }
    },
      "Диагностика и ремонт дизельных форсунок": {
        "f1": {
            "full_name": "Диагностика форсунок системы Common Rail",
            "price": 15,
            "time": "по запросу",
            "desc": "Профессиональная диагностика форсунок системы Common Rail для выявления неисправностей и определения необходимости ремонта или замены."
        },
        "f2": {
            "full_name": "Диагностика однопружинных механических форсунок",
            "price": 6,
            "time": "по запросу",
            "desc": "Проверка состояния и работоспособности однопружинных механических форсунок для выявления отклонений и неисправностей."
        },
        "f3": {
            "full_name": "Диагностика двухпружинных механических форсунок",
            "price": 15,
            "time": "по запросу",
            "desc": "Проверка состояния и работоспособности двухпружинных механических форсунок для выявления отклонений и неисправностей."
        },
        "f4": {
            "full_name": "Ремонт и настройка однопружинных механических форсунок",
            "price": 35,
            "time": "по запросу",
            "desc": "Профессиональный ремонт и точная настройка однопружинных механических форсунок для восстановления их работоспособности."
        },
        "f5": {
            "full_name": "Ремонт и настройка двухпружинных механических форсунок",
            "price": 75,
            "time": "по запросу",
            "desc": "Профессиональный ремонт и точная настройка двухпружинных механических форсунок для восстановления их работоспособности."
        }
    }
}

# ========== 3.1 КОРОТКИЕ ID РАЗДЕЛОВ (для callback_data) ==========
# Telegram ограничивает callback_data 64 байтами. Кириллица в UTF-8 занимает
# по 2 байта на символ, поэтому длинные названия разделов (например
# "Диагностика и ремонт дизельных форсунок") в callback_data не помещаются
# и Telegram отвечает ошибкой BUTTON_DATA_INVALID. Поэтому вместо самого
# названия раздела передаём короткий идентификатор.
SECTION_IDS = {name: f"sec{i}" for i, name in enumerate(SERVICES.keys())}
SECTION_NAMES = {v: k for k, v in SECTION_IDS.items()}

# ========== 4. КОРЗИНА ==========
baskets = {}

# ========== 5. СОСТОЯНИЯ ==========
class Form(StatesGroup):
    waiting_choice = State()

# ========== 6. БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== 7. ГЛАВНОЕ МЕНЮ ==========
def main_keyboard():
    buttons = [[KeyboardButton(text=section)] for section in SERVICES.keys()]
    buttons.append([KeyboardButton(text="🛒 Моя корзина")])
    buttons.append([KeyboardButton(text="🧹 Очистить корзину")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== 8. /start ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    baskets[user_id] = []
    await state.clear()
    await message.answer(
        f"🖐️ Привет! Я помогу рассчитать стоимость работ по ремонту твоего авто.\n\n"
        f"📞 Телефон: {PHONE}\n"
        f"📍 Адрес: {ADDRESS}\n\n"
        f"⚠️ *Важно:* Стоимость запчастей рассчитывается отдельно.\n\n"
        f"Выбери раздел из меню ниже, чтобы посмотреть услуги и цены.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ========== 9. ВЫБОР РАЗДЕЛА ==========
@dp.message(F.text.in_(SERVICES.keys()))
async def select_section(message: types.Message, state: FSMContext):
    section = message.text
    services = SERVICES.get(section, {})

    if not services:
        await message.answer(
            f"📂 Раздел *{section}*\n⏳ Скоро здесь появятся услуги.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        return

    await state.update_data(current_section=section)

    keyboard_buttons = []
    for key, data in services.items():
        button_text = data.get("full_name", key)
        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"svc_{key}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        f"📂 *{section}*\nВыберите услугу:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ========== 10. ПОКАЗ ОПИСАНИЯ ==========
@dp.callback_query(F.data.startswith("svc_"))
async def show_service(callback: types.CallbackQuery, state: FSMContext):
    key = callback.data.replace("svc_", "")

    found = False
    for section, services in SERVICES.items():
        if key in services:
            data = services[key]
            full_name = data.get("full_name", key)
            found = True
            break

    if not found:
        await callback.answer("Услуга не найдена")
        return

    text = (
        f"🔧 *{full_name}*\n\n"
        f"📝 {data['desc']}\n\n"
        f"💰 Цена работы: *{data['price']} руб.*\n"
        f"⏱️ Время: *{data['time']}*"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ В корзину", callback_data=f"add_{key}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_{SECTION_IDS[section]}")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# ========== 11. ДОБАВЛЕНИЕ В КОРЗИНУ ==========
@dp.callback_query(F.data.startswith("add_"))
async def add_to_basket(callback: types.CallbackQuery):
    key = callback.data.replace("add_", "")
    user_id = callback.from_user.id

    if user_id not in baskets:
        baskets[user_id] = []

    baskets[user_id].append(key)

    price = 0
    full_name = key
    for section, services in SERVICES.items():
        if key in services:
            price = services[key]["price"]
            full_name = services[key].get("full_name", key)
            break

    # Список названий всех позиций в корзине (а не просто их количество)
    basket_names = get_basket_names(user_id)
    basket_list_text = "\n".join(f"• {name}" for name in basket_names)

    await callback.message.answer(
        f"✅ Добавлено: *{full_name}*\n💰 {price} руб.\n\n"
        f"🛒 *В корзине:*\n{basket_list_text}\n\n"
        f"Сумма: {sum_price(user_id)} руб.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

def sum_price(user_id):
    total = 0
    for key in baskets.get(user_id, []):
        for section, services in SERVICES.items():
            if key in services:
                total += services[key]["price"]
                break
    return total

def get_basket_names(user_id):
    """Возвращает список полных названий позиций, находящихся в корзине пользователя."""
    names = []
    for key in baskets.get(user_id, []):
        for section, services in SERVICES.items():
            if key in services:
                names.append(services[key].get("full_name", key))
                break
    return names

# ========== 12. НАЗАД ==========
@dp.callback_query(F.data.startswith("back_"))
async def back_to_services(callback: types.CallbackQuery, state: FSMContext):
    section_id = callback.data.replace("back_", "")
    section = SECTION_NAMES.get(section_id)
    services = SERVICES.get(section, {})

    if not services:
        await callback.answer("Раздел не найден")
        return

    keyboard_buttons = []
    for key, data in services.items():
        button_text = data.get("full_name", key)
        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"svc_{key}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        f"📂 *{section}*\nВыберите услугу:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== 13. КОРЗИНА ==========
@dp.message(F.text == "🛒 Моя корзина")
async def show_basket(message: types.Message):
    user_id = message.from_user.id
    basket = baskets.get(user_id, [])

    if not basket:
        await message.answer("🛒 Корзина пуста.", reply_markup=main_keyboard())
        return

    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    for key in basket:
        for section, services in SERVICES.items():
            if key in services:
                full_name = services[key].get("full_name", key)
                price = services[key]["price"]
                total += price
                text += f"• {full_name} — {price} руб.\n"
                break

    text += f"\n💰 *Итого за работу: {total} руб.*"
    text += f"\n\n⚠️ *Стоимость запчастей рассчитывается отдельно.*"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Оформить", callback_data="checkout")]
        ]
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

# ========== 14. ОЧИСТКА ==========
@dp.message(F.text == "🧹 Очистить корзину")
async def clear_basket(message: types.Message):
    user_id = message.from_user.id
    baskets[user_id] = []
    await message.answer("🧹 Корзина очищена.", reply_markup=main_keyboard())

# ========== 15. ОФОРМЛЕНИЕ ==========
@dp.callback_query(F.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    total = sum_price(user_id)
    await callback.message.answer(
        f"📞 *Спасибо за заказ!*\n\n"
        f"Сумма за работу: *{total} руб.*\n"
        f"⚠️ Стоимость запчастей рассчитывается отдельно.\n\n"
        f"Наш менеджер свяжется с вами в ближайшее время.\n\n"
        f"📞 Телефон: {PHONE}\n"
        f"📍 Адрес: {ADDRESS}",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )
    baskets[user_id] = []
    await callback.answer()

# ========== 16. ЗАПУСК ==========
async def main():
    print("🚗 Магнат сервис бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())