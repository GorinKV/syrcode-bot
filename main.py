import asyncio
import logging
import os
from io import BytesIO

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN
from core.orchestrator import ask_llm
from core.task_manager import (
    add_task,
    list_tasks,
    list_all_tasks,
    list_completed_month,
    list_completed_tasks,
    list_completed_year,
    delete_task,
    clear_tasks,
    resolve_and_delete,
    resolve_done,
    mark_done_by_position,
    get_tasks_list,
)
from core.file_keeper import log_to_file
from core.voice_handler import transcribe_voice, extract_command
from core.natural_commands import parse
from core.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)

session = AiohttpSession(proxy="socks5://127.0.0.1:1443")
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

CHAT_ID_FILE = "data/chat_id.txt"


def _save_chat_id(chat_id: int):
    os.makedirs(os.path.dirname(CHAT_ID_FILE), exist_ok=True)
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(chat_id))


HELP_TEXT = (
    "🤖 Что я понимаю:\n\n"
    "📋 Задачи:\n"
    "  • надо позвонить маме\n"
    "  • нужно купить молоко\n"
    "  • сделай встречу с поставщиком\n"
    "  • написать пост про камамбер\n\n"
    "⏰ Сроки и важность:\n"
    "  • надо позвонить маме завтра\n"
    "  • важно сварить сыр в субботу\n"
    "  • срочно купить молоко до пятницы\n\n"
    "💡 Идеи:\n"
    "  • идея — сыр с трюфелем\n\n"
    "✅ Отметить сделанным:\n"
    "  • сделал первое\n"
    "  • выполнил #3\n"
    "  • /done 1\n\n"
    "📊 Списки:\n"
    "  • покажи задачи — активные\n"
    "  • все задачи — активные + выполненные\n"
    "  • выполненные за месяц\n"
    "  • выполненные за год\n\n"
    "🗑️ Удаление:\n"
    "  • удали первую задачу\n"
    "  • удали #3\n"
    "  • удали все задачи\n\n"
    "🛠 Команды:\n"
    "  • /task Название — создать\n"
    "  • /tasks — активные задачи\n"
    "  • /all — все задачи\n"
    "  • /month — выполнено за месяц\n"
    "  • /year — выполнено за год\n"
    "  • /done N — отметить выполненной\n"
    "  • /del N — удалить\n"
    "  • /clear — очистить всё\n"
    "  • /chatid — узнать chat_id\n"
    "  • /help — справка\n\n"
    "🕐 Автоотчёты (МСК):\n"
    "  • 07:00 — утренний дайджест\n"
    "  • 17:00 — напоминание о сроках\n"
    "  • 20:40 — вечерний отчёт\n\n"
    "🎤 Голосовые тоже работают."
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    _save_chat_id(message.chat.id)
    await message.answer(HELP_TEXT)
    log_to_file(message.text, HELP_TEXT)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(HELP_TEXT)
    log_to_file(message.text, HELP_TEXT)


@dp.message(Command("chatid"))
async def cmd_chatid(message: types.Message):
    _save_chat_id(message.chat.id)
    await message.answer(f"🆔 Твой chat_id: {message.chat.id}\n\nСохранён для автоотчётов.")
    log_to_file(message.text, f"chat_id={message.chat.id}")


@dp.message(Command("task"))
async def cmd_task(message: types.Message):
    task_text = message.text.replace("/task", "", 1).strip()
    if not task_text:
        await message.answer("Укажи название: /task Позвонить поставщику")
        return
    result = add_task(task_text)
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    result = list_tasks(sort_by_deadline=True)
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("all"))
async def cmd_all(message: types.Message):
    result = list_all_tasks()
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("completed"))
async def cmd_completed(message: types.Message):
    result = list_completed_tasks()
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("month"))
async def cmd_month(message: types.Message):
    result = list_completed_month()
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("year"))
async def cmd_year(message: types.Message):
    result = list_completed_year()
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("done"))
async def cmd_done(message: types.Message):
    arg = message.text.replace("/done", "", 1).strip()
    if not arg:
        await message.answer("Укажи номер: /done 1 или /done #3")
        return
    if arg.startswith("#") and arg[1:].isdigit():
        result = mark_done_by_position(int(arg[1:]))
    elif arg.isdigit():
        result = mark_done_by_position(int(arg))
    else:
        await message.answer("Укажи номер: /done 1 или /done #3")
        return
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("del"))
async def cmd_delete(message: types.Message):
    arg = message.text.replace("/del", "", 1).strip()
    if not arg:
        await message.answer("Укажи номер: /del 1 или /del #3")
        return
    if arg.startswith("#") and arg[1:].isdigit():
        result = resolve_and_delete({"action": "delete_by_real_id", "id": int(arg[1:])})
    elif arg.isdigit():
        result = resolve_and_delete({"action": "delete_by_id", "id": int(arg)})
    else:
        await message.answer("Укажи номер: /del 1 или /del #3")
        return
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    result = clear_tasks()
    log_to_file(message.text, result)
    await message.answer(result)


