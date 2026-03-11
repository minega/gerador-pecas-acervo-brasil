#!/usr/bin/env python3
"""
Cataloga automaticamente arquivos em acervo_pecas/entrada_novas.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


TYPE_RULES: Dict[str, Dict[str, object]] = {
    "contrato_compra_e_venda": {
        "descricao": "Contratos de compra e venda e variacoes",
        "materia": "civel_contratual",
        "fase": "pre_processual",
        "keywords": ["contrato", "compra e venda", "comprador", "vendedor"],
        "reuse_parts": "estrutura de clausulas; matriz de risco; clausulas de inadimplemento",
        "reuse_risks": "revisar partes, objeto, valores, prazos e garantias",
    },
    "peticao_inicial": {
        "descricao": "Peticoes iniciais de procedimento comum ou especial",
        "materia": "civel_conhecimento",
        "fase": "conhecimento",
        "keywords": ["peticao inicial", "acao de", "parte autora", "vem, com fundamento"],
        "reuse_parts": "estrutura narrativa; fundamentos juridicos; pedidos finais",
        "reuse_risks": "revisar competencia, valor da causa, pedidos e provas do caso",
    },
    "contestacao": {
        "descricao": "Contestacoes e defesas de merito em primeiro grau",
        "materia": "civel_conhecimento",
        "fase": "conhecimento",
        "keywords": ["contestacao", "parte re", "preliminarmente", "impugna"],
        "reuse_parts": "estrutura defensiva; preliminares; impugnacao de merito",
        "reuse_risks": "adequar a defesa aos fatos e pedidos da inicial concreta",
    },
    "replica": {
        "descricao": "Replicas e manifestacoes sobre contestacao",
        "materia": "civel_conhecimento",
        "fase": "conhecimento",
        "keywords": ["replica", "contestacao", "impugna a contestacao"],
        "reuse_parts": "ordem de refutacao; reforco probatorio; fechamento conclusivo",
        "reuse_risks": "responder especificamente aos pontos centrais da contestacao",
    },
    "impugnacao_documentos": {
        "descricao": "Impugnacoes de documentos e autenticidade",
        "materia": "civel_processual",
        "fase": "conhecimento",
        "keywords": ["impugnacao", "documentos", "autenticidade", "falsidade"],
        "reuse_parts": "ataque documental; pedidos de prova tecnica",
        "reuse_risks": "adequar o fundamento ao vicio documental concreto",
    },
    "peticao_de_custas": {
        "descricao": "Peticoes sobre custas, preparo e recolhimentos",
        "materia": "civel_processual",
        "fase": "conhecimento_ou_execucao",
        "keywords": ["custas", "guia", "preparo", "recolhimento", "comprovante"],
        "reuse_parts": "peticao enxuta de cumprimento; organizacao dos comprovantes",
        "reuse_risks": "validar guia, valor, prazo e finalidade do recolhimento",
    },
    "peticao_juntada": {
        "descricao": "Peticoes de juntada, comunicacao e retificacao de atos processuais",
        "materia": "civel_processual",
        "fase": "conhecimento_ou_execucao",
        "keywords": ["juntada", "retificacao", "erro material", "documentos anexos", "art. 1.018", "informa que", "interpos agravo de instrumento"],
        "reuse_parts": "estrutura enxuta; comunicacao objetiva; sequencia de anexacao",
        "reuse_risks": "atualizar processo, ids, datas e anexos",
    },
    "peticao_citacao_negativa": {
        "descricao": "Peticoes para providencias apos tentativa frustrada de citacao",
        "materia": "civel_processual",
        "fase": "conhecimento",
        "keywords": ["citacao", "negativa", "novo endereco", "certidao negativa"],
        "reuse_parts": "pedido de nova diligencia; organizacao do novo endereco",
        "reuse_risks": "revisar enderecos e meio de citacao cabivel",
    },
    "peticao_prorrogacao_prazo": {
        "descricao": "Peticoes para dilacao de prazo e/ou suspensao de exigibilidade",
        "materia": "processual",
        "fase": "conhecimento_ou_execucao",
        "keywords": ["prorrogacao", "dilacao", "prazo", "parcelamento", "suspensao"],
        "reuse_parts": "narrativa do impedimento; pedido de prazo adicional",
        "reuse_risks": "revisar prazo requerido e justificativa documentada",
    },
    "peticao_especificacao_provas": {
        "descricao": "Peticoes para especificacao de provas na fase instrutoria",
        "materia": "civel_conhecimento",
        "fase": "instrucao",
        "keywords": ["especificacao de provas", "prova testemunhal", "prova pericial"],
        "reuse_parts": "justificativa de pertinencia; pedidos probatorios",
        "reuse_risks": "adequar as provas aos pontos controvertidos",
    },
    "peticao_cumprimento_sentenca": {
        "descricao": "Peticoes para prosseguimento e atos executivos no cumprimento",
        "materia": "civel_execucao",
        "fase": "cumprimento_sentenca",
        "keywords": ["cumprimento de sentenca", "inadimplemento", "prosseguimento"],
        "reuse_parts": "roteiro executivo; pedidos constritivos",
        "reuse_risks": "atualizar memoria de calculo e marcos temporais",
    },
    "agravo_instrumento": {
        "descricao": "Recursos de agravo com pedido de tutela recursal",
        "materia": "civel_recursal",
        "fase": "recurso",
        "keywords": ["agravo de instrumento", "tutela recursal", "art. 1.015"],
        "reuse_parts": "cabimento; tempestividade; tutela recursal",
        "reuse_risks": "validar cabimento, prazo e pecas obrigatorias",
    },
    "apelacao": {
        "descricao": "Apelacoes e recursos contra sentenca",
        "materia": "civel_recursal",
        "fase": "recurso",
        "keywords": ["apelacao", "sentenca", "art. 1.009"],
        "reuse_parts": "estrutura recursal; topicos de reforma",
        "reuse_risks": "alinhar fundamentos aos capitulos impugnados da sentenca",
    },
    "notificacao_extrajudicial_cobranca": {
        "descricao": "Notificacoes extrajudiciais de cobranca",
        "materia": "civel_preprocessual",
        "fase": "pre_processual",
        "keywords": ["notificacao extrajudicial", "constituir em mora", "prazo para pagamento", "cobranca"],
        "reuse_parts": "estrutura de mora; demonstrativo de debito; fecho de advertencia",
        "reuse_risks": "confirmar memoria de calculo, vencimento e forma de pagamento",
    },
    "processo_integral": {
        "descricao": "Dumps integrais para mapear providencias apos atos do juizo",
        "materia": "processual",
        "fase": "multipla",
        "keywords": ["movimentacao", "processo:", "num.", "despacho", "sentenca", "acordao"],
        "reuse_parts": "recorte por evento; triagem de providencias; controle de prazos",
        "reuse_risks": "nao usar o dump integral como minuta sem triagem",
    },
    "procuracao": {
        "descricao": "Instrumentos de mandato para suporte de representacao",
        "materia": "documento_suporte",
        "fase": "suporte",
        "keywords": ["procuracao", "outorgante", "outorgado", "mandato"],
        "reuse_parts": "qualificacao; poderes; bloco de assinatura",
        "reuse_risks": "confirmar poderes especiais, dados e assinaturas",
    },
}


@dataclass
class Registro:
    id_peca: str
    arquivo_original: str
    caminho_catalogado: str
    texto_extraido: str
    data_catalogacao: str
    tipo: str
    subtipo: str
    materia: str
    fase: str
    confianca_classificacao: str
    secoes_principais: str
    padrao_pedidos: str
    padrao_provas: str
    tese_central: str
    fundamentos_legais: str
    precedentes: str
    qualidade_reuso: int
    partes_reutilizaveis: str
    riscos_reutilizar: str
    origem: str
    observacao: str
    pendencias: str


def fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", errors="ignore").decode("ascii", errors="ignore").lower()


def slugify(text: str) -> str:
    folded = fold_text(text)
    folded = re.sub(r"[^a-z0-9._-]+", "_", folded)
    folded = re.sub(r"_+", "_", folded)
    return folded.strip("_") or "arquivo"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def ensure_structure(acervo_dir: Path):
    for relative in [
        "entrada_novas",
        "texto_extraido",
        "catalogadas",
        "metadados",
        "indices",
        "indices/providencias_processos",
        "indices/relatorios_entrada",
        "tipos",
    ]:
        (acervo_dir / relative).mkdir(parents=True, exist_ok=True)


def next_id(metadata_dir: Path) -> str:
    numbers = []
    for path in metadata_dir.glob("P*.md"):
        match = re.match(r"P(\d+)\.md$", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return f"P{(max(numbers) if numbers else 0) + 1:04d}"


def run_python(script: Path, args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, check=False)


def extract_text(file_path: Path, output_dir: Path, scripts_dir: Path) -> Tuple[Path, str]:
    target = output_dir / f"{slugify(file_path.stem)}.md"
    if not target.exists():
        result = run_python(scripts_dir / "extract_legal_text.py", ["--input", str(file_path), "--output", str(output_dir)])
        if result.returncode != 0:
            fallback = (
                f"# TEXTO EXTRAIDO - {file_path.name}\n\n"
                "## Nota\nfalha ao extrair automaticamente; revisar manualmente.\n\n"
                "## Conteudo\n[sem texto extraido]\n"
            )
            target.write_text(fallback, encoding="utf-8")
    return target, read_text(target)


def classify(file_name: str, content: str) -> Tuple[str, str]:
    haystack_name = fold_text(file_name)
    haystack_text = fold_text(content[:12000])
    scores: Dict[str, int] = {}
    for tipo, data in TYPE_RULES.items():
        score = 0
        for keyword in data["keywords"]:
            token = fold_text(str(keyword))
            if token in haystack_name:
                score += 3
            if token in haystack_text:
                score += 1
        if tipo in haystack_name:
            score += 8
        if tipo == "agravo_instrumento" and "agravo de instrumento" in haystack_text:
            score += 8
        if tipo == "peticao_juntada" and ("art. 1.018" in haystack_text or "junta nesta oportunidade" in haystack_text):
            score += 8
        if tipo == "procuracao" and haystack_text.startswith("# texto extraido - procuracao"):
            score += 8
        if tipo == "processo_integral" and "movimentacao" in haystack_text:
            score += 3
        if tipo == "peticao_de_custas" and "agravo de instrumento" in haystack_text:
            score -= 4
        scores[tipo] = score
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_tipo, best_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0
    if best_score <= 0:
        return "peticao_juntada", "baixa"
    if best_score >= 6 and best_score - second_score >= 2:
        return best_tipo, "alta"
    if best_score >= 3:
        return best_tipo, "media"
    return best_tipo, "baixa"


def infer_subtipo(tipo: str, file_name: str, content: str) -> str:
    haystack = fold_text(f"{file_name} {content[:8000]}")
    if tipo == "contrato_compra_e_venda":
        if "veiculo" in haystack:
            return "veiculo"
        if "imovel" in haystack or "terreno" in haystack:
            return "imovel"
        return "generico"
    if tipo == "peticao_juntada":
        if "1.018" in haystack or "agravo" in haystack:
            return "aviso_interposicao_agravo_art_1018_cpc"
        if "retific" in haystack:
            return "retificacao_erro_material"
        if "procurac" in haystack:
            return "juntada_procuracoes"
        return "juntada_documental_simples"
    if tipo == "peticao_de_custas":
        return "juntada_de_guia" if "guia" in haystack else "regularizacao_custas"
    if tipo == "peticao_citacao_negativa":
        return "novo_endereco_apos_certidao_negativa"
    if tipo == "peticao_especificacao_provas":
        return "especificacao_provas_fase_instrutoria"
    if tipo == "peticao_cumprimento_sentenca":
        return "prosseguimento_por_inadimplemento"
    if tipo == "peticao_prorrogacao_prazo":
        return "pedido_dilacao_prazo"
    if tipo == "agravo_instrumento":
        return "tutela_recursal"
    if tipo == "apelacao":
        return "reforma_de_sentenca"
    if tipo == "notificacao_extrajudicial_cobranca":
        return "constituicao_em_mora"
    if tipo == "processo_integral":
        return "dump_execucao_fiscal" if "execucao fiscal" in haystack else "dump_processo_integral"
    if tipo == "procuracao":
        if "outorgante" in haystack and "cpf" in haystack and "cnpj" not in haystack.split("outorgado", 1)[0]:
            return "instrumento_mandato_pessoa_fisica"
        if "pessoa juridica" in haystack or ("cnpj" in haystack and "outorgante" in haystack):
            return "instrumento_mandato_pessoa_juridica"
        return "instrumento_mandato_pessoa_fisica"
    return "generico"


def extract_sections(content: str) -> str:
    sections: List[str] = []
    for line in content.splitlines():
        stripped = line.strip().strip("#").strip()
        if not stripped:
            continue
        if line.lstrip().startswith("#"):
            sections.append(fold_text(stripped).replace("_", " "))
        if len(sections) == 6:
            break
    return "; ".join(sections) if sections else "estrutura ainda nao consolidada"


def extract_refs(content: str, patterns: List[str], default: str) -> str:
    found: List[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, content, flags=re.IGNORECASE):
            cleaned = re.sub(r"\s+", " ", match).strip(" .;,:")
            if cleaned not in found:
                found.append(cleaned)
    return "; ".join(found[:6]) if found else default


def estimate_quality(tipo: str, content: str) -> int:
    size = len(content)
    score = 2
    if size > 2500:
        score += 1
    if size > 6000:
        score += 1
    if tipo in {"procuracao", "processo_integral"}:
        return 2 if tipo == "procuracao" else 3
    return max(1, min(score, 5))


def infer_tese(tipo: str, subtipo: str) -> str:
    if tipo.startswith("contrato_"):
        return f"instrumentalizacao contratual no subtipo {subtipo}"
    mapping = {
        "peticao_inicial": "apresentacao organizada da pretensao com fatos, fundamentos e pedidos",
        "contestacao": "resistencia aos pedidos iniciais com impugnacao especifica",
        "replica": "refutacao dirigida da contestacao para preservar a tese inicial",
        "impugnacao_documentos": "ataque objetivo ao valor probatorio de documentos juntados",
        "peticao_de_custas": "regularizacao ou comprovacao de recolhimento processual",
        "peticao_juntada": "comunicacao processual objetiva com juntada ou retificacao",
        "peticao_citacao_negativa": "superacao de tentativa frustrada de citacao",
        "peticao_prorrogacao_prazo": "pedido de prazo adicional por justificativa documentada",
        "peticao_especificacao_provas": "delimitacao das provas pertinentes na fase instrutoria",
        "peticao_cumprimento_sentenca": "prosseguimento executivo diante do inadimplemento",
        "agravo_instrumento": "reforma imediata de decisao interlocutoria com urgencia recursal",
        "apelacao": "reforma ou anulacao de sentenca",
        "notificacao_extrajudicial_cobranca": "constituicao em mora e cobranca pre-processual",
        "processo_integral": "triagem tecnica de movimentacoes e atos do processo",
        "procuracao": "outorga de poderes de representacao",
    }
    return mapping.get(tipo, f"estrutura principal do tipo {tipo}")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def move_original(file_path: Path, acervo_dir: Path, tipo: str) -> Path:
    dest_dir = acervo_dir / "catalogadas" / tipo
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = unique_path(dest_dir / f"{slugify(file_path.stem)}{file_path.suffix.lower()}")
    shutil.move(str(file_path), str(dest_path))
    return dest_path


def write_metadata(registro: Registro, metadata_dir: Path):
    content = f"""## Identificacao
