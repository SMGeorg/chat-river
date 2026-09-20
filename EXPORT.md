# Как выгрузить свою переписку из Telegram

Пайплайну нужен **полный machine-readable JSON-экспорт**. Эта страница — пошагово,
с точными галочками. Время выгрузки большого аккаунта — от минут до нескольких часов
(Telegram может дополнительно наложить суточную задержку на первый экспорт — это
защита от угона аккаунта, просто подожди и повтори).

## Где вообще есть кнопка экспорта

Экспорт умеет **только настольный Telegram на движке tdesktop**:

- **macOS**: приложение **Telegram Lite** (App Store) — в «обычном» Telegram для macOS
  из App Store функции экспорта НЕТ. Альтернатива — Telegram Desktop с telegram.org.
- **Windows / Linux**: обычный Telegram Desktop (telegram.org).
- В мобильных приложениях экспорта нет.

Путь: **Settings → Advanced → Export Telegram data**.

## Галочки: что включить и что выключить

### 1. Личные данные — всё ВЫКЛЮЧИТЬ (пайплайну не нужны)

- ☐ Account information
- ☐ Contacts list
- ☐ Story archive
- ☐ Music on Profile

### 2. Чаты — всё ВКЛЮЧИТЬ

- ☑ Personal chats
- ☑ Bot chats
- ☑ Private groups
- ☑ Private channels
- ☑ Public groups
- ☑ Public channels

**Самое важное место всего экспорта** — вложенные галочки «Only my messages»:

- у **Private groups** и **Private channels** — **СНЯТЬ** «Only my messages».
  Если оставить, в группах выгрузятся только твои реплики, и половина картины пропадёт.
- у Public groups и Public channels галочка «Only my messages» зажата намертво —
  это ограничение Telegram, снять её нельзя. Публичные группы в экспорте всегда
  односторонние; пайплайн это учитывает.

### 3. Media export settings — всё ВЫКЛЮЧИТЬ

- ☐ Photos, ☐ Videos, ☐ Voice messages, ☐ Video messages, ☐ Stickers, ☐ GIFs, ☐ Files

Пайплайн работает только с текстами. Медиа раздувают экспорт на десятки гигабайт
и не используются. Ползунок Size limit при снятых галочках ни на что не влияет.

### 4. Location and format

- ⦿ **Machine-readable JSON** — обязательно. Human-readable HTML пайплайн не читает.
- Папку назначения запомни: внутри появится файл **`result.json`** — это и есть вход
  для `scripts/01_prepare.py`.

## Проверка, что экспорт правильный

1. В папке экспорта лежит `result.json` (а не куча `.html`).
2. Файл весит сообразно жизни: годы активной переписки — это сотни мегабайт.
3. `python scripts/01_prepare.py "<путь к result.json>"` печатает счётчики сообщений
   и чатов без ошибок.

Типичные ошибки: выбран HTML вместо JSON; забыта галочка «Only my messages» у приватных
групп (симптом: в группах подозрительно мало сообщений); экспорт прерван до конца.
