def bold(text: str) -> str:
    """Делает текст жирным"""
    return f"<b>{text}</b>"

def italic(text: str) -> str:
    """Делает текст курсивом"""
    return f"<i>{text}</i>"

def code(text: str) -> str:
    """Форматирует как код"""
    return f"<code>{text}</code>"

def create_header(title: str, emoji: str = "") -> str:
    """Создает красивый заголовок"""
    if emoji:
        title = f"{emoji} {title}"
    border = "═" * 40
    return f"\n{border}\n{title}\n{border}\n"

def format_list(items: list, emoji: str = "•") -> str:
    """Форматирует список с эмодзи"""
    formatted = ""
    for item in items:
        formatted += f"{emoji} {item}\n"
    return formatted
