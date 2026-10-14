# Telegram-бот: USD/KZT ежедневно в 12:00

Отправляет официальный курс доллара США к тенге, изменение по сравнению с предыдущей датой и источник данных. Данные берутся из официального сервиса Национального банка РК, а отправляются через Telegram Bot API. **Никакая платная LLM или API-ключ ИИ не нужны**.

## 1. Создайте Telegram-бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте `/newbot`, введите название и username с окончанием `bot`.
3. Сохраните токен, который пришлёт BotFather; никому не отправляйте его и не добавляйте в Git.
4. Откройте своего бота и нажмите **Start** (или отправьте `/start`). Иначе бот не сможет первым написать вам в личные сообщения.

## 2. Узнайте chat ID

После `/start` откройте адрес в браузере, заменив `<TOKEN>` на токен:

`https://api.telegram.org/bot<TOKEN>/getUpdates`

Ищите в JSON `"chat":{"id":123456789,...}` — число и есть ваш **TELEGRAM_CHAT_ID**. Если `result` пустой, напишите ещё одно сообщение боту и обновите страницу. Не делитесь полным URL: в нём секретный токен. Если настроен webhook, получение `getUpdates` может быть недоступно.

## 3. Создайте GitHub-репозиторий и загрузите файлы

Можно создать новый **private** репозиторий и загрузить содержимое этой папки, сохранив скрытую папку `.github/workflows`.

Убедитесь, что на основной ветке репозитория (обычно `main`) есть `.github/workflows/daily-rate.yml` и `main.py`.

### Добавьте два GitHub Actions secrets

`Settings → Secrets and variables → Actions → New repository secret`:

| Name | Value |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | токен от BotFather |
| `TELEGRAM_CHAT_ID` | найденный chat ID |

Оба значения храните только в Secrets. Не вставляйте их в код или README.

## 4. Протестируйте

Откройте вкладку **Actions → Daily USD/KZT Telegram rate → Run workflow**. В Telegram должно прийти сообщение. Права на Actions должны быть включены в настройках репозитория.

## 5. Автоматическое расписание

`.github/workflows/daily-rate.yml` настроен на `12:00` в часовом поясе `Asia/Almaty` каждый день, включая выходные.

**Ограничение:** GitHub Actions запускает `schedule` по возможности; старт может задержаться при высокой нагрузке, в редких случаях плановые запуски пропускаются. Для строго гарантированного времени лучше использовать постоянно работающий сервер/VPS с cron и мониторингом. В публичных репозиториях GitHub может автоматически отключить неактивные scheduled workflows через 60 дней: лучше создать private repo.

## Локальная проверка на Mac/Linux

```bash
export TELEGRAM_BOT_TOKEN='ВАШ_ТОКЕН'
export TELEGRAM_CHAT_ID='ВАШ_CHAT_ID'
python3 main.py
```

При ошибке бот ничего не выдумывает: сообщение не отправляется, задача помечается как ошибка в GitHub Actions.

## Полезные ссылки

- [Нацбанк РК: официальные курсы (RSS)](https://nationalbank.kz/ru/page/rss)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [GitHub Actions: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
