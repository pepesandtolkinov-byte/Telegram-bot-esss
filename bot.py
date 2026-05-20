import time
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text

# Твой новый токен и твой ID уже внутри!
API_TOKEN = '8637040129:AAGAfQVVO2Vq1aidvj5opvLo7CPcSgGTNgc'  
OWNER_ID = 7942812864  

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- БАЗА ДАННЫХ В ПАМЯТИ ---
users_db = {}       
admins_list = set() 
black_list = set()  
admin_state = {}    
user_state = {}     

DEFAULT_COOLDOWN = 8 * 3600  
DEFAULT_REQUESTS = 4

def check_and_reset_limits(user_id):
    if user_id in users_db:
        current_time = time.time()
        user_data = users_db[user_id]
        if current_time - user_data["last_reset"] >= user_data["cooldown"]:
            user_data["requests"] = DEFAULT_REQUESTS
            user_data["last_reset"] = current_time

def is_any_admin(user_id):
    return user_id == OWNER_ID or user_id in admins_list

# --- КОМАНДА СТАРТ ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    if user_id in black_list:
        await message.answer("Вы заблокированы в этом боте. ❌")
        return

    if user_id not in users_db:
        users_db[user_id] = {
            "username": username.lower() if username else None,
            "requests": DEFAULT_REQUESTS,
            "last_reset": time.time(),
            "cooldown": DEFAULT_COOLDOWN
        }
    else:
        if username:
            users_db[user_id]["username"] = username.lower()

    check_and_reset_limits(user_id)
    
    keyboard = types.InlineKeyboardMarkup()
    btn_ask = types.InlineKeyboardButton(text="➕ Попросить запросы", callback_data="user_ask_req")
    keyboard.add(btn_ask)
    
    await message.answer(
        f"Привет! Это OSINT-бот.\n"
        f"У тебя осталось запросов: {users_db[user_id]['requests']}\n"
        f"Отправь мне @username человека, чтобы узнать его ID.",
        reply_markup=keyboard
    )

# --- ПОДАЧА ЗАЯВКИ ЮЗЕРОМ ---
@dp.callback_query_handler(text="user_ask_req")
async def ask_req_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in black_list:
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
        
    user_state[user_id] = "waiting_for_amount"
    await callback.message.answer("Сколько запросов ты хочешь получить? (Число от 1 до 10):")
    await callback.answer()

# --- ПАНЕЛЬ АДМИНИСТРАТОРА ---
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    user_id = message.from_user.id
    if not is_any_admin(user_id):
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    btn_requests = types.InlineKeyboardButton(text="⚙️ Изменить запросы вручную", callback_data="adm_req")
    btn_time = types.InlineKeyboardButton(text="⏳ Изменить время обновления", callback_data="adm_time")
    btn_ban = types.InlineKeyboardButton(text="🚫 Черный список (Добавить)", callback_data="adm_ban")
    
    if user_id == OWNER_ID:
        btn_add_admin = types.InlineKeyboardButton(text="👑 Добавить админа", callback_data="own_add_adm")
        btn_rem_admin = types.InlineKeyboardButton(text="🔨 Снять админа", callback_data="own_rem_adm")
        keyboard.add(btn_requests, btn_time, btn_ban, btn_add_admin, btn_rem_admin)
    else:
        keyboard.add(btn_requests, btn_time, btn_ban)

    await message.answer("🛠 Панель управления бота:", reply_markup=keyboard)

@dp.callback_query_handler(Text(startswith=["adm_", "own_"]))
async def admin_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_any_admin(user_id):
        await callback.answer("Доступ запрещен!")
        return

    action = callback.data
    
    if action == "adm_req":
        admin_state[user_id] = "waiting_for_req"
        await callback.message.answer("Введите юзернейм и количество запросов.\nПример: `@username 10`")
    elif action == "adm_time":
        admin_state[user_id] = "waiting_for_time"
        await callback.message.answer("Введите юзернейм и время обновления в часах.\nПример: `@username 2`")
    elif action == "adm_ban":
        admin_state[user_id] = "waiting_for_ban"
        await callback.message.answer("Введите юзернейм для бана.\nПример: `@username`")
        
    elif action == "own_add_adm" and user_id == OWNER_ID:
        admin_state[user_id] = "waiting_for_add_adm"
        await callback.message.answer("Введите юзернейм будущего админа.\nПример: `@username`")
    elif action == "own_rem_adm" and user_id == OWNER_ID:
        admin_state[user_id] = "waiting_for_rem_adm"
        await callback.message.answer("Введите юзернейм админа, которого нужно снять.\nПример: `@username`")
    
    await callback.answer()