@dp.message(F.voice)
async def handle_voice(message: types.Message):
    _save_chat_id(message.chat.id)
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        file = await bot.get_file(message.voice.file_id)
        buffer = BytesIO()
        await bot.download_file(file_path=file.file_path, destination=buffer)
        audio_bytes = buffer.getvalue()

        transcript = await transcribe_voice(audio_bytes, "voice.ogg")
        if transcript.startswith("__ERROR__"):
            await message.answer(f"⚠️ {transcript.replace('__ERROR__: ', '')}")
            return

        cmd = parse(transcript)
        if cmd["action"] != "none":
            await handle_parsed_command(message, transcript, cmd)
            return

        vcmd = extract_command(transcript)
        if vcmd["type"] == "idea":
            log_to_file(f"[ГОЛОС] {transcript}", f"Идея: {vcmd['text']}")
            await message.answer(
                f"💡 Идея записана: «{vcmd['text'] or transcript}»\n\n"
                f"_(распознано: {transcript})_"
            )
        elif vcmd["type"].startswith("task"):
            title = vcmd["text"] or transcript
            result = add_task(title)
            log_to_file(f"[ГОЛОС] {transcript}", result)
            await message.answer(f"{result}\n\n_(распознано: {transcript})_")
        else:
            response = await ask_llm(transcript)
            log_to_file(f"[ГОЛОС] {transcript}", response)
            await message.answer(f"🎤 _{transcript}_\n\n{response}")

    except Exception as e:
        await message.answer(f"⚠️ Ошибка обработки голосового: {e}")


async def handle_parsed_command(message: types.Message, source_text: str, cmd: dict):
    action = cmd["action"]

    if action == "help":
        result = HELP_TEXT
    elif action == "list_tasks":
        result = list_tasks(sort_by_deadline=True)
    elif action == "list_all":
        result = list_all_tasks()
    elif action == "list_completed":
        result = list_completed_tasks()
    elif action == "list_completed_month":
        result = list_completed_month()
    elif action == "list_completed_year":
        result = list_completed_year()
    elif action == "add_idea":
        idea_text = cmd.get("text") or source_text
        result = f"💡 Идея записана: «{idea_text}»"
    elif action == "add_task":
        result = add_task(
            cmd["title"],
            deadline=cmd.get("deadline"),
            important=cmd.get("important", False),
        )
    elif action in (
        "clear_all",
        "delete_by_real_id",
        "delete_by_id",
        "delete_by_ordinal",
        "delete_by_name",
    ):
        result = resolve_and_delete(cmd)
    elif action in (
        "done_by_real_id",
        "done_by_id",
        "done_by_ordinal",
        "done_by_name",
    ):
        result = resolve_done(cmd)
    else:
        result = f"⚠️ Не понял команду: {action}"

    log_to_file(source_text, result)
    await message.answer(result)


@dp.message(F.text)
async def handle_natural(message: types.Message):
    _save_chat_id(message.chat.id)
    cmd = parse(message.text)
    if cmd["action"] == "none":
        await bot.send_chat_action(message.chat.id, "typing")
        response = await ask_llm(message.text)
        log_to_file(message.text, response)
        await message.answer(response)
        return

    await bot.send_chat_action(message.chat.id, "typing")
    await handle_parsed_command(message, message.text, cmd)


@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пока я понимаю только текст и голосовые.")
        return
    _save_chat_id(message.chat.id)
    await bot.send_chat_action(message.chat.id, "typing")
    response = await ask_llm(message.text)
    log_to_file(message.text, response)
    await message.answer(response)


async def main():
    scheduler = setup_scheduler(bot)
    scheduler.start()
    print(">>> [main] Планировщик запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
