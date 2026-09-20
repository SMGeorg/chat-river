#!/usr/bin/env python3
"""Создаёт demo/result.json — синтетический мини-экспорт для проверки пакета без данных.
В демо-жизнь вшита эмоциональная дуга (холодное начало → тёплое плато → просадка),
чтобы страницы выглядели как настоящие. Все имена и тексты вымышлены."""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
random.seed(7)

WORDS = ('привет как дела работа проект встреча завтра лодка поход кино '
         'идея код данные книга музыка чай извини пожалуйста ахаха план отчет спорт '
         'бег горы море фильм ужин совет').split()
POS_W = 'круто люблю здорово отлично классно счастлив рад кайф'.split()
NEG_W = 'устал грустно бесит тревожно страшно тоска раздражает одиноко'.split()

DAYS = 730

def mood(day):
    """Дуга настроения демо-жизни: холодное начало → тёплое плато → просадка в конце."""
    x = day / DAYS
    if x < 0.25:
        return -0.5 + x * 3.4
    if x < 0.8:
        return 0.35
    return 0.35 - (x - 0.8) * 3.0

def msg(mid, ts, mine, me_id, other_id, m=0.0):
    n = random.randint(2, 12)
    words = random.choices(WORDS, k=n)
    r = random.random()
    if r < 0.15 + max(0.0, m) * 0.5:
        words.append(random.choice(POS_W))
    if r > 1 - (0.08 + max(0.0, -m) * 0.6):
        words.append(random.choice(NEG_W))
    return {'id': mid, 'type': 'message', 'date': ts.strftime('%Y-%m-%dT%H:%M:%S'),
            'from': 'Me' if mine else 'Friend',
            'from_id': me_id if mine else other_id,
            'text': ' '.join(words), 'text_entities': []}

me = 999001
chats = [{'name': None, 'type': 'saved_messages', 'id': me, 'messages': []}]
mid = 1
for k, (name, oid) in enumerate([('Алекс', 'user111'), ('Мария', 'user222'), ('Илья', 'user333')]):
    msgs = []
    t = datetime(2024, 1, 1, 10, 0)
    for d in range(DAYS):
        t2 = t + timedelta(days=d)
        for _ in range(random.randint(0, 4 - k)):
            t2 += timedelta(minutes=random.randint(1, 300))
            msgs.append(msg(mid, t2, random.random() < 0.5, f'user{me}', oid, mood(d)))
            mid += 1
    chats.append({'name': name, 'type': 'personal_chat', 'id': 111000 + k, 'messages': msgs})

out = ROOT / 'demo'
out.mkdir(exist_ok=True)
json.dump({'about': 'demo', 'chats': {'list': chats}},
          open(out / 'result.json', 'w'), ensure_ascii=False)
print(f'demo/result.json: {mid - 1} сообщений, {len(chats)} чата')
