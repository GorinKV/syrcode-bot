"""Управление git-репозиториями: коммиты, статус, автокоммиты."""
import json
import os
from datetime import datetime

from git import Repo, InvalidGitRepositoryError

from core.orchestrator import ask_llm

PROJECTS_FILE = os.path.expanduser("~/.syrcode_projects.json")


def _load_projects():
    """Загружает список отслеживаемых проектов."""
    try:
        with open(PROJECTS_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_projects(projects):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


def add_project(path):
    """Добавляет проект в отслеживаемые."""
    path = os.path.abspath(os.path.expanduser(path))

    if not os.path.isdir(path):
        return f"⚠️ Путь не существует: {path}"

    if not os.path.isdir(os.path.join(path, ".git")):
        return f"⚠️ Это не git-репозиторий: {path}"

    projects = _load_projects()
    if path in projects:
        return f"ℹ️ Проект уже отслеживается: {path}"

    projects.append(path)
    _save_projects(projects)
    return f"✅ Проект добавлен: {path}"


def remove_project(path):
    """Убирает проект из отслеживаемых."""
    path = os.path.abspath(os.path.expanduser(path))
    projects = _load_projects()

    if path not in projects:
        return f"⚠️ Проект не найден в списке: {path}"

    projects.remove(path)
    _save_projects(projects)
    return f"🗑️ Проект убран: {path}"


def list_projects():
    """Показывает список отслеживаемых проектов."""
    projects = _load_projects()
    if not projects:
        return "📭 Проектов нет. Добавь: /git add ~/my-project"
    lines = [f"📂 Отслеживаемые проекты ({len(projects)}):"]
    for i, p in enumerate(projects, 1):
        repo_name = os.path.basename(p)
        lines.append(f"{i}. {repo_name} — {p}")
    return "\n".join(lines)


def _open_repo(path):
    try:
        return Repo(path), None
    except InvalidGitRepositoryError:
        return None, f"⚠️ Не git-репозиторий: {path}"
    except Exception as e:
        return None, f"⚠️ Ошибка git: {e}"


def get_status(path):
    """Показывает git status репозитория."""
    repo, err = _open_repo(path)
    if err:
        return err

    try:
        lines = [f"📂 {os.path.basename(path)}"]

        # Ветка
        try:
            branch = repo.active_branch.name
        except Exception:
            branch = "(detached)"
        lines.append(f"🌿 Ветка: {branch}")

        # Изменённые файлы
        changed = [item.a_path for item in repo.index.diff(None)]
        staged = [item.a_path for item in repo.index.diff("HEAD")]
        untracked = repo.untracked_files

        # Убираем дубли
        all_changed = sorted(set(changed + staged))

        if not all_changed and not untracked:
            lines.append("✨ Изменений нет")
        else:
            if all_changed:
                lines.append(f"📝 Изменённые ({len(all_changed)}):")
                for f in all_changed[:10]:
                    lines.append(f"  • {f}")
                if len(all_changed) > 10:
                    lines.append(f"  ... и ещё {len(all_changed) - 10}")
            if untracked:
                lines.append(f"🆕 Новые ({len(untracked)}):")
                for f in untracked[:10]:
                    lines.append(f"  • {f}")
                if len(untracked) > 10:
                    lines.append(f"  ... и ещё {len(untracked) - 10}")

        # Расстояние до origin
        try:
            if repo.remotes:
                ahead = 0
                behind = 0
                try:
                    ahead = len(list(repo.iter_commits(f"{branch}@{{u}}..{branch}")))
                except Exception:
                    pass
                try:
                    behind = len(list(repo.iter_commits(f"{branch}..{branch}@{{u}}")))
                except Exception:
                    pass
                if ahead or behind:
                    lines.append(f"📊 Локально: +{ahead} / -{behind} к origin")
        except Exception:
            pass

        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Ошибка git status: {e}"


def _get_diff_summary(repo, max_chars=3000):
    """Возвращает сокращённый diff для передачи в LLM."""
    try:
        # Изменения в рабочей директории
        diff = repo.git.diff("--stat")
        # Изменения в staged
        staged = repo.git.diff("--cached", "--stat")

        # Сырой diff (сокращённый)
        raw = repo.git.diff()
        staged_raw = repo.git.diff("--cached")

        combined = ""
        if staged:
            combined += f"=== STAGED ===\n{staged}\n\n"
        if diff:
            combined += f"=== UNSTAGED ===\n{diff}\n\n"

        if staged_raw:
            combined += f"=== STAGED DIFF ===\n{staged_raw[:1500]}\n\n"
        if raw:
            combined += f"=== UNSTAGED DIFF ===\n{raw[:1500]}"

        # Новые файлы
        untracked = repo.untracked_files
        if untracked:
            combined += f"\n\n=== NEW FILES ===\n" + "\n".join(untracked[:20])

        return combined[:max_chars] if combined else ""
    except Exception as e:
        return f"(не удалось получить diff: {e})"


async def generate_commit_message(repo):
    """Просит LLM сгенерировать осмысленное сообщение коммита."""
    diff_text = _get_diff_summary(repo)
    if not diff_text:
        return "update: minor changes"

    prompt = (
        "Ты — опытный разработчик. Составь короткое сообщение коммита на русском языке "
        "(одна строка, до 70 символов) для следующих изменений в git.\n\n"
        "Правила:\n"
        "- Начни с глагола в прошедшем времени: «добавил», «исправил», «обновил», «удалил», «переделал»\n"
        "- Без точки в конце\n"
        "- Без кавычек и префиксов типа feat:, fix:\n"
        "- Только описание сути, без перечисления всех файлов\n\n"
        f"Изменения:\n{diff_text}\n\n"
        "Ответь ТОЛЬКО текстом сообщения, без пояснений."
    )

    try:
        msg = await ask_llm(prompt)
        # Чистим
        msg = msg.strip().strip('"').strip("'").split("\n")[0]
        if len(msg) > 80:
            msg = msg[:77] + "..."
        return msg or "update: изменения"
    except Exception as e:
        return f"update: изменения ({datetime.now().strftime('%Y-%m-%d %H:%M')})"


async def commit_project(path, push=False):
    """Делает коммит в репозитории с LLM-сообщением."""
    repo, err = _open_repo(path)
    if err:
        return err

    try:
        # Есть ли что коммитить?
        has_changes = (
            bool(repo.untracked_files)
            or bool(list(repo.index.diff(None)))
            or bool(list(repo.index.diff("HEAD")))
        )
        if not has_changes:
            return f"✨ {os.path.basename(path)}: изменений нет."

        # Генерируем сообщение через LLM
        msg = await generate_commit_message(repo)

        # Добавляем всё
        repo.git.add(A=True)

        # Коммитим
        commit = repo.index.commit(msg)

        short_sha = commit.hexsha[:7]
        result = f"✅ {os.path.basename(path)}: [{short_sha}] {msg}"

        # Push (опционально)
        if push and repo.remotes:
            try:
                origin = repo.remote(name="origin")
                push_info = origin.push()
                if push_info:
                    result += "\n📤 Запушено в origin"
                else:
                    result += "\n⚠️ Не удалось запушить"
            except Exception as e:
                result += f"\n⚠️ Ошибка push: {e}"

        return result
    except Exception as e:
        return f"⚠️ Ошибка коммита: {e}"


async def auto_commit_all(push=False):
    """Автокоммит во всех отслеживаемых проектах. Для scheduler."""
    projects = _load_projects()
    if not projects:
        return None

    results = []
    for path in projects:
        if not os.path.isdir(path):
            continue

        repo, err = _open_repo(path)
        if err:
            continue

        # Проверяем, есть ли изменения
        has_changes = (
            bool(repo.untracked_files)
            or bool(list(repo.index.diff(None)))
            or bool(list(repo.index.diff("HEAD")))
        )
        if not has_changes:
            continue

        result = await commit_project(path, push=push)
        results.append(result)

    if not results:
        return None

    return "🤖 Автокоммит:\n\n" + "\n".join(results)


def get_projects_count():
    """Возвращает количество отслеживаемых проектов (для scheduler)."""
    return len(_load_projects())
