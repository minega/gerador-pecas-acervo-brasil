#!/usr/bin/env python3
import argparse
import re
import shutil
import zipfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET


def slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_") or "arquivo"


def normalize_text(text: str) -> str:
    # Attempt to repair common mojibake artifacts from mixed encodings.
    if "Ã" in text or "Â" in text:
        try:
            repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if repaired:
                text = repaired
        except Exception:
            pass
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks = []
    for node in root.findall(".//w:t", ns):
        if node.text:
            chunks.append(node.text)
    text = " ".join(chunks)
    return normalize_text(text)


def extract_pdf_text_optional(path: Path):
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None, "pypdf nao instalado; PDF mantido sem extracao textual automatica"

    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
        text = normalize_text("\n\n".join(pages))
        if not text:
            return None, "PDF sem texto extraivel (possivel imagem/scan)"
        return text, None
    except Exception as exc:
        return None, f"falha ao extrair PDF: {exc}"


def extract_plain(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return normalize_text(raw)


def write_output(out_dir: Path, src_file: Path, text: str, note: Optional[str]):
    out_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(src_file.stem)
    text_file = out_dir / f"{base}.md"
    with text_file.open("w", encoding="utf-8") as fh:
        fh.write(f"# TEXTO EXTRAIDO - {src_file.name}\n\n")
        if note:
            fh.write(f"## Nota\n{note}\n\n")
        fh.write("## Conteudo\n")
        fh.write(text if text else "[sem texto extraido]")
        fh.write("\n")


def process_file(src: Path, out_dir: Path):
    if src.name.lower().startswith("readme"):
        return

    ext = src.suffix.lower()
    if ext == ".docx":
        text = extract_docx_text(src)
        write_output(out_dir, src, text, None)
        return
    if ext == ".pdf":
        text, note = extract_pdf_text_optional(src)
        write_output(out_dir, src, text or "", note)
        return
    if ext in {".txt", ".md"}:
        write_output(out_dir, src, extract_plain(src), None)
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{slugify(src.name)}.bin"
    shutil.copy2(src, target)


def main():
    parser = argparse.ArgumentParser(description="Extrai texto de DOCX/PDF/TXT/MD para markdown")
    parser.add_argument("--input", required=True, help="arquivo ou pasta de entrada")
    parser.add_argument("--output", required=True, help="pasta de saida")
    args = parser.parse_args()

    src = Path(args.input)
    out_dir = Path(args.output)

    if src.is_file():
        process_file(src, out_dir)
        return

    if src.is_dir():
        for item in sorted(src.iterdir()):
            if item.is_file():
                process_file(item, out_dir)
        return

    raise SystemExit("Caminho de entrada invalido")


if __name__ == "__main__":
    main()
