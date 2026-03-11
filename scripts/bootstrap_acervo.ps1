param(
    [string]$Destino = "acervo_pecas"
)

$ErrorActionPreference = "Stop"

$base = Join-Path (Get-Location) $Destino
$dirs = @(
    $base,
    (Join-Path $base "entrada_novas"),
    (Join-Path $base "texto_extraido"),
    (Join-Path $base "catalogadas"),
    (Join-Path $base "metadados"),
    (Join-Path $base "indices"),
    (Join-Path $base "indices\providencias_processos"),
    (Join-Path $base "tipos"),
    (Join-Path $base "referencias"),
    (Join-Path $base "scripts")
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$files = @{
    "README.md" = "# ACERVO DE PECAS`r`n`r`nEstrutura local para catalogar e reaproveitar pecas do proprio usuario.`r`n"
    "entrada_novas\README.md" = "# ENTRADA NOVAS`r`n`r`nColoque aqui arquivos que ainda serao catalogados.`r`n"
    "catalogadas\README.md" = "# CATALOGADAS`r`n`r`nArquivos classificados por tipo principal.`r`n"
    "texto_extraido\README.md" = "# TEXTO EXTRAIDO`r`n`r`nSaidas em markdown geradas a partir dos arquivos originais.`r`n"
    "metadados\README.md" = "# METADADOS`r`n`r`nFichas resumidas por documento catalogado.`r`n"
    "indices\indice_pecas.md" = "# INDICE DE PECAS`r`n"
    "indices\mapa_tipos.md" = "# MAPA DE TIPOS`r`n"
    "indices\providencias_processos\README.md" = "# PROVIDENCIAS PROCESSUAIS`r`n`r`nPlanos gerados a partir de processos integrais.`r`n"
}

foreach ($entry in $files.GetEnumerator()) {
    $target = Join-Path $base $entry.Key
    $parent = Split-Path $target -Parent
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    if (-not (Test-Path $target)) {
        Set-Content -Path $target -Value $entry.Value -Encoding UTF8
    }
}

Write-Output "OK: estrutura criada em $base"
