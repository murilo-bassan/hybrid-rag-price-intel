"""Synthetic procurement records with a hidden ground truth.

Each record looks like a line of a public purchase: a free-text description
written by a buyer, a packaging label, a quantity and a price per package.
Unlike real data, every record also carries its true `category` and the true
`base_price` of one comparable unit — so retrieval quality and price-estimate
error can be *measured*, not eyeballed.

The generator deliberately reproduces what makes the real problem hard:
  * distractors that share words with the product ("mesa para computador",
    "suporte para notebook", "mouse pad"),
  * the same product sold in different packages (box of 10, pack of 500 g, 1 kg),
  * buyer typos and abbreviations,
  * ~3% price-entry errors (box price typed as unit price and vice versa, ×10 slips).
Fixed seed: identical on every machine. Agencies, towns and suppliers are fictional.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from functools import lru_cache


@dataclass(frozen=True)
class Product:
    category: str
    names: tuple[str, ...]
    base_unit: str              # what one comparable unit is: "un", "kg", "l", "resma"
    base_price: float           # true price of one base unit (BRL)
    packages: tuple[tuple[str, float], ...]   # (label, how many base units it holds)


CATALOG: tuple[Product, ...] = (
    Product("notebook", ("Notebook 15,6\" Core i5 8GB SSD 256GB", "Notebook 14 pol Ryzen 5 8GB SSD 512GB",
                         "NOTEBOOK I5 8GB 256GB SSD TELA 15.6", "Computador portátil notebook Core i5 16GB"),
            "un", 4200, (("UN", 1),)),
    Product("desktop", ("Computador desktop Core i5 8GB SSD 256GB", "Microcomputador desktop i5 16GB 512GB SSD",
                        "COMPUTADOR TIPO DESKTOP COM MONITOR 21,5", "Estação de trabalho desktop Ryzen 7 32GB"),
            "un", 3900, (("UN", 1),)),
    Product("monitor", ("Monitor LED 24 polegadas Full HD", "Monitor 23,8\" IPS Full HD HDMI", "MONITOR LED 24 POL"),
            "un", 950, (("UN", 1),)),
    Product("mouse", ("Mouse óptico USB 1200 dpi", "MOUSE OPTICO C/ FIO USB", "Mouse sem fio 2.4GHz"),
            "un", 32, (("UN", 1), ("CX C/ 10", 10))),
    Product("teclado", ("Teclado ABNT2 USB", "TECLADO PADRAO ABNT 2 C/ FIO", "Teclado sem fio ABNT2"),
            "un", 58, (("UN", 1),)),
    Product("papel_a4", ("Papel sulfite A4 75g/m²", "PAPEL A4 BRANCO 75G 210X297MM", "Papel sulfite branco formato A4"),
            "resma", 27, (("RESMA 500 FL", 1), ("CX C/ 10 RESMAS", 10), ("CX C/ 5 RESMAS", 5))),
    Product("cafe", ("Café torrado e moído tradicional", "CAFE TORRADO MOIDO EMBALAGEM ALTO VACUO", "Café em pó tradicional"),
            "kg", 42, (("PCT 500G", 0.5), ("PCT 250G", 0.25), ("PCT 1KG", 1.0))),
    Product("agua", ("Água mineral sem gás 500ml", "AGUA MINERAL NATURAL S/ GAS 500 ML", "Água mineral garrafa 500ml"),
            "un", 1.9, (("UN", 1), ("FARDO C/ 12", 12))),
    Product("cadeira", ("Cadeira giratória com braços", "CADEIRA GIRATORIA ESPALDAR MEDIO C/ BRACOS", "Cadeira de escritório giratória"),
            "un", 720, (("UN", 1),)),
    Product("toner", ("Toner compatível HP CE285A", "TONER COMPATIVEL 85A PRETO", "Cartucho de toner preto compatível"),
            "un", 88, (("UN", 1),)),
    Product("detergente", ("Detergente líquido neutro 500ml", "DETERGENTE NEUTRO 500 ML", "Detergente lava-louças neutro"),
            "un", 2.8, (("UN", 1), ("CX C/ 24", 24))),
    Product("caneta", ("Caneta esferográfica azul", "CANETA ESFEROGRAFICA AZUL PONTA MEDIA", "Caneta azul ponta 1.0mm"),
            "un", 1.3, (("UN", 1), ("CX C/ 50", 50))),
    # distractors: share vocabulary with the products above, are not them
    Product("mesa_computador", ("Mesa para computador 120x60cm", "MESA P/ COMPUTADOR C/ SUPORTE TECLADO", "Mesa de escritório para computador"),
            "un", 520, (("UN", 1),)),
    Product("suporte_notebook", ("Suporte para notebook ajustável em alumínio", "SUPORTE P/ NOTEBOOK REGULAVEL", "Base refrigerada para notebook"),
            "un", 115, (("UN", 1),)),
    Product("mochila_notebook", ("Mochila para notebook 15,6 polegadas", "CAPA P/ NOTEBOOK 15.6", "Mochila executiva para notebook"),
            "un", 140, (("UN", 1),)),
    Product("mousepad", ("Mouse pad com apoio de pulso", "MOUSEPAD ERGONOMICO GEL", "Mouse pad tecido 22x18cm"),
            "un", 24, (("UN", 1),)),
    Product("filtro_cafe", ("Filtro de papel para café 103", "FILTRO P/ CAFE N 103 C/ 30", "Coador de papel para café"),
            "un", 0.19, (("CX C/ 30", 30),)),
)

AGENCIES = ["Prefeitura de Vila Aurora", "Prefeitura de Serra Clara", "Secretaria de Saúde de Porto Lume",
            "Universidade Estadual de Campo Novo", "Instituto de Pesquisa Rio Ametista", "Câmara de Lagoa Prata",
            "Prefeitura de Alto Cedro", "Tribunal Regional Bela Brisa", "Secretaria de Educação de Monte Ônix"]
SUPPLIERS = ["Atlas Comércio Ltda", "Boreal Distribuidora", "Cobalto Suprimentos ME", "Delta Office S.A.",
             "Equinócio Tecnologia", "Faro Papelaria Ltda", "Granito Informática", "Horizonte Atacadista"]
STATES = ["MS", "MT", "GO", "SP", "PR", "BA", "PE", "MG", "RS", "AM"]


def _noisy(name: str, rng: random.Random) -> str:
    r = rng.random()
    if r < 0.25:
        name = name.upper()
    elif r < 0.35:
        name = name.lower()
    if rng.random() < 0.08:     # one-character typo
        i = rng.randrange(1, max(2, len(name) - 1))
        name = name[:i] + name[i + 1:]
    if rng.random() < 0.3:
        name += rng.choice([" - marca de referência ou similar", ", garantia 12 meses", " conforme termo de referência",
                            " (item 3 do lote)", ""])
    return name


@lru_cache(maxsize=1)
def records() -> tuple[dict, ...]:
    rng = random.Random(20261028)
    weights = [9, 6, 6, 6, 5, 8, 7, 5, 5, 5, 4, 5, 4, 3, 3, 3, 3]
    out = []
    for i in range(3200):
        p = rng.choices(CATALOG, weights=weights)[0]
        label, factor = rng.choice(p.packages)
        regional = {"AM": 1.18, "PE": 1.04, "BA": 1.03, "SP": 0.97}.get(state := rng.choice(STATES), 1.0)
        true_package_price = p.base_price * factor * regional
        price = true_package_price * rng.lognormvariate(0, 0.14)
        error = None
        if rng.random() < 0.03:
            error = rng.choice(["x10", "div10", "package_as_unit"])
            price = price * 10 if error == "x10" else price / 10 if error == "div10" else price * rng.choice([10, 12, 24])
        out.append({
            "id": f"P{100000 + i}",
            "description": _noisy(rng.choice(p.names), rng),
            "package": label,
            "quantity": rng.choice([1, 2, 5, 10, 20, 50, 100, 200]),
            "unit_price": round(price, 2),
            "agency": rng.choice(AGENCIES),
            "supplier": rng.choice(SUPPLIERS),
            "state": state,
            "date": (date(2025, 1, 1) + timedelta(days=rng.randint(0, 640))).isoformat(),
            # ground truth — never used by the pipeline, only by evaluation
            "_category": p.category,
            "_true_base_price": round(p.base_price * regional, 4),
            "_entry_error": error,
        })
    return tuple(out)


def public(record: dict) -> dict:
    """The record as an API returns it: ground-truth fields stripped."""
    return {k: v for k, v in record.items() if not k.startswith("_")}


def product(category: str) -> Product:
    return next(p for p in CATALOG if p.category == category)


def as_dict(p: Product) -> dict:
    return asdict(p)