- id_peca: {registro.id_peca}
- arquivo_original: {registro.arquivo_original}
- caminho_catalogado: {registro.caminho_catalogado}
- texto_extraido: {registro.texto_extraido}
- data_catalogacao: {registro.data_catalogacao}
- origem: {registro.origem}

## Classificacao
- tipo: {registro.tipo}
- subtipo: {registro.subtipo}
- materia: {registro.materia}
- fase: {registro.fase}
- confianca_classificacao: {registro.confianca_classificacao}

## Estrutura da peca
- secoes principais: {registro.secoes_principais}
- padrao de pedidos: {registro.padrao_pedidos}
- padrao de provas/documentos: {registro.padrao_provas}

## Tese e fundamento
- tese central: {registro.tese_central}
- fundamentos legais citados na propria peca: {registro.fundamentos_legais}
- precedentes presentes na propria peca: {registro.precedentes}

## Reuso
- qualidade_reuso (1-5): {registro.qualidade_reuso}
- partes reutilizaveis: {registro.partes_reutilizaveis}
- riscos ao reutilizar: {registro.riscos_reutilizar}
- observacao: {registro.observacao}

## Pendencias
- {registro.pendencias}
"""
    (metadata_dir / f"{registro.id_peca}.md").write_text(content, encoding="utf-8")


def parse_metadata(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and ":" in stripped:
            key, value = stripped[2:].split(":", 1)
            data[key.strip()] = value.strip()
    return data


def write_orientacoes(type_dir: Path, tipo: str, itens: List[Dict[str, str]]):
    folder = type_dir / tipo
    folder.mkdir(parents=True, exist_ok=True)
    config = TYPE_RULES.get(tipo, {})
    aprendizado = [f"- {item.get('id_peca', '?')}: {item.get('observacao', 'registro catalogado')}." for item in itens[-8:]]
    content = [
        f"# ORIENTACOES - {tipo.upper()}",
        "",
        "## Escopo do tipo",
        f"- Definicao: {config.get('descricao', 'tipo catalogado automaticamente')}.",
        "- Limites: adaptar sempre ao caso concreto antes de reutilizar.",
        "",
        "## Aprendizado acumulado",
        *aprendizado,
        "",
        "## Regras para reutilizacao futura",
        "- Reaproveitar primeiro a estrutura e os padrões desse tipo.",
        "- Revisar dados concretos, documentos, prazos e valores antes de reaproveitar.",
        "- Validar aderencia ao rito e ao objetivo da nova peca.",
        "",
    ]
    (folder / "ORIENTACOES.md").write_text("\n".join(content), encoding="utf-8")


def regenerate_indexes(acervo_dir: Path):
    metadata_dir = acervo_dir / "metadados"
    type_dir = acervo_dir / "tipos"
    index_dir = acervo_dir / "indices"
    itens = [parse_metadata(path) for path in sorted(metadata_dir.glob("P*.md"))]
    itens.sort(key=lambda item: item.get("id_peca", ""))

    indice = [
        "# INDICE GERAL DE PECAS",
        "",
        "| id_peca | arquivo | tipo | subtipo | materia | fase | qualidade_reuso (1-5) | origem | observacao |",
        "|---|---|---|---|---|---|---:|---|---|",
    ]
    agrupados: Dict[str, List[Dict[str, str]]] = {}
    for item in itens:
        agrupados.setdefault(item.get("tipo", "nao_classificado"), []).append(item)
        indice.append(
            f"| {item.get('id_peca', '-')} | {Path(item.get('caminho_catalogado', '-')).name} | "
            f"{item.get('tipo', '-')} | {item.get('subtipo', '-')} | {item.get('materia', '-')} | "
            f"{item.get('fase', '-')} | {item.get('qualidade_reuso (1-5)', '-')} | "
            f"{item.get('origem', '-')} | {item.get('observacao', '-')} |"
        )
    (index_dir / "indice_pecas.md").write_text("\n".join(indice) + "\n", encoding="utf-8")

    mapa = [
        "# MAPA DE TIPOS",
        "",
        "| tipo | descricao curta | total_pecas | ultima_atualizacao | arquivo_orientacoes |",
        "|---|---|---:|---|---|",
    ]
    for tipo in sorted(agrupados):
        itens_tipo = agrupados[tipo]
        latest = max((item.get("data_catalogacao", "") for item in itens_tipo), default="")
        mapa.append(
            f"| {tipo} | {TYPE_RULES.get(tipo, {}).get('descricao', 'tipo catalogado automaticamente')} | "
            f"{len(itens_tipo)} | {latest} | acervo_pecas/tipos/{tipo}/ORIENTACOES.md |"
        )
        write_orientacoes(type_dir, tipo, itens_tipo)
    (index_dir / "mapa_tipos.md").write_text("\n".join(mapa) + "\n", encoding="utf-8")


def write_report(acervo_dir: Path, registros: List[Registro]):
    report_dir = acervo_dir / "indices" / "relatorios_entrada"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lines = [
        "# RELATORIO DE CATALOGACAO",
        "",
        f"- data_hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- total_catalogado: {len(registros)}",
        "",
        "| id_peca | arquivo | tipo | subtipo | confianca |",
        "|---|---|---|---|---|",
    ]
    for registro in registros:
        lines.append(
            f"| {registro.id_peca} | {Path(registro.caminho_catalogado).name} | {registro.tipo} | {registro.subtipo} | {registro.confianca_classificacao} |"
        )
    (report_dir / f"catalogacao_{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_post_decision(acervo_dir: Path, scripts_dir: Path):
    run_python(
        scripts_dir / "gerar_plano_pos_decisao.py",
        [
            "--texto-dir",
            str(acervo_dir / "texto_extraido"),
            "--saida-dir",
            str(acervo_dir / "indices" / "providencias_processos"),
        ],
    )


def catalogar(acervo_dir: Path):
    ensure_structure(acervo_dir)
    scripts_dir = Path(__file__).resolve().parent
    entrada_dir = acervo_dir / "entrada_novas"
    texto_dir = acervo_dir / "texto_extraido"
    metadata_dir = acervo_dir / "metadados"
    registros: List[Registro] = []

    arquivos = sorted(path for path in entrada_dir.iterdir() if path.is_file() and not path.name.lower().startswith("readme"))
    for arquivo in arquivos:
        texto_path, texto = extract_text(arquivo, texto_dir, scripts_dir)
        tipo, confianca = classify(arquivo.name, texto)
        subtipo = infer_subtipo(tipo, arquivo.name, texto)
        destino = move_original(arquivo, acervo_dir, tipo)
        config = TYPE_RULES[tipo]
        registro = Registro(
            id_peca=next_id(metadata_dir),
            arquivo_original=arquivo.name,
            caminho_catalogado=str(destino).replace("\\", "/"),
            texto_extraido=str(texto_path).replace("\\", "/"),
            data_catalogacao=datetime.now().strftime("%Y-%m-%d"),
            tipo=tipo,
            subtipo=subtipo,
            materia=str(config["materia"]),
            fase=str(config["fase"]),
            confianca_classificacao=confianca,
            secoes_principais=extract_sections(texto),
            padrao_pedidos="nao aplicavel (instrumento contratual)"
            if tipo.startswith("contrato_") or tipo == "procuracao"
            else "pedidos objetivos e aderentes ao rito",
            padrao_provas="nao identificado automaticamente",
            tese_central=infer_tese(tipo, subtipo),
            fundamentos_legais=extract_refs(texto, [r"art(?:s)?\.\s*[\d.,ºo §\-a-zA-Z]+(?:\s+do\s+[A-Z]{2,4})?", r"lei\s+\d[\d./-]+"], "nao identificado automaticamente"),
            precedentes=extract_refs(texto, [r"sumula\s+\d+", r"tema\s+\d+", r"resp\s+\d[\d.]+"], "nao identificado automaticamente"),
            qualidade_reuso=estimate_quality(tipo, texto),
            partes_reutilizaveis=str(config["reuse_parts"]),
            riscos_reutilizar=str(config["reuse_risks"]),
            origem="entrada_novas",
            observacao=f"catalogado como {tipo}/{subtipo}",
            pendencias="revisar classificacao e acentos apos catalogacao automatica",
        )
        write_metadata(registro, metadata_dir)
        registros.append(registro)

    regenerate_indexes(acervo_dir)
    if any(item.tipo == "processo_integral" for item in registros):
        generate_post_decision(acervo_dir, scripts_dir)
    write_report(acervo_dir, registros)
    print(f"OK: arquivos catalogados={len(registros)}")


def main():
    parser = argparse.ArgumentParser(description="Cataloga automaticamente arquivos em acervo_pecas/entrada_novas")
    parser.add_argument("--acervo", default="acervo_pecas", help="Pasta raiz do acervo")
    args = parser.parse_args()
    catalogar(Path(args.acervo))


if __name__ == "__main__":
    main()
