#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$HOME/full-backups"
TMP_DIR="/tmp/syrcode_full_$DATE"
ARCHIVE_PLAIN="$BACKUP_DIR/syrcode_full_$DATE.tar.gz"
ARCHIVE="$BACKUP_DIR/syrcode_full_$DATE.tar.gz.gpg"
KEEP=5

mkdir -p "$BACKUP_DIR"
mkdir -p "$TMP_DIR"

echo ">>> Собираем всё в $TMP_DIR ..."

# 1. Проект бота
mkdir -p "$TMP_DIR/syrcode-bot"
cd "$HOME/syrcode-bot"
tar cf - --exclude=venv --exclude=.git --exclude=__pycache__ --exclude='*.bak*' . | (cd "$TMP_DIR/syrcode-bot" && tar xf -)
echo "  ✅ syrcode-bot (включая .env)"

# 2. Taskdog конфиг
mkdir -p "$TMP_DIR/taskdog"
cp -r "$HOME/.config/taskdog/"* "$TMP_DIR/taskdog/" 2>/dev/null || true
echo "  ✅ taskdog configs"

# 3. Taskdog БД — берём напрямую + ищем дополнительно
mkdir -p "$TMP_DIR/taskdog_data"
TASKDOG_DB="$HOME/.local/share/taskdog/tasks.db"
if [ -f "$TASKDOG_DB" ]; then
    cp "$TASKDOG_DB" "$TMP_DIR/taskdog_data/"
    echo "  ✅ taskdog database (tasks.db)"
else
    echo "  ⚠️ tasks.db не найден по стандартному пути, ищем..."
    TASKDOG_DATA=$(find "$HOME" -name "tasks.db" -o -name "*.sqlite" -o -name "*.db" 2>/dev/null | grep -i taskdog | head -5)
    if [ -n "$TASKDOG_DATA" ]; then
        for db in $TASKDOG_DATA; do
            cp "$db" "$TMP_DIR/taskdog_data/" 2>/dev/null || true
        done
        echo "  ✅ taskdog database (найдено: $(echo $TASKDOG_DATA | wc -w))"
    fi
fi

# 4. tg-ws-proxy
if [ -d "$HOME/tg-ws-proxy" ]; then
    mkdir -p "$TMP_DIR/tg-ws-proxy"
    cd "$HOME/tg-ws-proxy"
    git log --oneline -1 > "$TMP_DIR/tg-ws-proxy/COMMIT.txt" 2>/dev/null || true
    git remote -v > "$TMP_DIR/tg-ws-proxy/REMOTE.txt" 2>/dev/null || true
    echo "  ✅ tg-ws-proxy"
fi

# 5. Whisper
if [ -d "$HOME/whisper.cpp/models" ]; then
    mkdir -p "$TMP_DIR/whisper"
    ls -lh "$HOME/whisper.cpp/models/" > "$TMP_DIR/whisper/models_list.txt" 2>/dev/null || true
    echo "  ✅ whisper models list"
fi

# 6. Systemd
mkdir -p "$TMP_DIR/systemd"
cp /etc/systemd/system/syrcode-bot.service "$TMP_DIR/systemd/" 2>/dev/null || true
cp "$HOME/.config/systemd/user/taskdog-server.service" "$TMP_DIR/systemd/" 2>/dev/null || true
cp "$HOME/.config/systemd/user/tg-ws-proxy.service" "$TMP_DIR/systemd/" 2>/dev/null || true
cp "$HOME/.config/systemd/user/whisper-server.service" "$TMP_DIR/systemd/" 2>/dev/null || true
echo "  ✅ systemd units"

# 7. Requirements
cd "$HOME/syrcode-bot"
source venv/bin/activate
pip freeze > "$TMP_DIR/requirements.freeze.txt"
echo "  ✅ requirements"

# 8. Git projects
[ -f "$HOME/.syrcode_projects.json" ] && cp "$HOME/.syrcode_projects.json" "$TMP_DIR/" && echo "  ✅ git projects"

# 9. README
cat > "$TMP_DIR/README.txt" << README
Полный бэкап СырКода (зашифрован)
==================================
Дата: $(date '+%Y-%m-%d %H:%M:%S')
Хост: $(hostname)

⚠️ АРХИВ ЗАШИФРОВАН GPG
Расшифровка: gpg -d syrcode_full_*.tar.gz.gpg > backup.tar.gz
Затем: tar xzf backup.tar.gz -C /tmp/

Содержимое:
  syrcode-bot/         — код бота + .env
  taskdog/             — конфиги Taskdog
  taskdog_data/        — база задач
  tg-ws-proxy/         — инфа о прокси
  whisper/             — список моделей
  systemd/             — юниты сервисов
  requirements.freeze.txt
README

echo ""
echo ">>> Упаковываем..."
tar czf "$ARCHIVE_PLAIN" -C "$TMP_DIR" .

# Шифрование
echo ""
read -sp ">>> Пароль для шифрования (Enter — без шифрования): " PASS
echo ""

if [ -n "$PASS" ]; then
    echo "$PASS" | gpg --batch --yes --passphrase-fd 0 --symmetric --cipher-algo AES256 -o "$ARCHIVE" "$ARCHIVE_PLAIN"
    rm -f "$ARCHIVE_PLAIN"
    FINAL="$ARCHIVE"
    echo ">>> ✅ Архив зашифрован"
else
    FINAL="$ARCHIVE_PLAIN"
    echo ">>> ✅ Архив без шифрования"
fi

SIZE=$(du -h "$FINAL" | cut -f1)
echo ">>> Размер: $SIZE"

echo ""
echo ">>> Чистим старые (оставляем $KEEP)..."
cd "$BACKUP_DIR"
ls -1t syrcode_full_*.tar.gz* 2>/dev/null | tail -n +$((KEEP + 1)) | while read old; do
    rm -f "$old"
    echo "  удалён: $old"
done

rm -rf "$TMP_DIR"

echo ""
echo "============================================================"
echo "✅ Бэкап готов!"
echo "============================================================"
echo "Архив: $FINAL"
echo "Размер: $SIZE"
echo ""
echo "Последние бэкапы:"
ls -lht "$BACKUP_DIR"/syrcode_full_* 2>/dev/null | head -$KEEP | awk '{print "  " $9 " (" $5 ")"}'
echo "============================================================"
