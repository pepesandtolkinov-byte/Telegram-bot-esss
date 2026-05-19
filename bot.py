import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ТОКЕН ОТ @BotFather (кавычки не удаляй)
API_TOKEN = '8637040129:AAFadeiQgcazSCUL3Ho7K5-DOo5_sxdBiyk'

# ТВОЙ ID ЦИФРАМИ (без кавычек)
ADMIN_ID = 7942812864

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Привет, админ! Бот обратной связи готов к работе.")
    else:
        await message.reply("Привет! Напиши сюда свой вопрос, и Usmanov ответит тебе.")

@dp.message_handler(lambda message: message.from_user.id == ADMIN_ID and message.reply_to_message)
async def handle_admin_reply(message: types.Message):
    try:
        if message.reply_to_message.forward_from:
            user_id = message.reply_to_message.forward_from.id
        else:
            await message.reply("⚠️ Ошибка: у пользователя скрыт ID в настройках.")
            return
        await bot.copy_message(chat_id=user_id, from_chat_id=ADMIN_ID, message_id=message.message_id)
        await message.reply("✅ Ответ отправлен.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message_handler()
async def forward_to_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.reply("🚀 Ваше сообщение отправлено! Usmanov скоро вам ответит.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

