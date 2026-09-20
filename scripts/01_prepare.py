#!/usr/bin/env python3
"""Chat River · шаг 1: нормализация экспорта Telegram в локальные Parquet-таблицы.

Использование: python scripts/01_prepare.py "/path/to/DataExport/result.json"
Выход: data/messages.parquet, data/chats.parquet (только на этой машине).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
TOKEN_RE = re.compile(r'[а-яёa-z0-9]+')
URL_RE = re.compile(r'(?:https?://|www\.)\S+', re.IGNORECASE)


def flat_text(msg):
    t = msg.get('text', '')
    if isinstance(t, str):
        return t
    return ''.join(p if isinstance(p, str) else p.get('text', '') for p in t)


def main():
    if len(sys.argv) < 2:
        sys.exit('Укажи путь к result.json: python scripts/01_prepare.py "/path/to/result.json"')
    src = Path(sys.argv[1])
    if src.is_dir():
        src = src / 'result.json'
    if not src.exists():
        sys.exit(f'Не найден файл: {src}\nЭкспорт должен быть в формате JSON (не HTML).')

    print(f'читаю {src} …', flush=True)
    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    chats = data.get('chats', {}).get('list', [])
    if not chats:
        sys.exit('В файле нет chats.list — это точно machine-readable JSON-экспорт?')

    # определяем владельца: id чата «Избранное» совпадает с user id владельца
    me_id = None
    for c in chats:
        if c.get('type') == 'saved_messages':
            me_id = f"user{c['id']}"
            break
    if me_id is None:  # запасной путь: самый частый from_id
        votes = defaultdict(int)
        for c in chats:
            for m in c.get('messages', []):
                if m.get('from_id'):
                    votes[m['from_id']] += 1
        me_id = max(votes, key=votes.get)
    print(f'владелец корпуса: {me_id}', flush=True)

    cols = defaultdict(list)
    chat_rows = []
    for c in chats:
        n = 0
        for m in c.get('messages', []):
            date = m.get('date', '')
            if m.get('type') != 'message' or date.startswith('1970'):
                continue
            n += 1
            text = flat_text(m)
            low = URL_RE.sub(' ', text).lower().replace('ё', 'е')
            cols['chat_id'].append(c['id'])
            cols['msg_id'].append(m['id'])
            cols['ts'].append(date)
            cols['is_mine'].append(m.get('from_id') == me_id)
            cols['is_forwarded'].append('forwarded_from' in m)
            cols['text'].append(text)
            cols['n_tokens'].append(sum(1 for t in TOKEN_RE.findall(low) if len(t) >= 2))
        chat_rows.append({'chat_id': c['id'], 'name': c.get('name') or '(без имени)',
                          'type': c.get('type') or 'unknown', 'n_messages': n})

    DATA.mkdir(exist_ok=True)
    arrays = []
    for k, v in cols.items():
        arr = pa.array(v)
        if k == 'ts':
            arr = arr.cast(pa.timestamp('s'))
        arrays.append(arr)
    table = pa.Table.from_arrays(arrays, names=list(cols.keys()))
    pq.write_table(table, DATA / 'messages.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(chat_rows), DATA / 'chats.parquet', compression='zstd')

    mine = sum(cols['is_mine'])
    months = {d[:7] for d in cols['ts']}
    print(f'готово: сообщений {table.num_rows} (моих {mine}), чатов {len(chat_rows)}, '
          f'месяцев {len(months)} ({min(months)} — {max(months)})')
    print('дальше: python scripts/02_ngram.py && python scripts/03_river.py && python scripts/04_big5.py')


if __name__ == '__main__':
    main()
