# knowledge_base.py
"""
База знаний о русских писателях + RAG-утилиты для SQLite FTS5.

Этот файл содержит:
- WRITERS_KNOWLEDGE (твоя база знаний, без изменений)
- build_knowledge_chunks(): преобразует знания в чанки для FTS5
- knowledge_hash(): хэш базы знаний для авто-переиндексации
- format_facts_for_user(): красиво выводит факты пользователю (fallback)
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

WRITERS_KNOWLEDGE = {
    "pushkin": {
        "full_name": "Александр Сергеевич Пушкин",
        "birth": {
            "date": "26 мая (6 июня) 1799",
            "place": "Москва, Немецкая улица",
            "family": "Сергей Львович Пушкин (отец), Надежда Осиповна Ганнибал (мать)"
        },
        "death": {
            "date": "29 января (10 февраля) 1837",
            "place": "Санкт-Петербург, набережная реки Мойки, 12",
            "cause": "Смертельное ранение на дуэли с Жоржем Дантесом"
        },
        "education": {
            "lyceum": "Царскосельский лицей (1811-1817)",
            "graduation": "Выпустился в чине коллежского секретаря"
        },
        "life_events": [
            "Участник литературного общества 'Арзамас'",
            "Ссылка в Южную Россию (1820-1824): Екатеринослав, Кишинёв, Одесса",
            "Ссылка в Михайловское (1824-1826)",
            "Женился на Наталье Гончаровой (1831)",
            "Открыл журнал 'Современник' (1836)"
        ],
        "major_works": [
            "Роман в стихах 'Евгений Онегин'",
            "Повесть 'Капитанская дочка'",
            "Трагедия 'Борис Годунов'",
            "Поэма 'Руслан и Людмила'",
            "Цикл 'Повести Белкина'"
        ],
        "interesting_facts": [
            "Знал несколько языков, включая французский (родной в детстве)",
            "Создал современный русский литературный язык",
            "Написал более 800 стихотворений",
            "Его произведения переведены более чем на 100 языков"
        ]
    },
    "dostoevsky": {
        "full_name": "Фёдор Михайлович Достоевский",
        "birth": {
            "date": "30 октября (11 ноября) 1821",
            "place": "Москва",
            "family": "Михаил Андреевич Достоевский (отец-врач), Мария Фёдоровна (мать)"
        },
        "death": {
            "date": "28 января (9 февраля) 1881",
            "place": "Санкт-Петербург",
            "cause": "Эмфизема лёгких, осложнения"
        },
        "education": {
            "school": "Николаевское инженерное училище (1838-1843)",
            "profession": "Военный инженер"
        },
        "life_events": [
            "Участие в кружке Петрашевского (1849)",
            "Арест и приговор к расстрелу (помилован в последний момент)",
            "Каторга в Омске (1850-1854)",
            "Служба солдатом в Семипалатинске (1854-1859)",
            "Игровая зависимость (рулетка)",
            "Женился на Анне Сниткиной (1867)"
        ],
        "major_works": [
            "Роман 'Преступление и наказание'",
            "Роман 'Идиот'",
            "Роман 'Братья Карамазовы'",
            "Роман 'Бесы'",
            "Повесть 'Записки из подполья'"
        ],
        "philosophy": [
            "Исследовал глубины человеческой психологии",
            "Темы: вера, сомнение, мораль, свобода выбора",
            "Концепция 'униженных и оскорблённых'",
            "Идея искупления через страдание"
        ],
        "interesting_facts": [
            "Страдал эпилепсией",
            "Написал 'Игрока' за 26 дней из-за долгов",
            "Читал Евангелие на каторге — единственная разрешённая книга",
            "Считается предтечей экзистенциализма"
        ]
    },
    "tolstoy": {
        "full_name": "Лев Николаевич Толстой",
        "birth": {
            "date": "28 августа (9 сентября) 1828",
            "place": "Ясная Поляна, Тульская губерния",
            "family": "Граф Николай Ильич Толстой (отец), Мария Николаевна (мать)"
        },
        "death": {
            "date": "7 (20) ноября 1910",
            "place": "Станция Астапово (ныне Лев Толстой), Рязанская губерния",
            "cause": "Воспаление лёгких"
        },
        "education": {
            "university": "Казанский университет (1844-1847, не окончил)",
            "self_education": "Занимался самообразованием всю жизнь"
        },
        "life_events": [
            "Служба в армии на Кавказе (1851-1854)",
            "Участие в Крымской войне, оборона Севастополя",
            "Женился на Софье Берс (1862), 13 детей",
            "Открыл школу для крестьянских детей в Ясной Поляне",
            "Духовный кризис и религиозные поиски (1870-е)",
            "Отлучён от православной церкви (1901)",
            "Уход из дома в конце жизни (1910)"
        ],
        "major_works": [
            "Роман-эпопея 'Война и мир'",
            "Роман 'Анна Каренина'",
            "Повесть 'Смерть Ивана Ильича'",
            "Роман 'Воскресение'",
            "Цикл 'Севастопольские рассказы'"
        ],
        "philosophy": [
            "Ненасилие и непротивление злу",
            "Простая жизнь и отказ от богатства",
            "Любовь к ближнему как основа морали",
            "Критика государства и церкви",
            "Влияние на Ганди и движение ненасилия"
        ],
        "interesting_facts": [
            "Отказался от авторских прав на поздние произведения",
            "Вёл дневники всю жизнь (около 50 лет)",
            "Был вегетарианцем последние 25 лет",
            "Разработал собственную систему образования"
        ]
    },
    "gogol": {
        "full_name": "Николай Васильевич Гоголь",
        "birth": {
            "date": "20 марта (1 апреля) 1809",
            "place": "Великие Сорочинцы, Полтавская губерния",
            "family": "Василий Афанасьевич Гоголь-Яновский (отец), Мария Ивановна (мать)"
        },
        "death": {
            "date": "21 февраля (4 марта) 1852",
            "place": "Москва",
            "cause": "Истощение, осложнения после голодания"
        },
        "education": {
            "school": "Нежинская гимназия высших наук (1821-1828)"
        },
        "life_events": [
            "Переезд в Петербург (1828)",
            "Первая неудача с поэмой 'Ганц Кюхельгартен' (сжёг тираж)",
            "Успех 'Вечеров на хуторе близ Диканьки' (1831-1832)",
            "Работа учителем истории (1834-1835)",
            "Долгое проживание в Риме и Европе (1836-1848)",
            "Сжёг рукопись второго тома 'Мёртвых душ' (1852)"
        ],
        "major_works": [
            "Поэма 'Мёртвые души'",
            "Комедия 'Ревизор'",
            "Повесть 'Шинель'",
            "Сборник 'Вечера на хуторе близ Диканьки'",
            "Повесть 'Тарас Бульба'"
        ],
        "interesting_facts": [
            "Боялся быть похороненным заживо",
            "Был очень религиозным в последние годы",
            "Считал 'Мёртвые души' 'поэмой' по образцу 'Божественной комедии'",
            "Его творчество оказало огромное влияние на русскую литературу"
        ]
    },
    "chekhov": {
        "full_name": "Антон Павлович Чехов",
        "birth": {
            "date": "17 (29) января 1860",
            "place": "Таганрог",
            "family": "Павел Егорович Чехов (отец), Евгения Яковлевна (мать)"
        },
        "death": {
            "date": "2 (15) июля 1904",
            "place": "Баденвайлер, Германия",
            "cause": "Туберкулёз"
        },
        "education": {
            "university": "Московский университет, медицинский факультет (1879-1884)",
            "profession": "Врач"
        },
        "life_events": [
            "Работал врачом, лечил бедных бесплатно",
            "Путешествие на Сахалин (1890) — изучение каторги",
            "Переезд в Мелихово (1892-1899)",
            "Переезд в Ялту из-за болезни (1898)",
            "Женился на Ольге Книппер (1901)"
        ],
        "major_works": [
            "Пьеса 'Вишнёвый сад'",
            "Пьеса 'Чайка'",
            "Пьеса 'Три сестры'",
            "Рассказ 'Дама с собачкой'",
            "Рассказ 'Палата №6'"
        ],
        "writing_style": [
            "Краткость и лаконичность",
            "Подтекст и недосказанность",
            "Внимание к деталям быта",
            "Юмор и ирония",
            "Психологическая глубина"
        ],
        "interesting_facts": [
            "Написал более 600 рассказов",
            "Использовал псевдонимы (Антоша Чехонте)",
            "Сказал перед смертью: 'Ich sterbe' (Я умираю)",
            "Принцип: 'Краткость — сестра таланта'",
            "Вёл обширную переписку (сохранилось около 4000 писем)",
            "Считал медицину своей женой, а литературу — любовницей"
        ]
    }
}


def get_writer_knowledge(author_key: str) -> dict[str, Any]:
    return WRITERS_KNOWLEDGE.get(author_key, {})


def _flatten(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.extend(_flatten(v, key))
        return out
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            out.extend(_flatten(v, key))
        return out
    title = prefix or "info"
    return [(title, str(obj))]


def build_knowledge_chunks() -> list[dict]:
    chunks: list[dict] = []
    for author_key, data in WRITERS_KNOWLEDGE.items():
        if not isinstance(data, dict):
            continue

        full_name = data.get("full_name") or author_key
        card_lines = [f"Полное имя: {full_name}"]

        b = data.get("birth")
        if isinstance(b, dict):
            date = b.get("date", "")
            place = b.get("place", "")
            fam = b.get("family", "")
            if date or place:
                card_lines.append(f"Рождение: {date} — {place}".strip(" —"))
            if fam:
                card_lines.append(f"Семья: {fam}")

        d = data.get("death")
        if isinstance(d, dict):
            date = d.get("date", "")
            place = d.get("place", "")
            cause = d.get("cause", "")
            if date or place:
                card_lines.append(f"Смерть: {date} — {place}".strip(" —"))
            if cause:
                card_lines.append(f"Причина смерти: {cause}")

        chunks.append({
            "author_key": author_key,
            "title": "Краткая справка",
            "content": "\n".join([x for x in card_lines if x.strip()])
        })

        flat = _flatten(data)
        grouped: dict[str, list[str]] = {}
        for path, value in flat:
            top = path.split(".", 1)[0]
            grouped.setdefault(top, [])
            grouped[top].append(f"{path}: {value}")

        for top, lines in grouped.items():
            buf: list[str] = []
            size = 0
            for line in lines:
                buf.append(line)
                size += len(line)
                if size > 900:
                    chunks.append({"author_key": author_key, "title": top, "content": "\n".join(buf)})
                    buf, size = [], 0
            if buf:
                chunks.append({"author_key": author_key, "title": top, "content": "\n".join(buf)})

    return chunks


def knowledge_hash() -> str:
    raw = json.dumps(WRITERS_KNOWLEDGE, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def format_facts_for_user(results: list[dict], max_items: int = 6) -> str:
    if not results:
        return ""
    lines: list[str] = []
    for r in results[:max_items]:
        title = (r.get("title") or "Факт").strip()
        content = (r.get("content") or "").strip()
        if not content:
            continue
        content_lines = [ln for ln in content.splitlines() if ln.strip()][:6]
        if not content_lines:
            continue
        lines.append(f"• <b>{title}</b>\n" + "\n".join(content_lines))
    return "\n\n".join(lines).strip()


def normalize_query_for_fts(text: str) -> str:
    t = (text or "").strip().lower()
    tokens = re.findall(r"[0-9A-Za-zА-Яа-яЁё]+", t)
    if not tokens:
        return ""
    tokens = tokens[:8]
    return " AND ".join([tok + "*" for tok in tokens])
