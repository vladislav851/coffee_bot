from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import (
    location_report_keyboard,
    main_menu_keyboard,
    stock_menu_keyboard,
)
from services.chat_tracker import clear_chat, send_tracked
from services.repository import (
    get_full_stock_report,
    get_product_by_id,
    get_stock_report_by_location,
    get_user_direction,
    toggle_user_direction,
    undo_last,
)

_LOCATION_TITLE = {
    "warehouse": "🏬 Остатки: Склад",
    "coffee_shop": "☕ Остатки: Кофейня",
}

router = Router()

_LOCATION_LABEL = {
    "warehouse": "Склад",
    "coffee_shop": "Кофейня",
}

_MAX_MESSAGE_LEN = 3500

_UNDO_ALERT_LIMIT = 200

_last_report_messages: dict[tuple[int, str], list[int]] = {}


@router.callback_query(F.data == "menu_stock")
async def handle_menu_stock(callback: CallbackQuery) -> None:
    direction = await get_user_direction(callback.from_user.id)
    await callback.message.edit_text(
        "📦 Учёт склада",
        reply_markup=stock_menu_keyboard(direction),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(Command("stock"))
async def cmd_stock(message: Message) -> None:
    direction = await get_user_direction(message.from_user.id)
    await send_tracked(message, "📦 Учёт склада", reply_markup=stock_menu_keyboard(direction))


@router.message(Command("toggle"))
async def cmd_toggle(message: Message) -> None:
    direction = await toggle_user_direction(message.from_user.id)
    await send_tracked(message, "Направление изменено", reply_markup=stock_menu_keyboard(direction))


@router.message(Command("undo"))
async def cmd_undo(message: Message) -> None:
    text = await _build_undo_text(message.from_user.id)
    await send_tracked(message, text)


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    deleted = await clear_chat(message.bot, message.chat.id)
    await send_tracked(
        message,
        f"🧹 Удалено сообщений бота: {deleted}",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "clear_chat")
async def handle_clear_chat(callback: CallbackQuery) -> None:
    deleted = await clear_chat(callback.bot, callback.message.chat.id)
    await send_tracked(
        callback.message,
        f"🧹 Удалено сообщений бота: {deleted}",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_direction")
async def handle_toggle_direction(callback: CallbackQuery) -> None:
    direction = await toggle_user_direction(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=stock_menu_keyboard(direction))
    await callback.answer("Направление изменено")


async def _build_undo_text(user_id: int) -> str:
    result = await undo_last(user_id)
    if result is None:
        return "Нечего отменять."

    if result["action_type"] == "movement":
        lines = []
        for item in result["payload"]:
            product = await get_product_by_id(item["product_id"])
            name = product["display_name"] if product else f"#{item['product_id']}"
            from_label = _LOCATION_LABEL.get(item["from_location"], item["from_location"])
            to_label = _LOCATION_LABEL.get(item["to_location"], item["to_location"])
            lines.append(f"{name}: {from_label} → {to_label} отменено")
        return "↩️ Последнее перемещение отменено:\n" + "\n".join(lines)

    payload = result["payload"]
    product = await get_product_by_id(payload["product_id"])
    name = product["display_name"] if product else f"#{payload['product_id']}"
    location_label = _LOCATION_LABEL.get(payload["location"], payload["location"])
    return (
        f"↩️ Отменена инвентаризация: {name} ({location_label}) "
        f"вернулось к {payload['old_qty']}"
    )


@router.callback_query(F.data == "undo_last")
async def handle_undo_last(callback: CallbackQuery) -> None:
    text = await _build_undo_text(callback.from_user.id)
    if len(text) <= _UNDO_ALERT_LIMIT:
        await callback.answer(text, show_alert=True)
        return
    await send_tracked(callback.message, text)
    await callback.answer()


async def _build_full_report_blocks() -> list[str]:
    rows = await get_full_stock_report()
    blocks: list[str] = []
    current_category = None
    lines: list[str] = []

    for row in rows:
        if row["category_name"] != current_category:
            if lines:
                blocks.append("\n".join(lines))
            current_category = row["category_name"]
            lines = [f"📦 {current_category}"]
        lines.append(
            f"  {row['display_name']}: "
            f"Склад {row['warehouse_qty']} {row['unit']} / "
            f"Кофейня {row['coffee_qty']} {row['unit']}"
        )
    if lines:
        blocks.append("\n".join(lines))
    return blocks


def _chunk_blocks(blocks: list[str]) -> list[str]:
    chunks: list[str] = []
    chunk = ""
    for block in blocks:
        if chunk and len(chunk) + len(block) + 2 > _MAX_MESSAGE_LEN:
            chunks.append(chunk)
            chunk = ""
        chunk = f"{chunk}\n\n{block}" if chunk else block
    if chunk:
        chunks.append(chunk)
    return chunks


async def _replace_report(target, user_id: int, report_key: str, blocks: list[str]) -> bool:
    """Удаляет предыдущий отчёт этого типа у пользователя и присылает новый вместо накопления."""
    if not blocks:
        return False

    bot = target.bot
    chat_id = target.chat.id

    for old_message_id in _last_report_messages.get((user_id, report_key), []):
        try:
            await bot.delete_message(chat_id, old_message_id)
        except TelegramBadRequest:
            pass

    new_ids = []
    for chunk in _chunk_blocks(blocks):
        sent = await send_tracked(target, chunk)
        new_ids.append(sent.message_id)

    _last_report_messages[(user_id, report_key)] = new_ids
    return True


@router.message(Command("report"))
async def cmd_full_report(message: Message) -> None:
    sent = await _replace_report(
        message, message.from_user.id, "full", await _build_full_report_blocks()
    )
    if not sent:
        await message.answer("Товаров нет в справочнике.")


@router.callback_query(F.data == "full_report")
async def handle_full_report(callback: CallbackQuery) -> None:
    sent = await _replace_report(
        callback.message, callback.from_user.id, "full", await _build_full_report_blocks()
    )
    if not sent:
        await callback.answer("Товаров нет в справочнике", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data == "location_report_menu")
async def handle_location_report_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📍 Выберите локацию",
        reply_markup=location_report_keyboard(),
    )
    await callback.answer()


async def _build_location_report_blocks(location: str) -> list[str]:
    rows = await get_stock_report_by_location(location)
    blocks: list[str] = []
    current_category = None
    lines: list[str] = []

    for row in rows:
        if row["category_name"] != current_category:
            if lines:
                blocks.append("\n".join(lines))
            current_category = row["category_name"]
            lines = [f"📦 {current_category}"]
        lines.append(f"  {row['display_name']}: {row['quantity']} {row['unit']}")
    if lines:
        blocks.append("\n".join(lines))
    return blocks


@router.message(Command("report_warehouse"))
async def cmd_report_warehouse(message: Message) -> None:
    blocks = await _build_location_report_blocks("warehouse")
    title_and_blocks = [_LOCATION_TITLE["warehouse"]] + blocks if blocks else []
    sent = await _replace_report(message, message.from_user.id, "warehouse", title_and_blocks)
    if not sent:
        await message.answer("Товаров нет в справочнике.")


@router.message(Command("report_coffee"))
async def cmd_report_coffee(message: Message) -> None:
    blocks = await _build_location_report_blocks("coffee_shop")
    title_and_blocks = [_LOCATION_TITLE["coffee_shop"]] + blocks if blocks else []
    sent = await _replace_report(message, message.from_user.id, "coffee_shop", title_and_blocks)
    if not sent:
        await message.answer("Товаров нет в справочнике.")


@router.callback_query(F.data == "location_report_warehouse")
async def handle_location_report_warehouse(callback: CallbackQuery) -> None:
    blocks = await _build_location_report_blocks("warehouse")
    title_and_blocks = [_LOCATION_TITLE["warehouse"]] + blocks if blocks else []
    sent = await _replace_report(
        callback.message, callback.from_user.id, "warehouse", title_and_blocks
    )
    if not sent:
        await callback.answer("Товаров нет в справочнике", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data == "location_report_coffee_shop")
async def handle_location_report_coffee_shop(callback: CallbackQuery) -> None:
    blocks = await _build_location_report_blocks("coffee_shop")
    title_and_blocks = [_LOCATION_TITLE["coffee_shop"]] + blocks if blocks else []
    sent = await _replace_report(
        callback.message, callback.from_user.id, "coffee_shop", title_and_blocks
    )
    if not sent:
        await callback.answer("Товаров нет в справочнике", show_alert=True)
        return
    await callback.answer()
