# PR15 — rodada 1 — falha de contrato do snapshot

- Commit revisado: `2720897`
- Project: `g-p-6a9ba1a060208191a5b6e03a3950b183`
- PR: `ds1david/specify-powerpack#15`
- Resultado: rodada interrompida antes do deep review; nunca foi considerada aprovação.

## Evidência

O transporte ChatGPT Web/SSE autenticou no Project, invocou o GitHub connector e recebeu `confirm_action`. O fluxo renovou Sentinel e obteve `allow` HTTP 200. Porém, o snapshot foi devolvido pelo SSE como `assistant.content.content_type=code` em `content.text`; o parser detectava o código como chamada de ferramenta, mas não extraía o JSON final. O `_extract_json` recebeu texto vazio e retornou `Reviewer did not return a JSON object`.

## Correção encaminhada

O parser passa a distinguir código dirigido a `api_tool.*` de código final dirigido a `all`, preservando o JSON final para o contrato do snapshot. Foi adicionada regressão para ambos os formatos. A próxima rodada deve repetir o snapshot e o deep review no SHA corrigido.
