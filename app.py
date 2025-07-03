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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "highlighted_text": "", "text": ""},
    )


def build_highlight_spans_from_offsets(entities, label):
    spans = []
    for ent in entities:
        spans.append({"start": ent["start"], "end": ent["end"], "label": label})
    return spans


@app.post("/", response_class=HTMLResponse)
async def analyze(request: Request, text: str = Form(...)):
    spans = []

    ner_results = ner(text)
    persons = [ent for ent in ner_results if ent["entity_group"] == "PER"]
    spans += build_highlight_spans_from_offsets(persons, "person")

    # Email
    emails = list(re.finditer(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text))
    spans += [{"start": m.start(), "end": m.end(), "label": "email"} for m in emails]

    # Phone
    phones = list(re.finditer(r"\+?\d[\d\s\-()]{7,}", text))
    spans += [{"start": m.start(), "end": m.end(), "label": "phone"} for m in phones]

    # Address
    addresses = list(
        re.finditer(
            r"\d{1,5}\s\w+\s\w+|\b(street|road|ave|avenue|boulevard|rd|blvd)\b",
            text,
            flags=re.I,
        )
    )
    spans += [
        {"start": m.start(), "end": m.end(), "label": "address"} for m in addresses
    ]

    # ID
    ids = list(re.finditer(r"(order|customer|serial)[\s:#\-]*\w+", text, flags=re.I))
    spans += [{"start": m.start(), "end": m.end(), "label": "id"} for m in ids]

    # Credentials
    credentials = list(
        re.finditer(r"(username|password|login)[\s:=\-]*\w+", text, flags=re.I)
    )
    spans += [
        {"start": m.start(), "end": m.end(), "label": "credentials"}
        for m in credentials
    ]

    # Warranty
    warranties = list(
        re.finditer(r"(warranty|ticket|reference)[\s:#\-]*\w+", text, flags=re.I)
    )
    spans += [
        {"start": m.start(), "end": m.end(), "label": "warranty"} for m in warranties
    ]

    # Sort and merge highlights
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
