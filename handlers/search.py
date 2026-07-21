from aiogram.types import Message

from services.chat_tracker import send_tracked
from services.matcher import find_best_match
from services.parser import split_names
from services.repository import get_stock_many


async def handle_search(message: Message, products: dict) -> bool:
    """
    Сценарий Б: список названий без чисел -> остатки на Складе.
    Возвращает True, если хотя бы один товар найден и ответ отправлен.
    """
    names = split_names(message.text)
    if not names:
        return False

    choices = {name: info["id"] for name, info in products.items()}
    products_by_id = {info["id"]: info for info in products.values()}

    matched_ids: list[int] = []
    unmatched: list[str] = []

    for raw_name in names:
        product_id = find_best_match(raw_name, choices)
        if product_id is None:
            unmatched.append(raw_name)
            continue
        matched_ids.append(product_id)

    if not matched_ids:
        return False

    stock = await get_stock_many(matched_ids, "warehouse")

    lines = []
    for pid in matched_ids:
        product = products_by_id[pid]
        qty = stock.get(pid, 0.0)
        lines.append(f"{product['display_name']}: {qty} {product['unit']}")

    blocks = ["\n".join(lines)]
    if unmatched:
        blocks.append("⚠️ Не найдено: " + ", ".join(unmatched))

    await send_tracked(message, "\n\n".join(blocks))
    return True
