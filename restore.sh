#!/bin/bash
set -e

BACKUP_DIR="$HOME/full-backups"
RESTORE_DIR="/tmp/syrcode_restore"

echo "============================================================"
echo "  Восстановление СырКода из бэкапа"
echo "============================================================"
echo ""

echo ">>> Доступные архивы:"
if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    echo "❌ Нет архивов в $BACKUP_DIR"
    read -p ">>> Укажи полный путь к архиву: " ARCHIVE
else
    ls -1t "$BACKUP_DIR"/syrcode_full_* 2>/dev/null | head -10 | nl -w2 -s'. '
    echo ""
    read -p ">>> Выбери номер (Enter — самый свежий): " CHOICE
    if [ -z "$CHOICE" ]; then
        ARCHIVE=$(ls -1t "$BACKUP_DIR"/syrcode_full_* 2>/dev/null | head -1)
    else
        ARCHIVE=$(ls -1t "$BACKUP_DIR"/syrcode_full_* 2>/dev/null | sed -n "${CHOICE}p")
    fi
fi

if [ ! -f "$ARCHIVE" ]; then
    echo "❌ Архив не найден: $ARCHIVE"
    exit 1
fi

echo ""
echo ">>> Выбран архив: $ARCHIVE"
ls -lh "$ARCHIVE"
echo ""

rm -rf "$RESTORE_DIR"
mkdir -p "$RESTORE_DIR"

if [[ "$ARCHIVE" == *.gpg ]]; then
    echo ">>> Архив зашифрован GPG"
    read -sp ">>> Пароль: " PASS
    echo ""
    PLAIN="/tmp/syrcode_restore_$$.tar.gz"
    if ! echo "$PASS" | gpg --batch --yes --passphrase-fd 0 -d -o "$PLAIN" "$ARCHIVE" 2>/dev/null; then
        echo "❌ Неверный пароль или ошибка расшифровки"
        rm -f "$PLAIN"
        exit 1
    fi
    echo ">>> ✅ Расшифровано"
    TAR="$PLAIN"
else
    TAR="$ARCHIVE"
fi

echo ">>> Распаковка..."
tar xzf "$TAR" -C "$RESTORE_DIR"
[ -f "/tmp/syrcode_restore_$$.tar.gz" ] && rm -f "/tmp/syrcode_restore_$$.tar.gz"
echo ">>> ✅ Распаковано в $RESTORE_DIR"
echo ""

if [ -f "$RESTORE_DIR/README.txt" ]; then
    echo "=== Информация об архиве ==="
    cat "$RESTORE_DIR/README.txt"
    echo ""
fi

echo "============================================================"
echo "  Что восстановить?"
echo "============================================================"
echo ""
echo "  1. Всё (код + конфиги + systemd)"
echo "  2. Только код бота"
echo "  3. Только .env и config.py"
echo "  4. Только конфиги Taskdog"
echo "  5. Только systemd-юниты"
echo "  6. Показать содержимое архива"
echo "  0. Отмена"
echo ""
read -p ">>> Твой выбор: " MODE

