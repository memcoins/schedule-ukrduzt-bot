from aiogram.fsm.state import State, StatesGroup


class Schedule(StatesGroup):
    step = State()
    day = State()
    faculty = State()
    course = State()
    group = State()
