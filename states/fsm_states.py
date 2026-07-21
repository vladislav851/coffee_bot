from aiogram.fsm.state import State, StatesGroup


class InventoryStates(StatesGroup):
    warehouse = State()
    coffee_shop = State()


class KbzhuStates(StatesGroup):
    waiting = State()
