# authors.py

from typing import Dict, List


AUTHORS: Dict[str, Dict[str, str]] = {
    # ===== ЗОЛОТОЙ ВЕК =====
    "pushkin": {
        "name": "Александр Пушкин",
        "group": "Золотой век",
    },
    "lermontov": {
        "name": "Михаил Лермонтов",
        "group": "Золотой век",
    },
    "gogol": {
        "name": "Николай Гоголь",
        "group": "Золотой век",
    },
    "turgenev": {
        "name": "Иван Тургенев",
        "group": "Золотой век",
    },
    "goncharov": {
        "name": "Иван Гончаров",
        "group": "Золотой век",
    },
    "ostrovsky": {
        "name": "Александр Островский",
        "group": "Золотой век",
    },

    # ===== СЕРЕБРЯНЫЙ ВЕК =====
    "blokk": {
        "name": "Александр Блок",
        "group": "Серебряный век",
    },
    "akhmatova": {
        "name": "Анна Ахматова",
        "group": "Серебряный век",
    },
    "esenin": {
        "name": "Сергей Есенин",
        "group": "Серебряный век",
    },
    "mayakovsky": {
        "name": "Владимир Маяковский",
        "group": "Серебряный век",
    },
    "tsvetaeva": {
        "name": "Марина Цветаева",
        "group": "Серебряный век",
    },
    "mandelstam": {
        "name": "Осип Мандельштам",
        "group": "Серебряный век",
    },

    # ===== XIX–XX ВЕК =====
    "dostoevsky": {
        "name": "Фёдор Достоевский",
        "group": "XIX–XX век",
    },
    "tolstoy": {
        "name": "Лев Толстой",
        "group": "XIX–XX век",
    },
    "chekhov": {
        "name": "Антон Чехов",
        "group": "XIX–XX век",
    },
    "bunina": {
        "name": "Иван Бунин",
        "group": "XIX–XX век",
    },
    "gorky": {
        "name": "Максим Горький",
        "group": "XIX–XX век",
    },

    # ===== СОВРЕМЕННЫЕ =====
    "bulgakov": {
        "name": "Михаил Булгаков",
        "group": "Современные",
    },
    "nabokov": {
        "name": "Владимир Набоков",
        "group": "Современные",
    },
    "pasternak": {
        "name": "Борис Пастернак",
        "group": "Современные",
    },
    "solzhenitsyn": {
        "name": "Александр Солженицын",
        "group": "Современные",
    },
    "filatov": {
        "name": "Леонид Филатов",
        "group": "Современные",
    },
}


# =========================
# ФУНКЦИИ ДЛЯ КНОПОК
# =========================

def get_groups() -> List[str]:
    """Вернуть список групп (эпох), отсортированных красиво"""
    groups = {a["group"] for a in AUTHORS.values()}
    order = ["Золотой век", "Серебряный век", "XIX–XX век", "Современные"]
    return [g for g in order if g in groups]


def get_authors_by_group(group: str) -> Dict[str, str]:
    """Вернуть авторов конкретной группы: key -> name"""
    result = {
        key: data["name"]
        for key, data in AUTHORS.items()
        if data["group"] == group
    }
    return dict(sorted(result.items(), key=lambda x: x[1]))
