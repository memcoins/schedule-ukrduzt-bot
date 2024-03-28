import asyncio
import logging
from os import getenv
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from config.utils import *
from config.states import *
from config.constants import *
from config.database import Database

# Connect Telegram Bot
TOKEN = getenv("TOKEN_BOT")
ADMIN = getenv("ADMIN")
dp = Dispatcher()
# Connect Database
db = Database()


def get_current_week() -> tuple[str, str]:
    today = date.today()
    day = datetime.now().strftime('%A')
    week_number = today.isocalendar()[1]
    current_word = "Парна" if week_number % 2 != 0 else "Непарна"
    return current_word, day


@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❗️ Скасовано")


@dp.message(CommandStart())
async def start_bot(message: Message) -> None:
    db.add_user(user_id=message.from_user.id, username=message.from_user.username)
    week, _ = get_current_week()

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Розклад занять", callback_data="schedule"))
    if str(message.from_user.id) == ADMIN:
        kb.add(InlineKeyboardButton(text="⚡️ Панель розробника", callback_data="admin_panel"))
    kb.adjust(1)

    await message.answer(
        text=f"✋ Привіт, я допоможу дізнатися актуальний розклад на тиждень\n\n"
             f"📆 Поточна неділя - *{week}*",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.callback_query(lambda call: call.data == "admin_panel")
async def admin_panel(call: CallbackQuery) -> None:
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="👤 Користувачі", callback_data="count_users"))
    kb.adjust(1)
    await call.message.edit_text(text="Виберіть, що хочете зробити ⬇️", reply_markup=kb.as_markup())


@dp.callback_query(lambda call: call.data == "count_users")
async def count_users(call: CallbackQuery) -> None:
    users = len(db.get_users())
    repr(users)
    await call.message.edit_text(text=f"👥 *Кількість користувачів:* {users}", parse_mode=ParseMode.MARKDOWN)


@dp.callback_query(lambda call: call.data == "schedule")
async def get_day(call: CallbackQuery, state: FSMContext) -> None:
    user = db.get_user(user_id=call.from_user.id)
    kb = InlineKeyboardBuilder()
    if user[5] is None:
        buttons = [InlineKeyboardButton(text=week_day.split("_")[0], callback_data=f'{week_day}') for week_day in
                   week_days_first]
    else:
        buttons = [InlineKeyboardButton(text=week_day.split("-")[0], callback_data=f'{week_day}') for week_day in
                   week_days_h]
        kb.add(InlineKeyboardButton(text="📝 Змінити групу", callback_data="change_user_data"))
    kb.add(*buttons).adjust(1)
    await call.message.edit_text(text="Виберіть день ⬇️", reply_markup=kb.as_markup())
    await state.set_state(Schedule.day)
    await state.update_data(step=0)


@dp.callback_query(lambda call: call.data == "change_user_data" or call.data in week_days_first)
async def get_faculty(call: CallbackQuery, state: FSMContext) -> None:
    if call.data == "change_user_data":
        await state.update_data(day=week_days_first[0], step=1)
    else:
        await state.update_data(day=call.data, step=1)
    faculties = get_faculties()
    kb = InlineKeyboardBuilder()
    buttons = [InlineKeyboardButton(text=faculty, callback_data=f'faculty_{faculty_id}') for faculty_id, faculty in
               faculties.items()]
    kb.add(*buttons).adjust(1)
    kb.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule")).adjust(1)
    await call.message.edit_text(text="Виберіть факультатив ⬇️", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("faculty_"))
async def get_course(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(faculty=call.data, step=2)
    kb = InlineKeyboardBuilder()
    buttons = [InlineKeyboardButton(text=f'{i}-й курс', callback_data=f'course_{i}') for i in range(1, 6+1)]
    kb.add(*buttons).adjust(1)
    await call.message.edit_text(text="Виберіть курс ⬇️", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("course_"))
async def get_group(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(course=call.data, step=3)
    kb = InlineKeyboardBuilder()
    user_data = await state.get_data()
    faculty = user_data["faculty"].split("_")[1]
    course = user_data["course"].split("_")[1]
    groups = get_groups(faculty, course)
    for group_id, group_name in groups.items():
        kb.add(InlineKeyboardButton(text=f'{group_name}', callback_data=f'{group_id}'))
    kb.adjust(1)
    await call.message.edit_text(text="Виберіть групу ⬇️", reply_markup=kb.as_markup())


@dp.callback_query(lambda call: call.data.isdigit() and len(call.data) == 5 or call.data in week_days_h)
async def get_schedule(call: CallbackQuery, state: FSMContext) -> None:
    week, current_day = get_current_week()

    if call.data.isdigit() and len(call.data) == 5:
        await state.update_data(group=call.data, step=4)
        user_data = await state.get_data()
        week_day = user_data["day"]
        week_day_sel = week_day.split("_")[0]
        faculty = user_data["faculty"].split("_")[1]
        course = int(user_data["course"].split("_")[1])
        group = user_data["group"]
        db.update_user(faculty=faculty, course=course, group=group, user_id=call.from_user.id)
        schedule = get_schedules(week, week_day.split("_")[1], current_day, faculty, course, group)
    else:
        await state.update_data(day=call.data, step=1)
        user_data = db.get_user(call.from_user.id)
        week_day = (await state.get_data())["day"]
        week_day_sel = week_day.split("-")[0]
        faculty, course, group = user_data[3:6]
        schedule = get_schedules(week, week_day.split("-")[1], current_day, faculty, course, group)

    subjects, change_week = schedule

    if not subjects:
        text = f"🔍 На *цей* день ваш розклад вільний\n\n⏰Вибраний день - *{week_day_sel}* \n📆Поточна неділя - *{week}*"
    else:
        text_message = "\n".join(f"{subject_id}: *{subject_name}*" for subject_id, subject_name in subjects.items())
        week_str = "наступний" if change_week else "цей"
        text = f"🔔Показано розклад на *{week_str}* тиждень\n\n{text_message}\n\n⏰Вибраний день - *{week_day_sel}* \n📆Поточна неділя - *{week}*"

    await call.message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)
    await state.clear()


async def main() -> None:
    bot = Bot(TOKEN)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    db.check_database()
    asyncio.run(main())
