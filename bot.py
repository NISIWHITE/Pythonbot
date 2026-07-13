import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== 1. ТОКЕН ==========
BOT_TOKEN = "8999270734:AAHfpk2XBynYvzU_3EqeduWhcdSGKsUTRxQ"

# ========== 2. ID МЕНЕДЖЕРА (КОМУ ПРИХОДЯТ ЗАКАЗЫ) ==========
# Узнайте свой ID у бота @userinfobot
MANAGER_ID = 896122548  # ЗАМЕНИТЕ НА СВОЙ ID

# ========== 3. КОНТАКТЫ ==========
PHONE = "+375 (29) 162-86-28"
ADDRESS = "г. Минск, ул. Меньковский тракт 5"

# ========== 4. КОРЗИНА И ПОЛЬЗОВАТЕЛИ ==========
baskets = {}
users = {}  # для статистики

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
[13.07.2026 17:32] Леша: "desc": "Настройка углов установки колёс на обеих осях для идеальной управляемости и равномерного износа шин."
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

# ========== 6. БОТ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== 7. ГЛАВНОЕ МЕНЮ ==========
def main_keyboard():
    buttons = [[KeyboardButton(text=section)] for section in SERVICES.keys()]
    buttons.append([KeyboardButton(text="🛒 Моя корзина")])
    buttons.append([KeyboardButton(text="🧹 Очистить корзину")])
    # Кнопка для запроса номера телефона
    buttons.append([KeyboardButton(text="📞 Поделиться номером", request_contact=True)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== 8. /start ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "без юзернейма"
    first_name = message.from_user.first_name or "без имени"

    # Запоминаем пользователя
    if user_id not in users:
        users[user_id] = {"username": username, "first_name": first_name}

    baskets[user_id] = []
    await state.clear()
    await message.answer(
        f"🖐️ Привет! Я помогу рассчитать стоимость работ по ремонту твоего авто.\n\n"
        f"📞 Телефон: {PHONE}\n"
        f"📍 Адрес: {ADDRESS}\n\n"
        f"⚠️ *Важно:* Стоимость запчастей рассчитывается отдельно.\n\n"
        f"Выбери раздел из меню ниже, чтобы посмотреть услуги и цены.\n"
        f"После выбора услуг нажми '🛒 Моя корзина' для оформления.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ========== 9. ОСТАЛЬНЫЕ ХЭНДЛЕРЫ (выбор услуг, корзина) ==========
# ... (вставьте сюда весь ваш код, который я давал ранее)
# Все функции: select_section, show_service, add_to_basket, show_basket, clear_basket

# ========== 10. ОФОРМЛЕНИЕ ЗАКАЗА ==========
@dp.callback_query(F.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    basket = baskets.get(user_id, [])

    if not basket:
        await callback.message.answer("🛒 Корзина пуста.", reply_markup=main_keyboard())
        await callback.answer()
        return

    # Формируем текст заказа
    text = "🛒 *Новый заказ!*\n\n"
    text += f"👤 Клиент: {callback.from_user.first_name} (@{callback.from_user.username or 'без юзернейма'})\n"
    text += f"🆔 ID: {user_id}\n\n"
    text += "📋 *Услуги:*\n"

    total = 0
    for key in basket:
        for section, services in SERVICES.items():
            if key in services:
                full_name = services[key].get("full_name", key)
                price = services[key]["price"]
                total += price
                text += f"• {full_name} — {price} руб.\n"
                break

    text += f"\n💰 *Итого: {total} руб.*"
    text += f"\n\n⚠️ Стоимость запчастей рассчитывается отдельно."

    # Кнопка "Позвонить клиенту" (для менеджера)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Позвонить клиенту", url=f"tg://user?id={user_id}")]
        ]
    )

    # Отправляем заказ менеджеру
    try:
        await bot.send_message(
            chat_id=MANAGER_ID,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await bot.send_message(
            chat_id=MANAGER_ID,
            text="⚠️ *Важно:* Номер телефона клиента не привязан к Telegram. Уточните его при звонке.",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки менеджеру: {e}")

    # Ответ клиенту
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

    # Очищаем корзину
    baskets[user_id] = []
    await callback.answer()

# ========== 11. ОБРАБОТКА НОМЕРА ТЕЛЕФОНА ==========
@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    contact = message.contact

    # Сохраняем номер в словаре пользователя
    if user_id not in users:
        users[user_id] = {}

    users[user_id]["phone"] = contact.phone_number

    await message.answer(
        f"✅ Спасибо! Ваш номер телефона сохранён.\n"
        f"📞 {contact.phone_number}\n\n"
        f"Теперь выберите услуги и оформите заказ.",
        reply_markup=main_keyboard()
    )

    # Отправляем уведомление менеджеру, что клиент поделился номером
    try:
        await bot.send_message(
            chat_id=MANAGER_ID,
            text=f"📞 *Клиент поделился номером!*\n\n"
                 f"👤 {message.from_user.first_name} (@{message.from_user.username or 'без юзернейма'})\n"
                 f"📞 Номер: `{contact.phone_number}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")

# ========== 12. АДМИН-КОМАНДЫ ==========
@dp.message(Command("users"))
async def list_users(message: types.Message):
    if message.from_user.id != MANAGER_ID:
        await message.answer("⛔ У вас нет прав.")
        return

    if not users:
        await message.answer("📭 Нет пользователей.")
        return

    text = "👥 *Список пользователей:*\n\n"
    for uid, data in users.items():
        phone = data.get("phone", "не указан")
        text += f"• {data['first_name']} (@{data['username']}) — 📞 {phone}\n"

    await message.answer(text, parse_mode="Markdown")

# ========== 13. ЗАПУСК ==========
async def main():
    print("🚗 Магнат сервис бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
