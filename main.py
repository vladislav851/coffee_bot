import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database.db import init_db
from handlers.inventory_mode import router as inventory_router
from handlers.main_menu_actions import router as main_menu_actions_router
from handlers.menu_info import router as menu_info_router
from handlers.movement import router as movement_router
from handlers.start import router as start_router
from middlewares.auth import AuthMiddleware

logging.basicConfig(level=logging.INFO)

BOT_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="stock", description="📦 Учёт склада"),
    BotCommand(command="kbzhu", description="🍽 КБЖУ"),
    BotCommand(command="report", description="📊 Все остатки"),
    BotCommand(command="report_warehouse", description="🏬 Остатки: Склад"),
    BotCommand(command="report_coffee", description="☕ Остатки: Кофейня"),
    BotCommand(command="inv_warehouse", description="📋 Инвентаризация Склада"),
    BotCommand(command="inv_coffee", description="📋 Инвентаризация Кофейни"),
    BotCommand(command="toggle", description="🔄 Сменить направление"),
    BotCommand(command="undo", description="↩️ Отменить последнее действие"),
    BotCommand(command="clear", description="🧹 Очистить чат"),
]


async def main() -> None:
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    await bot.set_my_commands(BOT_COMMANDS)

    dp.message.middleware(AuthMiddleware())

    dp.include_router(start_router)
    dp.include_router(inventory_router)
    dp.include_router(menu_info_router)
    dp.include_router(main_menu_actions_router)
    dp.include_router(movement_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
