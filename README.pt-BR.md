# priceintel

[English](README.md) · **Português**

Responde "quanto o governo pagou por isto?" buscando em registros de compras públicas.
Ignora itens só parecidos, converte caixas e pacotes em preço por unidade e descarta valores digitados errado.

![priceintel](docs/screenshots/research-full.png)

## Por que não é só buscar e tirar a média

- Busque *computador* e uma busca simples traz primeiro **"Mesa para computador"**.
- Papel é vendido por resma e por caixa com 10 resmas. Café vem em 250 g, 500 g e 1 kg.
- Às vezes alguém digita o preço da caixa no campo do preço unitário.

Tirando a média sem cuidado, a resposta chega a errar em **968%**.

## O que ele faz

1. **Busca** de dois jeitos ao mesmo tempo, por palavras (BM25) e por similaridade (pgvector), e junta os resultados.
2. **Confere** cada resultado: é este o produto, ou só algo parecido? Quem faz isso pode ser um LLM ou um conjunto de regras, e cada item descartado mostra o motivo. Se sobrar pouca coisa, busca mais fundo.
3. **Converte** embalagens para a unidade base (`CX C/ 10`, `PCT 500G`...).
4. **Remove valores fora da curva** e calcula a mediana e a faixa típica de preço.
5. **Responde** citando os registros de onde saiu cada número. Clicar numa citação leva até a compra na tabela.

Perguntas fora do catálogo ("foguete", "oi") recebem um "não sei", e não um preço inventado.

## Quanto cada etapa ajuda

Medido com dados de teste em que o preço certo é conhecido (detalhes em [`docs/EVAL.md`](docs/EVAL.md), gerado no CI):

| versão | erro típico | pior erro | acertos dentro de 10% |
|---|---|---|---|
| só busca e média | 23,1% | **968,7%** | 4 de 12 |
| + preço por unidade | 3,7% | 97,0% | 8 de 12 |
| + conferência dos itens | 2,1% | 12,4% | 11 de 12 |
| + remoção de outliers | 2,0% | 12,8% | 11 de 12 |
| + busca híbrida (completo) | 2,5% | 14,5% | 11 de 12 |

O CI falha se a qualidade da busca ou o erro de preço piorarem.

Na interface dá para desligar cada etapa e ver a estimativa piorar na hora:

| Sem a conferência, a mediana vira o preço de uma mesa | Página de avaliação |
|---|---|
| ![](docs/screenshots/ablated-judge.png) | ![](docs/screenshots/eval.png) |

## Rodando

```bash
git clone https://github.com/murilo-bassan/hybrid-rag-price-intel.git
cd hybrid-rag-price-intel
pip install -r requirements-dev.txt
docker compose up -d pgvector        # opcional, para o teste com pgvector
python -m pytest
python -m uvicorn priceintel.api:app --port 8900

cd web && npm ci && npm run build && npm start   # http://localhost:3000
```

Ou tudo junto com `docker compose up --build`.

Por padrão a conferência usa regras. Para usar um LLM: `PI_JUDGE=llm`, `PI_JUDGE_MODEL` e `LLM_API_KEY`.

As decisões de projeto estão em [`docs/adr`](docs/adr).

**Stack:** Python, FastAPI, pgvector, Next.js, TypeScript

Os dados são fictícios (órgãos, cidades e fornecedores inventados). Licença MIT.
