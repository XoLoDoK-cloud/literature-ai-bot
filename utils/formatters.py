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

def create_progress_bar(value: int, max_value: int, length: int = 10) -> str:
    """Создает прогресс-бар"""
    percentage = min(value / max_value * 100, 100)
    filled = int(percentage / 100 * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {percentage:.1f}%"

def format_list(items: list, emoji: str = "•") -> str:
    """Форматирует список с эмодзи"""
    formatted = ""
    for item in items:
        formatted += f"{emoji} {item}\n"
    return formatted

def create_card(title: str, content: str, border_char: str = "─") -> str:
    """Создает карточку с рамкой"""
    border = border_char * 40
    return f"{border}\n🎴 {bold(title)}\n{content}\n{border}"
