from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import finish_inventory_keyboard, stock_menu_keyboard
from services.chat_tracker import send_tracked
from services.matcher import find_best_match
from services.parser import parse_inventory
from services.repository import get_all_products, get_user_direction, set_stock
from states.fsm_states import InventoryStates

router = Router()

_STATE_LOCATION = {
    InventoryStates.warehouse.state: "warehouse",
    InventoryStates.coffee_shop.state: "coffee_shop",
}

_LOCATION_LABEL = {
    "warehouse": "склада",
    "coffee_shop": "кофейни",
}

_PROMPT = (
    "📋 Инвентаризация {label}.\n"
    "Отправьте список товаров построчно, например:\n"
    "молоко 4\nсахар 1.5"
)


async def _enter_inventory_state(target, state: FSMContext, location: str) -> None:
    fsm_state = InventoryStates.warehouse if location == "warehouse" else InventoryStates.coffee_shop
    await state.set_state(fsm_state)
    await send_tracked(
        target,
        _PROMPT.format(label=_LOCATION_LABEL[location]),
        reply_markup=finish_inventory_keyboard(),
    )


@router.callback_query(F.data == "inventory_warehouse")
async def start_inventory_warehouse(callback: CallbackQuery, state: FSMContext) -> None:
    await _enter_inventory_state(callback.message, state, "warehouse")
    await callback.answer()


@router.callback_query(F.data == "inventory_coffee_shop")
async def start_inventory_coffee_shop(callback: CallbackQuery, state: FSMContext) -> None:
    await _enter_inventory_state(callback.message, state, "coffee_shop")
    await callback.answer()


@router.message(Command("inv_warehouse"))
async def cmd_inventory_warehouse(message: Message, state: FSMContext) -> None:
    await _enter_inventory_state(message, state, "warehouse")


@router.message(Command("inv_coffee"))
async def cmd_inventory_coffee_shop(message: Message, state: FSMContext) -> None:
    await _enter_inventory_state(message, state, "coffee_shop")


@router.callback_query(F.data == "finish_inventory")
async def finish_inventory(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    direction = await get_user_direction(callback.from_user.id)
    await send_tracked(
        callback.message,
        "✅ Инвентаризация завершена.",
        reply_markup=stock_menu_keyboard(direction),
    )
    await callback.answer()


@router.message(InventoryStates.warehouse)
@router.message(InventoryStates.coffee_shop)
async def handle_inventory_input(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    current_state = await state.get_state()
    location = _STATE_LOCATION[current_state]

    items, errors = parse_inventory(message.text)
    if not items and not errors:
        return

    products = await get_all_products()
    choices = {name: info["id"] for name, info in products.items()}
    products_by_id = {info["id"]: info for info in products.values()}

    applied: list[str] = []
    unmatched: list[str] = []

    for item in items:
        product_id = find_best_match(item.raw_name, choices)
        if product_id is None:
            unmatched.append(item.raw_name)
            continue

        product = products_by_id[product_id]
        await set_stock(product_id, location, item.quantity, message.from_user.id)
        applied.append(f"✅ {product['display_name']}: {item.quantity} {product['unit']}")

    blocks: list[str] = []
    if applied:
        blocks.append("\n".join(applied))
    if unmatched:
        blocks.append("⚠️ Не найдено совпадений:\n" + "\n".join(unmatched))
    if errors:
        blocks.append("❗ Не распознано:\n" + "\n".join(errors))

    await send_tracked(
        message,
        "\n\n".join(blocks) or "Ничего не обработано.",
        reply_markup=finish_inventory_keyboard(),
    )
