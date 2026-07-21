from aiogram.exceptions import TelegramBadRequest

_sent_messages: dict[int, list[int]] = {}


def track(chat_id: int, message_id: int) -> None:
    _sent_messages.setdefault(chat_id, []).append(message_id)


async def clear_chat(bot, chat_id: int) -> int:
    """Удаляет все отслеженные сообщения бота в чате. Возвращает количество удалённых."""
    message_ids = _sent_messages.pop(chat_id, [])
    deleted = 0
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
            deleted += 1
        except TelegramBadRequest:
            pass
    return deleted


async def send_tracked(target, text: str, **kwargs):
    """message.answer / callback.message.answer с автоматическим трекингом для /clear."""
    sent = await target.answer(text, **kwargs)
    track(sent.chat.id, sent.message_id)
    return sent
