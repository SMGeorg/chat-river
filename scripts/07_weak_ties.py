#!/usr/bin/env python3
"""Chat River · шаг 7: «Слабые связи» — долгоживущие тонкие русла.

Рамка: Granovetter, The Strength of Weak Ties (AJS, 1973). Слабая связь — человек,
чьё русло слишком тонкое, чтобы разглядеть его в большой реке, но оно не пересыхает
годами: активность возвращается эпизодами. Прозрачные пороги (личные чаты):
дуга жизни ≥ 24 мес · ≥ 3 эпизода активности (паузы ≥ 4 мес) · ≤ 40 сообщ/активный
месяц · всего ≤ 1500 · у каждой стороны ≥ 10 сообщений. «Затухла» = тишина ≥ 12 мес.

Работает на любом уровне обработки: без шага 5 бусины серые; если data/llm_valence.parquet
существует — бусины окрашиваются тоном твоих сообщений месяца.
Клик по имени открывает профиль человека в Telegram (ссылка tg://user?id=…).

Выход: out/weak-ties.html. Всё локально.
"""
import json
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = ROOT / 'out'
con = duckdb.connect()

rows = con.execute(f"""
    SELECT m.chat_id, c.name, strftime(m.ts,'%Y-%m') mm,
           SUM(m.is_mine::int) mine, SUM((NOT m.is_mine)::int) other
    FROM '{DATA / 'messages.parquet'}' m
    JOIN '{DATA / 'chats.parquet'}' c USING (chat_id)
    WHERE c.type = 'personal_chat'
    GROUP BY 1,2,3""").fetchall()

months_all = [r[0] for r in con.execute(f"""
    SELECT DISTINCT strftime(ts,'%Y-%m') FROM '{DATA / 'messages.parquet'}' ORDER BY 1""").fetchall()]
mi = {m: i for i, m in enumerate(months_all)}
LAST = months_all[-1]

def midx(mm):
    return int(mm[:4]) * 12 + int(mm[5:])

chats = defaultdict(dict)
names = {}
for cid, nm, mm, mine, other in rows:
    chats[cid][mm] = (mine, other)
    names[cid] = nm or '(без имени)'

ties = []
for cid, mon in chats.items():
    act = sorted(m for m, (a, b) in mon.items() if a + b >= 2)
    if len(act) < 3:
        continue
    idx = [midx(m) for m in act]
    span = idx[-1] - idx[0] + 1
    mine_t = sum(a for a, _ in mon.values())
    other_t = sum(b for _, b in mon.values())
    total = mine_t + other_t
    episodes = 1 + sum(1 for i in range(1, len(idx)) if idx[i] - idx[i-1] >= 4)
    if not (span >= 24 and episodes >= 3 and total / len(act) <= 40
            and total <= 1500 and mine_t >= 10 and other_t >= 10):
        continue
    ties.append({'uid': cid, 'name': names[cid], 'span': span, 'episodes': episodes,
                 'act': len(act), 'total': total,
                 'first': act[0], 'last': act[-1],
                 'silent': midx(LAST) - idx[-1],
                 'months': {mi[m]: [mon[m][0], mon[m][1]] for m in mon if m in mi and sum(mon[m]) >= 1},
                 'tone': {}})

ties.sort(key=lambda t: -t['span'])

if (DATA / 'llm_valence.parquet').exists() and ties:
    ids = tuple(t['uid'] for t in ties) + (0, 0)
    vrows = con.execute(f"""
        SELECT v.chat_id, strftime(m.ts,'%Y-%m'), AVG(v.valence)
        FROM '{DATA / 'llm_valence.parquet'}' v
        JOIN '{DATA / 'messages.parquet'}' m
          ON v.chat_id = m.chat_id AND v.msg_id = m.msg_id
        WHERE v.chat_id IN {ids}
        GROUP BY 1, 2""").fetchall()
    tone = defaultdict(dict)
    for cid, mm, av in vrows:
        if mm in mi:
            tone[cid][mi[mm]] = round(float(av), 2)
    for t in ties:
        t['tone'] = tone.get(t['uid'], {})

print(f"слабых связей: {len(ties)} (живых {sum(1 for t in ties if t['silent'] < 12)}, "
      f"затухших {sum(1 for t in ties if t['silent'] >= 12)})")

payload = {'months': months_all, 'ties': ties}
blob = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

page = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Слабые связи</title><style>
body{margin:0;background:#0d0d0d;color:#fff;font-family:system-ui,-apple-system,'Segoe UI',sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:34px 18px 60px}
h1{font-size:40px;margin:0 0 8px;letter-spacing:-.01em}
h2{font-size:22px;margin:40px 0 6px}
.eyebrow{font-size:13px;color:#8fd14f;text-transform:uppercase;letter-spacing:.22em;margin:0 0 10px}
.big{font-size:16px;line-height:1.55;color:#c3c2b7;max-width:76ch;margin:0 0 8px}
.note{font-size:13px;color:#898781;line-height:1.5;max-width:82ch;margin:6px 0 0}
svg{width:100%;height:auto;display:block}
.tiles{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0 6px}
.tile{background:#141413;border:1px solid #292826;border-radius:14px;padding:13px 18px;min-width:170px;flex:1}
.tile .v{font-size:28px;font-weight:700}
.tile .l{font-size:12.5px;color:#898781;margin-top:3px;line-height:1.4}
#tip{position:fixed;pointer-events:none;display:none;z-index:9;background:rgba(20,20,19,.97);
 border:1px solid #383835;border-radius:10px;padding:9px 12px;font-size:13px;line-height:1.5;max-width:260px}
.rev{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
.card{background:#141413;border:1px solid #2c3a24;border-radius:14px;padding:13px 16px;min-width:210px;flex:1;max-width:280px}
.card b{font-size:15px}
.card .m{font-size:12.5px;color:#898781;margin-top:5px;line-height:1.5}
.empty{color:#898781;font-size:14px;margin-top:14px}
.foot{color:#52514e;font-size:12px;line-height:1.6;margin-top:34px;max-width:92ch}
</style></head><body><div class="wrap">
<p class="eyebrow">chat river · слабые связи</p>
<h1>Слабые связи: долгожители на орбите</h1>
<p class="big">Люди, чьи русла слишком тонкие, чтобы разглядеть их в большой реке, —
но они не пересыхают годами: исчезают и возвращаются эпизодами. По Грановеттеру
(«Сила слабых связей», 1973) именно такие контакты приносят новое — они живут в других
кругах. Бусина = активный месяц, размер = объём; клик по имени откроет профиль
в Telegram.</p>
<div class="tiles" id="tiles"></div>
<svg id="beads"></svg>
<div class="empty" id="empty" style="display:none">По текущим порогам слабых связей не
нашлось — это нормально для коротких или молодых архивов: главный критерий (жизнь
дуги ≥ 2 лет) просто ещё не успел накопиться.</div>
<h2>Кандидаты на возрождение</h2>
<p class="note">Связи, прожившие годами и молчащие больше года. Страница ничего
не советует — она показывает, где пунктир оборвался.</p>
<div class="rev" id="rev"></div>
<p class="foot">Пороги: личные чаты, дуга жизни ≥ 24 мес, ≥ 3 эпизода активности
(паузы ≥ 4 мес), ≤ 40 сообщений на активный месяц, всего ≤ 1500, у каждой стороны
≥ 10 сообщений; «затухла» = тишина ≥ 12 мес от конца корпуса. Рамка — Granovetter,
The Strength of Weak Ties (AJS, 1973). Цвет бусин — средний тон твоих сообщений месяца
по LLM-разметке шага 5 (если делал; иначе бусины серые). Страница локальная и личная —
делись осознанно.</p>
</div>
<div id="tip"></div>
<script type="application/json" id="data">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const N = D.months.length, T = D.ties;
function tempColor(t){
  const cold=[77,157,255], warm=[255,176,77], mid=[107,106,102];
  const a = t<0?cold:warm, f=Math.min(1,Math.abs(t)/1.5);
  const c = a.map((x,j)=>Math.round(mid[j]+(x-mid[j])*f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
(function(){
  const liv = T.filter(t=>t.silent<12).length;
  const years = Math.round(T.reduce((s,t)=>s+t.span,0)/12);
  document.getElementById('tiles').innerHTML=`
   <div class="tile"><div class="v">${T.length}</div><div class="l">слабых связей по критериям</div></div>
   <div class="tile"><div class="v" style="color:#8fd14f">${liv}</div><div class="l">живых (активность за последний год)</div></div>
   <div class="tile"><div class="v" style="color:#4d9dff">${T.length-liv}</div><div class="l">затухших — кандидаты на возрождение</div></div>
   <div class="tile"><div class="v">${years}</div><div class="l">суммарных лет жизни этих пунктиров</div></div>`;
})();
(function(){
  if(!T.length){document.getElementById('empty').style.display='block';
    document.getElementById('beads').style.display='none';return;}
  const padL=150, padT=34, padR=14, rowH=30;
  const W=1140, H=padT+rowH*T.length+30;
  const X=i=>padL+i*(W-padL-padR)/Math.max(1,N-1);
  let s='';
  const y0=+D.months[0].slice(0,4), y1=+D.months[N-1].slice(0,4);
  for(let y=y0;y<=y1;y++){
    const i=D.months.indexOf(y+'-01'); if(i<0)continue;
    s+=`<line x1="${X(i)}" y1="${padT-6}" x2="${X(i)}" y2="${H-24}" stroke="#1d1c1b"/>`;
    s+=`<text x="${X(i)}" y="${H-8}" fill="#6b6a66" font-size="11" text-anchor="middle">${y}</text>`;
  }
  T.forEach((t,r)=>{
    const y=padT+rowH*r+rowH/2;
    const dead=t.silent>=12;
    s+=`<a href="tg://user?id=${t.uid}"><text x="${padL-10}" y="${y+4}" fill="${dead?'#6b6a66':'#e8e6df'}" font-size="12.5" text-anchor="end" style="cursor:pointer" text-decoration="underline dotted">${t.name.slice(0,20)}</text></a>`;
    const ms=Object.keys(t.months).map(Number).sort((a,b)=>a-b);
    s+=`<line x1="${X(ms[0])}" y1="${y}" x2="${X(ms[ms.length-1])}" y2="${y}" stroke="#1d1c1b" stroke-width="1"/>`;
    ms.forEach(i=>{
      const [a,b]=t.months[i], tot=a+b;
      const rr=Math.max(2.4,Math.min(9,1.8*Math.sqrt(tot)));
      const tn=t.tone[i];
      const col=(tn===undefined)?'#4a4a47':tempColor(tn);
      s+=`<circle cx="${X(i)}" cy="${y}" r="${rr.toFixed(1)}" fill="${col}" opacity=".88" data-i="${i}" data-r="${r}" data-a="${a}" data-b="${b}" data-t="${tn===undefined?'':tn}"/>`;
    });
    if(dead){
      const lastX=X(ms[ms.length-1]);
      s+=`<text x="${Math.min(lastX+12,W-130)}" y="${y+4}" fill="#4d9dff" font-size="10.5">молчит ${Math.floor(t.silent/12)>0?Math.floor(t.silent/12)+' г ':''}${t.silent%12} мес</text>`;
    }
  });
  const svg=document.getElementById('beads');
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  svg.innerHTML=s;
  const tip=document.getElementById('tip');
  svg.addEventListener('mousemove',ev=>{
    const c=ev.target;
    if(c.tagName!=='circle'){tip.style.display='none';return;}
    tip.style.display='block';
    tip.style.left=Math.min(window.innerWidth-270,ev.clientX+14)+'px';
    tip.style.top=(ev.clientY+14)+'px';
    const tn=c.dataset.t, t=T[+c.dataset.r];
    tip.innerHTML=`<b>${t.name}</b> · ${D.months[+c.dataset.i]}<br>я: ${c.dataset.a} · собеседник: ${c.dataset.b}`+
      (tn!==''?`<br>мой тон: <b style="color:${tempColor(+tn)}">${+tn>0?'+':''}${tn}</b>`:'');
  });
  svg.addEventListener('mouseleave',()=>{tip.style.display='none';});
})();
(function(){
  const dead=T.filter(t=>t.silent>=12).sort((a,b)=>b.span-a.span);
  document.getElementById('rev').innerHTML=dead.length?dead.map(t=>`
   <div class="card"><b><a href="tg://user?id=${t.uid}" style="color:#e8e6df">${t.name}</a></b>
    <div class="m">прожила ${Math.round(t.span/12*10)/10} лет · ${t.episodes} эпизодов ·
    ${t.total} сообщений<br>последний контакт: ${t.last} —
    молчит ${Math.floor(t.silent/12)>0?Math.floor(t.silent/12)+' г ':''}${t.silent%12} мес<br>
    <a href="tg://user?id=${t.uid}" style="color:#8fd14f">открыть в Telegram →</a></div></div>`).join('')
   :'<div class="empty">Все найденные слабые связи живы — возрождать нечего.</div>';
})();
</script></body></html>"""

OUT.mkdir(exist_ok=True)
(OUT / 'weak-ties.html').write_text(page.replace('__DATA__', blob), encoding='utf-8')
print(f"готово: out/weak-ties.html ({len(ties)} связей)")
