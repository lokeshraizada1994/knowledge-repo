import os
import json
import anthropic
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a master synthesizer. You receive raw content from articles, YouTube videos, podcasts, case studies, and consulting reports.

Your job: extract the MAXIMUM value in the FEWEST words. Someone should be able to read your output in under 90 seconds and walk away with everything worth remembering. No filler, no restating the obvious, no academic throat-clearing.

STRICT RULES:
1. NEVER infer, hallucinate, or use prior knowledge. Every word must be grounded in the source content provided.
2. Be ruthless about signal over noise — if the source has 10 pages, distill it to what actually matters. Prefer sharp, specific, quotable phrasing over vague summary language.
3. If something genuinely does not exist in the source (e.g. no real-world example given), set that field's "present" to false with a one-line reason. Do NOT pad or invent to fill a template.
4. "the_catch" is the one place for your own honest judgment — a limitation, blind spot, or reason to be skeptical.
5. FLEXIBLE STRUCTURE — this is important: beyond the core fields below, if the source contains something genuinely notable that doesn't fit the standard fields (a striking statistic, a contrarian take, a useful framework/model, a checklist, a quote worth remembering, a prediction, a comparison table, numbers/data worth highlighting), add it as an entry in "extra_sections". Only add a section if it's genuinely additive — do not force one into existence. Zero, one, or several extra_sections is fine. Each source is different; let the structure follow the content, not the other way around.
6. Tags: 3-6 short, specific tags (not generic like "business" or "technology" alone).

OUTPUT FORMAT (strict JSON, no markdown fences around it):
{
  "metadata": {
    "title": "string",
    "source_type": "article|youtube|podcast|case_study|report|text",
    "source_url": "string or null",
    "author": "string or null",
    "date_processed": "string",
    "estimated_duration": "string or null",
    "tags": ["tag1", "tag2", "tag3"]
  },
  "tldr": ["One crisp sentence — what this is", "One crisp sentence — the core claim or finding", "One crisp sentence — why it matters / who should care"],
  "top_insights": [
    {"insight": "Sharp, specific, one-sentence insight", "why_it_matters": "One short phrase — the payoff of knowing this"},
    {"insight": "...", "why_it_matters": "..."},
    {"insight": "...", "why_it_matters": "..."}
  ],
  "best_example": {
    "present": true,
    "title": "Short label for the example/case/story (e.g. company name or scenario)",
    "story": "2-4 sentences telling the single most memorable, concrete example/case/story/data-point from the source — something worth referencing later.",
    "reason_absent": null
  },
  "do_this": {
    "present": true,
    "actions": ["Specific, concrete action 1", "Specific, concrete action 2"],
    "reason_absent": null
  },
  "the_catch": "One sharp sentence: the key limitation, risk, or reason to be skeptical of this source's claims — your honest take.",
  "flashcards": [
    {"question": "A specific, testable question about a fact/number/claim from the source", "answer": "The precise answer, short"},
    {"question": "...", "answer": "..."},
    {"question": "...", "answer": "..."}
  ],
  "extra_sections": [
    {
      "emoji": "📊",
      "title": "Short section title (e.g. 'By The Numbers', 'Contrarian Take', 'The Framework')",
      "type": "bullets|quote|stat",
      "content": ["item 1", "item 2"]
    }
  ]
}

If best_example.present is false, set story to null and give reason_absent (e.g. "Source is purely theoretical with no case studies or examples").
If do_this.present is false, set actions to [] and give reason_absent (e.g. "Source is informational/reflective with no actionable steps").
extra_sections can be an empty array [] if nothing extra is genuinely worth adding — do not force it.
flashcards: exactly 3 question/answer pairs testing recall of the most important specific facts, numbers, or claims — designed for spaced repetition, so keep answers short and precise (a number, a name, a one-line definition)."""


def process_content(content: dict) -> dict:
    source_type = content.get("type", "text")
    title = content.get("title", "Untitled")
    raw_content = content.get("content", "")
    source_url = content.get("source_url")
    author = content.get("author")
    duration = content.get("duration")

    # Truncate content to avoid Claude's response being cut off.
    if len(raw_content) > 20000:
        raw_content = (
            raw_content[:15000]
            + "\n\n[... middle section truncated ...]\n\n"
            + raw_content[-5000:]
        )

    user_message = f"""SOURCE TYPE: {source_type}
TITLE: {title}
AUTHOR: {author or "Unknown"}
URL: {source_url or "N/A"}
DURATION: {duration or "Unknown"}

CONTENT:
{raw_content}

Distill this into the crisp, high-signal knowledge card described in the system prompt."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw_json = response.content[0].text.strip()

    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1]
        raw_json = raw_json.rsplit("```", 1)[0]

    if response.stop_reason == "max_tokens":
        raise ValueError(
            "Claude response was truncated — content may be too long. "
            f"stop_reason={response.stop_reason}"
        )

    knowledge_card = json.loads(raw_json)

    knowledge_card["metadata"]["date_processed"] = datetime.utcnow().strftime("%Y-%m-%d")
    if not knowledge_card["metadata"].get("source_url"):
        knowledge_card["metadata"]["source_url"] = source_url
    if not knowledge_card["metadata"].get("author"):
        knowledge_card["metadata"]["author"] = author
    if not knowledge_card["metadata"].get("estimated_duration"):
        knowledge_card["metadata"]["estimated_duration"] = duration

    return knowledge_card
