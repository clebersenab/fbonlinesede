# Banco de horas FB Online: cálculo mensal

1. Converter o PDF do mês (Relatório de Exceções) em texto: `pdftotext -layout ocorrencias.pdf oc.txt`
2. Extrair as marcações: `python3 parse.py oc.txt AAAA-MM.json`
3. Calcular o acumulado com todos os meses, em ordem: `python3 compute.py dados.json 2026-10.json 2026-11.json ...`
4. Enviar `dados.json` pelo botão "Atualizar dados" em /banco-de-horas.

As regras (jornada, home office por equipe, feriados, almoço, faltas) ficam no início de `compute.py` e são gravadas junto com os dados, no campo `regras`.
Os arquivos de ponto não ficam neste repositório, que é público.
