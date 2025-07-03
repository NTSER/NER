from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from transformers import pipeline
import re

app = FastAPI()
ner = pipeline(
    "ner", model="Davlan/xlm-roberta-base-ner-hrl", aggregation_strategy="simple"
)
templates = Jinja2Templates(directory="templates")


def build_highlight_spans(text, entities, label):
    spans = []
    for ent in entities:
        start = text.find(ent)
        if start != -1:
            spans.append({"start": start, "end": start + len(ent), "label": label})
    return spans


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "highlighted_text": "", "text": ""},
    )


@app.post("/", response_class=HTMLResponse)
async def analyze(request: Request, text: str = Form(...)):
    spans = []

    ner_results = ner(text)
    persons = [ent["word"] for ent in ner_results if ent["entity_group"] == "PER"]
    spans += build_highlight_spans(text, persons, "person")

    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    spans += build_highlight_spans(text, emails, "email")

    phones = re.findall(r"\+?\d[\d\s\-()]{7,}", text)
    spans += build_highlight_spans(text, phones, "phone")

    addresses = re.findall(
        r"\d{1,5}\s\w+\s\w+|\b(street|road|ave|avenue|boulevard|rd|blvd)\b",
        text,
        flags=re.I,
    )
    flattened_addresses = [a[0] if isinstance(a, tuple) else a for a in addresses]
    spans += build_highlight_spans(text, flattened_addresses, "address")

    ids = re.findall(r"(order|customer|serial)[\s:#\-]*\w+", text, flags=re.I)
    spans += build_highlight_spans(text, ids, "id")

    credentials = re.findall(r"(username|password|login)[\s:=\-]*\w+", text, flags=re.I)
    spans += build_highlight_spans(text, credentials, "credentials")

    warranties = re.findall(
        r"(warranty|ticket|reference)[\s:#\-]*\w+", text, flags=re.I
    )
    spans += build_highlight_spans(text, warranties, "warranty")

    # Sort and merge highlights (non-overlapping)
    spans = sorted(spans, key=lambda x: x["start"])
    highlighted_text = ""
    last = 0
    for span in spans:
        if span["start"] >= last:
            highlighted_text += text[last : span["start"]]
            highlighted_text += f'<span class="{span["label"]}">{text[span["start"] : span["end"]]}</span>'
            last = span["end"]
    highlighted_text += text[last:]

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "highlighted_text": highlighted_text, "text": text},
    )
