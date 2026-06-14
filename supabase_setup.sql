create table if not exists knowledge_entries (
  id                  uuid primary key default gen_random_uuid(),
  title               text not null,
  source_type         text,
  source_url          text,
  author              text,
  date_processed      date,
  tags                text[],
  duration            text,
  github_url          text,
  notion_url          text,
  executive_summary   text,
  top_takeaways       text,
  actionables         text,
  thinking_framework  text,
  whats_ahead         text,
  full_card_json      jsonb,
  created_at          timestamptz default now()
);

-- Full text search index
create index if not exists knowledge_entries_fts
on knowledge_entries
using gin(to_tsvector('english',
  coalesce(title,'') || ' ' ||
  coalesce(executive_summary,'') || ' ' ||
  coalesce(top_takeaways,'') || ' ' ||
  coalesce(actionables,'')
));
