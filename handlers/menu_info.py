from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import kbzhu_keyboard
from services.chat_tracker import send_tracked
from services.matcher import find_best_match
from services.parser import split_names
from services.repository import get_all_product_info
from states.fsm_states import KbzhuStates

router = Router()

_PROMPT = (
    "🍽 КБЖУ\n"
    "Отправьте название блюда/напитка (можно несколько через запятую или "
    "с новой строки)."
)


def _format_number(value: float | None) -> str:
    if value is None:
        return "?"
    return str(int(value)) if float(value).is_integer() else str(round(value, 2))


def _format_card(info: dict) -> str:
    return (
        f"🥐 {info['name']}\n"
        f"{_format_number(info['calories'])} ккал "
        f"(Б: {_format_number(info['protein'])}г, "
        f"Ж: {_format_number(info['fat'])}г, "
        f"У: {_format_number(info['carbs'])}г)"
    )


async def _enter_kbzhu_state(target, state: FSMContext) -> None:
    await state.set_state(KbzhuStates.waiting)
    await send_tracked(target, _PROMPT, reply_markup=kbzhu_keyboard())


@router.callback_query(F.data == "menu_kbzhu")
async def handle_menu_kbzhu(callback: CallbackQuery, state: FSMContext) -> None:
    await _enter_kbzhu_state(callback.message, state)
    await callback.answer()


@router.message(Command("kbzhu"))
async def cmd_kbzhu(message: Message, state: FSMContext) -> None:
    await _enter_kbzhu_state(message, state)


@router.message(KbzhuStates.waiting)
async def handle_kbzhu_input(message: Message) -> None:
    if not message.text:
        return

    names = split_names(message.text)
    if not names:
        return

    product_info = await get_all_product_info()
    choices = {name: name for name in product_info}

    cards: list[str] = []
    unmatched: list[str] = []

    for raw_name in names:
        matched_key = find_best_match(raw_name, choices)
        if matched_key is None:
            unmatched.append(raw_name)
            continue
        cards.append(_format_card(product_info[matched_key]))

    blocks: list[str] = []
    if cards:
        blocks.append("\n\n".join(cards))
    if unmatched:
        blocks.append("⚠️ Не найдено совпадений:\n" + "\n".join(unmatched))

    await send_tracked(
        message,
        "\n\n".join(blocks) or "Ничего не найдено.",
        reply_markup=kbzhu_keyboard(),
    )