# --- ОБРАБОТКА ЗАЯВОК ---
@dp.callback_query_handler(Text(startswith="ticket_"))
async def handle_ticket(callback: types.CallbackQuery):
    if not is_any_admin(callback.from_user.id):
        await callback.answer("Вы не админ!")
        return

    data_parts = callback.data.split("_")
    action = data_parts[1]
    target_id = int(data_parts[2])
    amount = int(data_parts[3])

    if action == "accept":
        if target_id in users_db:
            users_db[target_id]["requests"] += amount
            try:
                await bot.send_message(target_id, f"🎉 Твоя заявка одобрена! Начислено +{amount} запросов.")
            except Exception: pass
            await callback.message.edit_text(f"✅ Заявка на {amount} запросов для ID {target_id} одобрена.")
        else:
            await callback.message.edit_text("❌ Ошибка: юзер не найден в базе.")
            
    elif action == "reject":
        try:
            await bot.send_message(target_id, f"❌ Твоя заявка на {amount} запросов была отклонена.")
        except Exception: pass
        await callback.message.edit_text(f"🛑 Заявка на {amount} запросов от ID {target_id} отклонена.")

    await callback.answer()

# --- ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ---
@dp.message_handler()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in black_list:
        await message.answer("Вы заблокированы. ❌")
        return

    if user_id in user_state and user_state[user_id] == "waiting_for_amount":
        del user_state[user_id]
        try:
            amount = int(text)
            if amount < 1 or amount > 10:
                await message.answer("Можно запросить только от 1 до 10!")
                return
            
            username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
            
            keyboard = types.InlineKeyboardMarkup()
            btn_yes = types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ticket_accept_{user_id}_{amount}")
            btn_no = types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"ticket_reject_{user_id}_{amount}")
            keyboard.add(btn_yes, btn_no)
            
            await bot.send_message(OWNER_ID, f"📥 *Новая заявка!*\nОт: {username}\nКоличество: *{amount}*", parse_mode="Markdown", reply_markup=keyboard)
            
            for adm in admins_list:
                try:
                    await bot.send_message(adm, f"📥 *Новая заявка!*\nОт: {username}\nКоличество: *{amount}*", parse_mode="Markdown", reply_markup=keyboard)
                except Exception: pass
                
            await message.answer("⏳ Заявка отправлена администрации.")
            return
        except ValueError:
            await message.answer("Введите число от 1 до 10.")
            return

    if is_any_admin(user_id) and user_id in admin_state:
        state = admin_state[user_id]
        del admin_state[user_id]

        try:
            parts = text.split()
            target_username = parts[0].replace("@", "").lower()

            target_id = None
            for uid, data in users_db.items():
                if data["username"] == target_username:
                    target_id = uid
                    break

            if not target_id:
                await message.answer("❌ Пользователь еще не заходил в бота.")
                return

            if state == "waiting_for_req":
                count = int(parts[1])
                users_db[target_id]["requests"] = count
                await message.answer(f"✅ Для @{target_username} установлено {count} запросов.")
            elif state == "waiting_for_time":
                hours = int(parts[1])
                users_db[target_id]["cooldown"] = hours * 3600
                await message.answer(f"✅ Время обновления для @{target_username} изменено на {hours} ч.")
            elif state == "waiting_for_ban":
                if target_id == OWNER_ID:
                    await message.answer("Вы не можете забанить Главного админа! 😂")
                    return
                black_list.add(target_id)
                await message.answer(f"🚫 @{target_username} добавлен в ЧС.")
                
            elif state == "waiting_for_add_adm" and user_id == OWNER_ID:
                admins_list.add(target_id)
                await message.answer(f"👑 @{target_username} теперь назначен Администратором!")
            elif state == "waiting_for_rem_adm" and user_id == OWNER_ID:
                if target_id in admins_list:
                    admins_list.remove(target_id)
                    await message.answer(f"🔨 @{target_username} снят с должности администратора.")
                else:
                    await message.answer("Этот... не был админом.")
            return
        except Exception:
            await message.answer("❌ Ошибка ввода!")
            return

    if text.startswith("@"):
        check_and_reset_limits(user_id)
        if users_db[user_id]["requests"] <= 0:
            keyboard = types.InlineKeyboardMarkup()
            btn_ask = types.InlineKeyboardButton(text="➕ Попросить запросы", callback_data="user_ask_req")
            keyboard.add(btn_ask)
            await message.answer("❌ У тебя закончились лимиты запросов!", reply_markup=keyboard)
            return

        search_name = text.replace("@", "").lower()
        found_id = None
        for uid, data in users_db.items():
            if data["username"] == search_name:
                found_id = uid
                break
                
        if found_id:
            users_db[user_id]["requests"] -= 1
            await message.answer(f"🔍 Результат для {text}:\n🔹 Telegram ID: `{found_id}`\n\nОсталось запросов: {users_db[user_id]['requests']}", parse_mode="Markdown")
        else:
            await message.answer("❌ Данного пользователя пока нет в системе.")
    else:
        await message.answer("Отправь юзернейм в формате `@username`.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    
