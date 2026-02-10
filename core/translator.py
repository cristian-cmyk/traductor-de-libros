"""Translate text chunks using Claude API with parallel async calls."""
import asyncio
from dataclasses import dataclass
from typing import Callable, Optional

import anthropic


TRANSLATION_PROMPT = """You are a professional book translator. Translate the following text from {source_lang} to {target_lang}.

Rules:
- Maintain the author's tone, style, and voice
- Use neutral, standard {target_lang} (avoid regional slang)
- Preserve all formatting: paragraph breaks, numbered lists, bold markers (**text**), section headers
- Keep proper nouns, brand names, and technical terms as-is when appropriate
- Ensure all diacritical marks are correct (accents, tildes, umlauts, etc.)
- Do NOT add any commentary, notes, or explanations — output ONLY the translation
- If the text contains chapter headers, preserve them with their numbering

Text to translate:

{text}"""


@dataclass
class TranslationResult:
    chunk_index: int
    original_text: str
    translated_text: str
    success: bool = True
    error: str = ""


class Translator:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_concurrent: int = 8,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.model = model
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries

    async def translate_chunks(
        self,
        chunks: list,
        source_lang: str,
        target_lang: str,
        on_progress: Optional[Callable] = None,
    ) -> list[TranslationResult]:
        """Translate all chunks in parallel with concurrency control.

        Args:
            chunks: list of Chunk objects from chunker
            source_lang: source language name (e.g., "English")
            target_lang: target language name (e.g., "Spanish")
            on_progress: callback(completed, total, chunk_index) for progress updates

        Returns:
            List of TranslationResult in same order as input chunks.
        """
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = [None] * len(chunks)
        completed = 0

        async def translate_one(chunk):
            nonlocal completed
            async with semaphore:
                result = await self._translate_single(
                    client, chunk, source_lang, target_lang
                )
                results[chunk.index] = result
                completed += 1
                if on_progress:
                    on_progress(completed, len(chunks), chunk.index)

        tasks = [translate_one(chunk) for chunk in chunks]
        await asyncio.gather(*tasks)

        return results

    async def _translate_single(
        self,
        client: anthropic.AsyncAnthropic,
        chunk,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate a single chunk with retry logic."""
        prompt = TRANSLATION_PROMPT.format(
            source_lang=source_lang,
            target_lang=target_lang,
            text=chunk.text,
        )

        for attempt in range(self.max_retries + 1):
            try:
                message = await client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    messages=[{"role": "user", "content": prompt}],
                )
                translated = message.content[0].text
                return TranslationResult(
                    chunk_index=chunk.index,
                    original_text=chunk.text,
                    translated_text=translated,
                )
            except anthropic.RateLimitError:
                if attempt < self.max_retries:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                return TranslationResult(
                    chunk_index=chunk.index,
                    original_text=chunk.text,
                    translated_text="",
                    success=False,
                    error="Rate limited after retries",
                )
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(2)
                    continue
                return TranslationResult(
                    chunk_index=chunk.index,
                    original_text=chunk.text,
                    translated_text="",
                    success=False,
                    error=str(e),
                )


def translate_sync(
    chunks: list,
    source_lang: str,
    target_lang: str,
    api_key: str,
    model: str = "claude-sonnet-4-5-20250929",
    max_concurrent: int = 8,
    on_progress: Optional[Callable] = None,
) -> list[TranslationResult]:
    """Synchronous wrapper for async translation. Use this from Streamlit."""
    translator = Translator(
        api_key=api_key,
        model=model,
        max_concurrent=max_concurrent,
    )
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            translator.translate_chunks(chunks, source_lang, target_lang, on_progress)
        )
    finally:
        loop.close()
    return results
