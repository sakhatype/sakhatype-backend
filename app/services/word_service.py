from typing import List

from app.db.postgres import get_pool
from app.services.word_difficulty import pick_words_for_game_difficulty


async def get_words(language: str = "sakha", count: int = 50, difficulty: str = "normal") -> List[str]:
    """Fetch words from PostgreSQL and apply the game difficulty picker."""
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT word
        FROM words
        WHERE NULLIF(BTRIM(word), '') IS NOT NULL
        ORDER BY id
        """
    )
    source_words = [row["word"] for row in rows]
    selected_difficulty = difficulty if language == "sakha" else "normal"
    return pick_words_for_game_difficulty(source_words, selected_difficulty, count)
