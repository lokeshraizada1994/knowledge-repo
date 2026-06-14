"""
Run this once to connect the integration and create the database.
Usage: python fix_notion.py
"""
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

token = os.getenv("NOTION_TOKEN")
page_id = os.getenv("NOTION_PAGE_ID", "").replace("-", "")

print(f"Token starts with: {token[:12]}...")
print(f"Page ID: {page_id}")

notion = Client(auth=token)

# Try to retrieve the page first
try:
    page = notion.pages.retrieve(page_id)
    print(f"✓ Page found: {page['id']}")
except Exception as e:
    print(f"✗ Cannot access page: {e}")
    print("\nThe integration cannot see this page.")
    print("This means the integration is not connected to the page.")
    print("\nTry this: go to notion.so/my-integrations and check if the")
    print("integration is installed in the correct workspace.")
    exit(1)

# Create database inside the page
try:
    db = notion.databases.create(
        parent={"type": "page_id", "page_id": page_id},
        title=[{"type": "text", "text": {"content": "Knowledge Repository"}}],
        properties={
            "Title":          {"title": {}},
            "Source Type":    {"select": {"options": [
                {"name": "Article",    "color": "blue"},
                {"name": "YouTube",    "color": "red"},
                {"name": "Podcast",    "color": "purple"},
                {"name": "Case Study", "color": "green"},
                {"name": "Report",     "color": "yellow"},
                {"name": "Text",       "color": "gray"},
            ]}},
            "Author":         {"rich_text": {}},
            "Date Processed": {"date": {}},
            "Tags":           {"multi_select": {}},
            "Source URL":     {"url": {}},
            "Duration":       {"rich_text": {}},
            "GitHub URL":     {"url": {}},
        }
    )
    print(f"✓ Database created: {db['id']}")
    print(f"\nAdd this to your Railway variables:")
    print(f"NOTION_DATABASE_ID={db['id'].replace('-','')}")
except Exception as e:
    print(f"✗ Could not create database: {e}")
