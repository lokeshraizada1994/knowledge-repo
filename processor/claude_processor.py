import os
import json
import anthropic
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a knowledge extraction expert. You receive raw content from articles, YouTube videos, podcasts, case studies, and consulting reports.

Your job is to produce a structured knowledge card in valid JSON format.

STRICT RULES — READ CAREFULLY:
1. NEVER infer, hallucinate, or use prior knowledge to fill fields. Every field must be grounded ONLY in what is explicitly present in the source content provided.
2. For contextual fields (thinking_framework, examples_and_stories, limitations_and_challenges, best_practices, use_cases, whats_ahead, knowledge_insights): if the source does not explicitly discuss this topic, set content to "N/A — [specific reason, e.g. 'motivational content with no frameworks presented']". Do NOT infer or fabricate.
3. For Top 5 Takeaways: extract from actual source content only. If source has fewer than 5 clear points, produce only what exists and pad remaining with "N/A — insufficient content in source" rather than inferring.
4. For Critique: give YOUR honest assessment of the source quality and usefulness — this is the ONE field where your own judgment is welcome.
5. Executive Summary: write as 3-5 crisp bullet points covering WHAT was discussed, KEY argument/finding, and WHY it matters. No paragraph prose.
6. Never leave any field blank — either real extracted content or "N/A — [reason]".
7. Be specific — quote or closely paraphrase the source. Avoid generic filler sentences.

OUTPUT FORMAT (strict JSON, no markdown around it):
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
  "executive_summary": {
    "content": ["Bullet 1 — what this source is about", "Bullet 2 — core argument or finding", "Bullet 3 — why it matters or who it's for", "Bullet 4 — optional key context", "Bullet 5 — optional standout insight"],
    "needs_visual": false
  },
  "top_5_takeaways": {
    "content": [
      {"point": "Takeaway 1", "inferred": false},
      {"point": "Takeaway 2", "inferred": false},
      {"point": "Takeaway 3", "inferred": false},
      {"point": "Takeaway 4", "inferred": false},
      {"point": "Takeaway 5", "inferred": false}
    ],
    "needs_visual": false
  },
  "actionables": {
    "content": ["Action 1", "Action 2", "Action 3"],
    "needs_visual": false
  },
  "critique": {
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "missing": ["what's missing 1"],
    "needs_visual": false
  },
  "thinking_framework": {
    "content": "string or N/A — reason",
    "framework_name": "string or null",
    "needs_visual": true
  },
  "knowledge_insights": {
    "content": "string or N/A — reason",
    "needs_visual": false
  },
  "examples_and_stories": {
    "content": ["example 1", "example 2"] or "N/A — reason",
    "needs_visual": false
  },
  "limitations_and_challenges": {
    "content": ["limitation 1", "limitation 2"] or "N/A — reason",
    "needs_visual": false
  },
  "best_practices": {
    "content": ["practice 1", "practice 2"] or "N/A — reason",
    "needs_visual": false
  },
  "use_cases": {
    "content": ["use case 1", "use case 2"] or "N/A — reason",
    "needs_visual": false
  },
  "whats_ahead": {
    "content": "string or N/A — reason",
    "needs_visual": false
  }
}"""


def process_content(content: dict) -> dict:
    source_type = content.get("type", "text")
    title = content.get("title", "Untitled")
    raw_content = content.get("content", "")
    source_url = content.get("source_url")
    author = content.get("author")
    duration = content.get("duration")

    # Truncate content to avoid Claude's response being cut off.
    # 20k chars of input leaves plenty of room for the JSON output.
    if len(raw_content) > 20000:
        # Keep first 15k (intro/body) + last 5k (conclusions) for reports
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

Extract the full knowledge card from this content following all rules."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw_json = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1]
        raw_json = raw_json.rsplit("```", 1)[0]

    # Guard against truncated JSON (stop_reason == max_tokens)
    stop_reason = response.stop_reason
    if stop_reason == "max_tokens":
        raise ValueError(
            "Claude response was truncated — content may be too long. "
            f"stop_reason={stop_reason}"
        )

    knowledge_card = json.loads(raw_json)

    # Ensure metadata fields are set
    knowledge_card["metadata"]["date_processed"] = datetime.utcnow().strftime("%Y-%m-%d")
    if not knowledge_card["metadata"].get("source_url"):
        knowledge_card["metadata"]["source_url"] = source_url
    if not knowledge_card["metadata"].get("author"):
        knowledge_card["metadata"]["author"] = author
    if not knowledge_card["metadata"].get("estimated_duration"):
        knowledge_card["metadata"]["estimated_duration"] = duration

    return knowledge_card
