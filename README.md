# priceintel

**English** · [Português](README.pt-BR.md)

Answers "how much did the government pay for this?" by searching public purchase records.
It skips items that only look similar, turns boxes and packs into unit prices, and drops values typed in wrong.

![priceintel](docs/screenshots/research-full.png)

## Why it isn't just search and average

- Search for *computador* (computer) and a plain search returns **"computer desk"** first.
- Paper is sold by the ream and by the box of 10 reams. Coffee comes in 250 g, 500 g and 1 kg.
- Sometimes someone types the box price into the unit price field.

Average that carelessly and the answer can be off by **968%**.

## What it does

1. **Searches** two ways at once, by words (BM25) and by similarity (pgvector), and merges the results.
2. **Checks** each result: is this the product, or just something similar? An LLM or a set of rules does this, and every rejected item shows why. If too little is left, it searches deeper.
3. **Converts** packages to the base unit (`CX C/ 10`, `PCT 500G`...).
4. **Drops outliers** and computes the median and the typical price range.
5. **Answers** citing the records behind every number. Clicking a citation jumps to that purchase in the table.

Questions outside the catalog ("rocket", "hi") get an "I don't know" instead of a made-up price.

## How much each step helps

Measured on test data where the right price is known (details in [`docs/EVAL.md`](docs/EVAL.md), generated in CI):

| version | typical error | worst error | within 10% |
|---|---|---|---|
| search and average only | 23.1% | **968.7%** | 4 of 12 |
| + unit prices | 3.7% | 97.0% | 8 of 12 |
| + item check | 2.1% | 12.4% | 11 of 12 |
| + outlier removal | 2.0% | 12.8% | 11 of 12 |
| + hybrid search (full) | 2.5% | 14.5% | 11 of 12 |

CI fails if search quality or price error gets worse.

In the app you can switch off each step and watch the estimate get worse right away:

| Without the item check, the median becomes the price of a desk | Evaluation page |
|---|---|
| ![](docs/screenshots/ablated-judge.png) | ![](docs/screenshots/eval.png) |

## Running it

```bash
git clone https://github.com/murilo-bassan/hybrid-rag-price-intel.git
cd hybrid-rag-price-intel
pip install -r requirements-dev.txt
docker compose up -d pgvector        # optional, for the pgvector test
python -m pytest
python -m uvicorn priceintel.api:app --port 8900

cd web && npm ci && npm run build && npm start   # http://localhost:3000
```

Or everything at once with `docker compose up --build`.

By default the item check uses rules. To use an LLM: `PI_JUDGE=llm`, `PI_JUDGE_MODEL` and `LLM_API_KEY`.

Design decisions are in [`docs/adr`](docs/adr).

**Stack:** Python, FastAPI, pgvector, Next.js, TypeScript

The data is made up (agencies, cities and suppliers are invented). MIT license.
