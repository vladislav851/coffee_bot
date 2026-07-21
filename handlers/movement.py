from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from handlers.search import handle_search
from services.chat_tracker import send_tracked
from services.matcher import find_best_match
from services.parser import parse_movement
from services.repository import get_all_products, get_user_direction, move_products

router = Router()

_LOCATION_LABEL = {
    "warehouse": "Склад",
    "coffee_shop": "Кофейня",
}

_DIRECTION_LOCATIONS = {
    "warehouse_to_coffee": ("warehouse", "coffee_shop"),
    "coffee_to_warehouse": ("coffee_shop", "warehouse"),
}


@router.message(StateFilter(None), F.text)
async def handle_free_text(message: Message) -> None:
    """Единая точка входа для текста вне FSM: Сценарий А -> Б -> заглушка."""
    items, errors = parse_movement(message.text)
    products = await get_all_products()

    if not items:
        handled = await handle_search(message, products)
        if not handled:
            await send_tracked(message, "Не нашёл такой товар, проверьте название.")
        return

    user_id = message.from_user.id
    direction = await get_user_direction(user_id)
    from_location, to_location = _DIRECTION_LOCATIONS[direction]

    choices = {name: info["id"] for name, info in products.items()}
    products_by_id = {info["id"]: info for info in products.values()}

    to_move: list[dict] = []
    unmatched: list[str] = []

    for item in items:
        product_id = find_best_match(item.raw_name, choices)
        if product_id is None:
            unmatched.append(item.raw_name)
            continue
        to_move.append({"product_id": product_id, "quantity": item.quantity})

    result = await move_products(
        items=to_move,
        from_location=from_location,
        to_location=to_location,
        user_id=user_id,
    )

    moved_lines = []
    for entry in result["moved"]:
        product = products_by_id[entry["product_id"]]
        moved_lines.append(f"{product['display_name']}: {entry['quantity']} {product['unit']}")

    blocked_lines = []
    for entry in result["blocked"]:
        product = products_by_id[entry["product_id"]]
        blocked_lines.append(
            f"⛔ {product['display_name']}: недостаточно на {_LOCATION_LABEL[from_location]} "
            f"(есть {entry['available']}, нужно {entry['quantity']})"
        )

    blocks: list[str] = []
    if moved_lines:
        blocks.append(
            f"✅ Успешно перемещено ({_LOCATION_LABEL[from_location]} → {_LOCATION_LABEL[to_location]}):\n"
            + "\n".join(moved_lines)
        )
    if blocked_lines:
        blocks.append("\n".join(blocked_lines))
    if unmatched:
        blocks.append("⚠️ Не найдено: " + ", ".join(unmatched))
    if errors:
        blocks.append("❗ Не распознано:\n" + "\n".join(errors))

    await send_tracked(message, "\n\n".join(blocks) or "Ничего не обработано.")
