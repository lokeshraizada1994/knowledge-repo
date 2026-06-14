import base64
import io
import pdfplumber


def extract_pdf(data_b64: str, filename: str) -> dict:
    pdf_bytes = base64.b64decode(data_b64)

    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

    content = "\n\n".join(text_parts)
    title = filename.replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title()
    word_count = len(content.split())
    read_time = max(1, round(word_count / 200))

    return {
        "type": "pdf",
        "title": title,
        "author": None,
        "content": content,
        "source_url": None,
        "duration": f"~{read_time} min read",
    }
