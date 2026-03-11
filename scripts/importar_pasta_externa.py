#!/usr/bin/env python3
"""
Importa pecas de uma pasta externa para o acervo local.

Objetivos:
- Aceitar um caminho externo informado no chat
- Detectar arquivos novos/editados desde o ultimo sync
- Ignorar guias e imagens automaticamente
- Em modo "processo", importar o essencial para plano processual:
  - pecas de advogados
  - decisoes/sentencas/despachos
  - certidoes/atos de secretaria
"""

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt"}
IGNORE_NAME_KEYWORDS = {
    "guia",
    "comprovante",
    "boleto",
    "recibo",
    "imagem",
    "foto",
    "print",
    "screenshot",
    "extrato",
    "holerite",
    "gps",
    "gru",
    "darf",
}
PIECE_KEYWORDS = {
    "peticao",
    "inicial",
    "contestacao",
    "replica",
    "impugnacao",
    "embargos",
    "agravo",
    "apelacao",
    "recurso",
    "manifestacao",
    "contrarrazoes",
    "defesa",
    "cumprimento",
    "notificacao",
    "contrato",
    "acordo",
}
JUDGE_KEYWORDS = {
    "decisao",
    "despacho",
    "sentenca",
    "acordao",
    "liminar",
    "tutela",
}
SECRETARY_KEYWORDS = {
    "certidao",
    "mandado",
    "intimacao",
    "citacao",
    "oficio",
    "ato ordinatorio",
}


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "arquivo"


@dataclass
class FileEntry:
    path: Path
    mtime: float
    size: int
    category: str
    reason: str


def classify_file(file_path: Path) -> Tuple[str, str]:
    name = normalize(file_path.stem)
    ext = file_path.suffix.lower()

    if ext not in SUPPORTED_EXTS:
        return "ignorar", "extensao_nao_suportada"

    for kw in IGNORE_NAME_KEYWORDS:
        if kw in name:
            return "ignorar", f"keyword_ignorada:{kw}"

    for kw in JUDGE_KEYWORDS:
        if kw in name:
            return "decisao_judicial", f"keyword:{kw}"

    for kw in SECRETARY_KEYWORDS:
        if kw in name:
            return "ato_secretaria", f"keyword:{kw}"

    for kw in PIECE_KEYWORDS:
        if kw in name:
            return "peca_advogado", f"keyword:{kw}"

    return "nao_classificado", "sem_keyword_clara"


def load_state(state_file: Path) -> Dict:
    if not state_file.exists():
        return {"sources": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {"sources": {}}


def save_state(state_file: Path, data: Dict):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def is_changed(prev_meta: Optional[Dict], mtime: float, size: int) -> bool:
    if prev_meta is None:
        return True
    return float(prev_meta.get("mtime", -1)) != float(mtime) or int(prev_meta.get("size", -1)) != int(size)


def should_import(category: str, mode: str) -> bool:
    if category == "ignorar":
        return False
    if mode == "pecas":
        return category == "peca_advogado"
    if mode == "processo":
        return category in {"peca_advogado", "decisao_judicial", "ato_secretaria"}
    return False


def unique_target(dest_dir: Path, src_name: str, category: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = slugify(Path(src_name).stem)
    ext = Path(src_name).suffix.lower()
    base = f"import_{timestamp}_{category}_{stem}{ext}"
    target = dest_dir / base
    counter = 1
    while target.exists():
        target = dest_dir / f"import_{timestamp}_{category}_{stem}_{counter}{ext}"
        counter += 1
    return target


def copy_file(src: Path, dst: Path):
    dst.write_bytes(src.read_bytes())


def build_report(
    source: Path,
    mode: str,
    imported: List[FileEntry],
    ignored: List[FileEntry],
    report_file: Path,
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = []
    lines.append("# RELATORIO DE IMPORTACAO EXTERNA")
    lines.append("")
    lines.append(f"- atualizado_em: {now}")
    lines.append(f"- origem: {source}")
    lines.append(f"- modo: {mode}")
    lines.append(f"- importados: {len(imported)}")
    lines.append(f"- ignorados: {len(ignored)}")
    lines.append("")
    lines.append("## Importados")
    lines.append("| categoria | arquivo | motivo |")
    lines.append("|---|---|---|")
    if imported:
        for item in imported:
            lines.append(f"| {item.category} | {item.path.name} | {item.reason} |")
    else:
        lines.append("| - | - | nenhum arquivo importado |")

    lines.append("")
    lines.append("## Ignorados")
    lines.append("| categoria | arquivo | motivo |")
    lines.append("|---|---|---|")
    if ignored:
        for item in ignored[:200]:
            lines.append(f"| {item.category} | {item.path.name} | {item.reason} |")
    else:
        lines.append("| - | - | nenhum arquivo ignorado |")

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def walk_files(source: Path) -> List[Path]:
    return [p for p in source.rglob("*") if p.is_file()]


def main():
    parser = argparse.ArgumentParser(description="Importa pecas de pasta externa para entrada_novas")
    parser.add_argument("--origem", required=True, help="Caminho da pasta externa")
    parser.add_argument("--modo", choices=["pecas", "processo"], default="pecas")
    parser.add_argument("--destino", default="acervo_pecas/entrada_novas")
    parser.add_argument("--state", default="acervo_pecas/indices/sync_importacao_externa.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = Path(args.origem).expanduser().resolve()
    dest = Path(args.destino)
    state_file = Path(args.state)

    if not source.exists() or not source.is_dir():
        raise SystemExit(f"Pasta de origem invalida: {source}")

    state = load_state(state_file)
    source_key = str(source).lower()
    src_state = state["sources"].get(source_key, {"files": {}, "last_sync_utc": None})
    prev_files_meta: Dict[str, Dict] = src_state.get("files", {})

    all_files = walk_files(source)
    imported: List[FileEntry] = []
    ignored: List[FileEntry] = []
    new_files_meta: Dict[str, Dict] = {}

    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    for p in all_files:
        p_key = str(p).lower()
        stat = p.stat()
        mtime = float(stat.st_mtime)
        size = int(stat.st_size)
        new_files_meta[p_key] = {"mtime": mtime, "size": size}

        if not is_changed(prev_files_meta.get(p_key), mtime, size):
            continue

        category, reason = classify_file(p)
        entry = FileEntry(path=p, mtime=mtime, size=size, category=category, reason=reason)

        if should_import(category, args.modo):
            imported.append(entry)
            if not args.dry_run:
                target = unique_target(dest, p.name, category)
                copy_file(p, target)
        else:
            ignored.append(entry)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["sources"][source_key] = {"files": new_files_meta, "last_sync_utc": now_utc}
    if not args.dry_run:
        save_state(state_file, state)

    report_name = f"_relatorio_importacao_externa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_file = dest / report_name
    if not args.dry_run:
        build_report(source, args.modo, imported, ignored, report_file)

    print(
        "OK: "
        f"origem={source} modo={args.modo} importados={len(imported)} ignorados={len(ignored)}"
        + (" (dry-run)" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
