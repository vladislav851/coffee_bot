from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.db import get_connection
from keyboards.main_menu import main_menu_keyboard
from services.chat_tracker import send_tracked

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO user_settings (telegram_user_id) VALUES (?)",
            (user_id,),
        )
        await conn.commit()
    finally:
        await conn.close()

    await send_tracked(
        message,
        f"Привет, {message.from_user.first_name}! ☕\n"
        "Отправь список товаров для перемещения или запроса остатков.",
        reply_markup=main_menu_keyboard(),
    )
