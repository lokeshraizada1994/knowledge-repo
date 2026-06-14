import os
import json
import anthropic
from datetime import datetime

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a knowledge extraction expert. You receive raw content from articles, YouTube videos, podcasts, case studies, and consulting reports.

Your job is to produce a structured knowledge card in valid JSON format.

RULES:
- Never leave a field blank. Either fill it with real content OR set it to "N/A — [one-line reason why it does not apply]"
- For Top 5 Takeaways: always produce exactly 5. If the source has fewer strong points, synthesise/infer the remaining ones from context and mark them [inferred]
- For Critique: always give YOUR honest assessment — what's strong, what's weak, what's missing
- For visuals: set "needs_visual" to true only if the field contains data, comparisons, processes, or frameworks that would genuinely benefit from a chart/diagram/table
- Be specific and insightful — not generic summaries

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
    "content": "3-5 sentence TL;DR of what this is and why it matters",
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

    # Truncate very long content to fit context window (~100k chars max)
    if len(raw_content) > 80000:
        raw_content = raw_content[:80000] + "\n\n[Content truncated for processing]"

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
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw_json = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1]
        raw_json = raw_json.rsplit("```", 1)[0]

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