case "$MODE" in
    1|"")
        echo ""
        echo ">>> Восстанавливаем ВСЁ..."
        echo "  → Останавливаем сервисы..."
        sudo systemctl stop syrcode-bot 2>/dev/null || true
        systemctl --user stop whisper-server 2>/dev/null || true
        systemctl --user stop taskdog-server 2>/dev/null || true
        systemctl --user stop tg-ws-proxy 2>/dev/null || true

        SAVE_DIR="$HOME/pre-restore-backup-$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$SAVE_DIR"
        cp -r "$HOME/syrcode-bot" "$SAVE_DIR/" 2>/dev/null || true
        cp -r "$HOME/.config/taskdog" "$SAVE_DIR/taskdog" 2>/dev/null || true
        echo "  → Текущее состояние в $SAVE_DIR"

        if [ -d "$RESTORE_DIR/syrcode-bot" ]; then
            echo "  → Код бота..."
            cp -r "$RESTORE_DIR/syrcode-bot/"* "$HOME/syrcode-bot/" 2>/dev/null || true
            cp "$RESTORE_DIR/syrcode-bot/.env" "$HOME/syrcode-bot/" 2>/dev/null || true
            chmod 600 "$HOME/syrcode-bot/.env" 2>/dev/null || true
        fi

        if [ -d "$RESTORE_DIR/taskdog" ]; then
            echo "  → Конфиги Taskdog..."
            mkdir -p "$HOME/.config/taskdog"
            cp -r "$RESTORE_DIR/taskdog/"* "$HOME/.config/taskdog/" 2>/dev/null || true
            chmod 600 "$HOME/.config/taskdog/"*.toml 2>/dev/null || true
        fi

        if [ -d "$RESTORE_DIR/taskdog_data" ]; then
            echo "  → База задач..."
            for db in "$RESTORE_DIR/taskdog_data/"*; do
                [ -f "$db" ] || continue
                DEST=$(find "$HOME" -name "$(basename "$db")" 2>/dev/null | grep -i taskdog | head -1)
                [ -n "$DEST" ] && cp "$db" "$DEST"
            done
        fi

        if [ -d "$RESTORE_DIR/systemd" ]; then
            echo "  → Systemd-юниты..."
            sudo cp "$RESTORE_DIR/systemd/syrcode-bot.service" /etc/systemd/system/ 2>/dev/null || true
            mkdir -p "$HOME/.config/systemd/user"
            cp "$RESTORE_DIR/systemd/taskdog-server.service" "$HOME/.config/systemd/user/" 2>/dev/null || true
            cp "$RESTORE_DIR/systemd/tg-ws-proxy.service" "$HOME/.config/systemd/user/" 2>/dev/null || true
            cp "$RESTORE_DIR/systemd/whisper-server.service" "$HOME/.config/systemd/user/" 2>/dev/null || true
            sudo systemctl daemon-reload
            systemctl --user daemon-reload
        fi

        echo "  → Запускаем сервисы..."
        systemctl --user start tg-ws-proxy 2>/dev/null || true
        systemctl --user start taskdog-server 2>/dev/null || true
        systemctl --user start whisper-server 2>/dev/null || true
        sudo systemctl start syrcode-bot 2>/dev/null || true

        echo ""
        echo "✅ Восстановление завершено"
        ;;

    2)
        echo ""
        echo ">>> Только код бота..."
        if [ -d "$RESTORE_DIR/syrcode-bot" ]; then
            SAVE_DIR="$HOME/pre-restore-$(date +%Y%m%d_%H%M%S)"
            mkdir -p "$SAVE_DIR"
            cp -r "$HOME/syrcode-bot" "$SAVE_DIR/"
            cp -r "$RESTORE_DIR/syrcode-bot/"* "$HOME/syrcode-bot/"
            echo "✅ Код восстановлен. Старая версия в $SAVE_DIR"
            echo "   sudo systemctl restart syrcode-bot"
        fi
        ;;

    3)
        echo ""
        echo ">>> .env и config.py..."
        if [ -f "$RESTORE_DIR/syrcode-bot/.env" ]; then
            cp "$HOME/syrcode-bot/.env" "$HOME/syrcode-bot/.env.before-restore" 2>/dev/null || true
            cp "$RESTORE_DIR/syrcode-bot/.env" "$HOME/syrcode-bot/.env"
            chmod 600 "$HOME/syrcode-bot/.env"
            echo "  ✅ .env восстановлен"
        fi
        if [ -f "$RESTORE_DIR/syrcode-bot/config.py" ]; then
            cp "$RESTORE_DIR/syrcode-bot/config.py" "$HOME/syrcode-bot/config.py"
            echo "  ✅ config.py восстановлен"
        fi
        echo "   sudo systemctl restart syrcode-bot"
        ;;

    4)
        echo ""
        echo ">>> Конфиги Taskdog..."
        if [ -d "$RESTORE_DIR/taskdog" ]; then
            mkdir -p "$HOME/.config/taskdog"
            cp -r "$HOME/.config/taskdog" "$HOME/.config/taskdog.before-restore" 2>/dev/null || true
            cp -r "$RESTORE_DIR/taskdog/"* "$HOME/.config/taskdog/"
            chmod 600 "$HOME/.config/taskdog/"*.toml 2>/dev/null || true
            echo "  ✅ Восстановлено"
            echo "   systemctl --user restart taskdog-server"
        fi
        ;;

    5)
        echo ""
        echo ">>> Systemd-юниты..."
        if [ -d "$RESTORE_DIR/systemd" ]; then
            sudo cp "$RESTORE_DIR/systemd/syrcode-bot.service" /etc/systemd/system/ 2>/dev/null || true
            mkdir -p "$HOME/.config/systemd/user"
            cp "$RESTORE_DIR/systemd/taskdog-server.service" "$HOME/.config/systemd/user/" 2>/dev/null || true
            cp "$RESTORE_DIR/systemd/tg-ws-proxy.service" "$HOME/.config/systemd/user/" 2>/dev/null || true
            cp "$RESTORE_DIR/systemd/whisper-server.service" "$HOME/.config/systemd/user/" 2>/dev/null || true
            sudo systemctl daemon-reload
            systemctl --user daemon-reload
            echo "  ✅ Восстановлено"
        fi
        ;;

    6)
        echo ""
        echo ">>> Содержимое архива:"
        find "$RESTORE_DIR" -type f | head -50
        echo ""
        echo "Всего файлов: $(find "$RESTORE_DIR" -type f | wc -l)"
        ;;

    0)
        echo "Отмена."
        rm -rf "$RESTORE_DIR"
        exit 0
        ;;

    *)
        echo "❌ Неизвестный выбор: $MODE"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "  Готово!"
echo "============================================================"
echo ""
echo "Распакованное содержимое: $RESTORE_DIR"
echo "(можешь удалить: rm -rf $RESTORE_DIR)"
echo ""

if [ "$MODE" = "1" ]; then
    echo "=== Статус сервисов ==="
    echo "--- syrcode-bot ---"
    sudo systemctl status syrcode-bot --no-pager -n 3 2>/dev/null | head -5
    echo ""
    echo "--- taskdog-server ---"
    systemctl --user status taskdog-server --no-pager -n 2 2>/dev/null | head -4
    echo ""
    echo "--- tg-ws-proxy ---"
    systemctl --user status tg-ws-proxy --no-pager -n 2 2>/dev/null | head -4
fi
