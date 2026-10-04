from pathlib import Path

import pandas as pd
from graphviz import Digraph

from src.loader import load_terminology


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "reports" / "figures"


# ============================================================
# СТИЛИ РЕАЛЬНЫХ СВЯЗЕЙ
# ============================================================

RELATION_STYLES = {
    "Is-A": {
        "style": "solid",
        "penwidth": "1.8",
        "color": "#1f4e79",      # синий
    },
    "Part-Of": {
        "style": "dashed",
        "penwidth": "1.6",
        "color": "#2e8b57",      # зелёный
    },
    "Role": {
        "style": "dotted",
        "penwidth": "1.5",
        "color": "#7a3db8",      # фиолетовый
    },
    "Attribute": {
        "style": "dashdot",
        "penwidth": "1.4",
        "color": "#c97a00",      # оранжевый
    },
}


# ============================================================
# РУЧНЫЕ ПРАВИЛА ТОЛЬКО ДЛЯ РАСКЛАДКИ
#
# Они НЕ создают новые понятия
# и НЕ меняют семантику графа.
# ============================================================

SAME_RANK_GROUPS = [
    [
        "Спортивная федерация",
        "Программа развития вида спорта",
    ],
]


# Для конкретных поперечных связей можем указать,
# откуда выходит и куда входит стрелка.
#
# e = east  (справа)
# w = west  (слева)
# n = north (сверху)
# s = south (снизу)

SPECIAL_EDGE_PORTS = {
    (
        "Спортивная федерация",
        "Программа развития вида спорта",
    ): {
        "tailport": "e",
        "headport": "w",
    },
}


def clean(value) -> str:
    """
    Преобразует NaN в пустую строку
    и убирает лишние пробелы.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def build_plain_graph(df: pd.DataFrame) -> Digraph:
    """
    Строит чистый AS-IS граф.

    ВАЖНО:
    1. Видимые узлы = только термины статьи.
    2. Никаких helper-узлов.
    3. Is-A и Part-Of формируют вертикальную структуру.
    4. Role и Attribute отображаются,
       но почти не влияют на раскладку.
    5. L1 используется только для невидимого
       позиционирования терминов,
       у которых нет реального родителя из статьи.
    """

    graph = Digraph(
        "terminology_plain",
        format="svg",
        engine="dot",
    )

    # ========================================================
    # ОБЩИЕ НАСТРОЙКИ
    # ========================================================

    graph.attr(
        rankdir="LR",
        splines="spline",
        overlap="false",
        concentrate="false",
        nodesep="0.25",
        ranksep="0.55",
        newrank="true",
        bgcolor="white",
        pad="0.15",
    )

    # ========================================================
    # СТИЛЬ УЗЛОВ
    # ========================================================

    graph.attr(
        "node",

        # Никаких прямоугольников.
        shape="plain",

        fontname="Arial",
        fontsize="10",
    )

    # ========================================================
    # СТИЛЬ СТРЕЛОК
    # ========================================================

    graph.attr(
        "edge",
        fontname="Arial",
        fontsize="8",
        arrowsize="0.75",
    )

    # ========================================================
    # СОБИРАЕМ ВСЕ 69 ТЕРМИНОВ
    # ========================================================

    terms = {
        clean(term)
        for term in df["Термин"]
        if clean(term)
    }

    # Graphviz удобнее работать с короткими ID,
    # а русское название используется как label.
    term_to_id = {
        term: f"T{index:03d}"
        for index, term in enumerate(
            sorted(terms),
            start=1,
        )
    }

    # ========================================================
    # 1. СОЗДАЁМ ТОЛЬКО РЕАЛЬНЫЕ ТЕРМИНЫ
    # ========================================================

    for _, row in df.iterrows():

        term = clean(row["Термин"])

        if not term:
            continue

        # Два главных понятия выделяем размером шрифта.
        if term in {
            "Спорт",
            "Физическая культура",
        }:

            graph.node(
                term_to_id[term],
                label=f"<<B>{term}</B>>",
                fontsize="15",
            )

        else:

            graph.node(
                term_to_id[term],
                label=term,
            )

    # ========================================================
    # 2. РУЧНЫЕ ПРАВИЛА РАСПОЛОЖЕНИЯ
    #
    # Например:
    #
    # Спортивная федерация   Программа развития вида спорта
    #
    # должны находиться примерно на одном уровне.
    # ========================================================

    for group in SAME_RANK_GROUPS:

        existing_terms = [
            term
            for term in group
            if term in terms
        ]

        if len(existing_terms) < 2:
            continue

        with graph.subgraph() as rank_group:

            rank_group.attr(
                rank="same"
            )

            for term in existing_terms:

                rank_group.node(
                    term_to_id[term]
                )

    # ========================================================
    # 3. ДОБАВЛЯЕМ РЕАЛЬНЫЕ СВЯЗИ ИЗ ТАБЛИЦЫ
    # ========================================================

    for _, row in df.iterrows():

        child = clean(
            row["Термин"]
        )

        parent = clean(
            row["Родительский узел"]
        )

        relation = clean(
            row["Тип связи"]
        )

        # --------------------------------------------
        # Пропускаем отсутствие родителя
        # --------------------------------------------

        if not parent:
            continue

        if parent in {
            "—",
            "-",
        }:
            continue

        # --------------------------------------------
        # Root не является обычным ребром
        # --------------------------------------------

        if relation == "Root":
            continue

        # --------------------------------------------
        # КЛЮЧЕВОЕ ПРАВИЛО:
        #
        # Если родителя нет среди 69 терминов статьи,
        # НОВЫЙ УЗЕЛ НЕ СОЗДАЁМ.
        # --------------------------------------------

        if parent not in terms:
            continue

        if child not in terms:
            continue

        # --------------------------------------------
        # Получаем визуальный стиль
        # --------------------------------------------

        style = RELATION_STYLES.get(
            relation,
            {
                "style": "solid",
                "penwidth": "1.0",
                "color": "#555555",
            },
        )

        # --------------------------------------------
        # Структурные связи формируют уровни.
        #
        # Role / Attribute должны быть видны,
        # но не должны разваливать всю раскладку.
        # --------------------------------------------

        is_structural = relation in {
            "Is-A",
            "Part-Of",
        }

        edge_attrs = {
            # Никаких надписей прямо на стрелках.
            # Тип определяется цветом + стилем.
            "label": "",

            "color": style["color"],
            "style": style["style"],
            "penwidth": style["penwidth"],

            "arrowhead": "normal",

            # Только структурные отношения
            # задают иерархические уровни.
            "constraint": (
                "true"
                if is_structural
                else "false"
            ),

            # Структурные связи сильнее влияют
            # на расположение.
            "weight": (
                "6"
                if is_structural
                else "1"
            ),
        }

        # --------------------------------------------
        # Специальные настройки отдельных стрелок
        # --------------------------------------------

        pair = (
            parent,
            child,
        )

        if pair in SPECIAL_EDGE_PORTS:

            edge_attrs.update(
                SPECIAL_EDGE_PORTS[pair]
            )

        # --------------------------------------------
        # Создаём ребро:
        #
        # parent -> child
        #
        # поэтому граф визуально читается сверху вниз.
        # --------------------------------------------

        graph.edge(
            term_to_id[parent],
            term_to_id[child],
            **edge_attrs,
        )

    # ========================================================
    # 4. НЕВИДИМЫЕ СВЯЗИ ТОЛЬКО ДЛЯ РАСКЛАДКИ
    #
    # Пример:
    #
    # Спортсмен
    # Родитель = "Физические лица"
    #
    # Но "Физические лица" НЕ термин статьи.
    #
    # Поэтому такого видимого узла нет.
    #
    # Однако через L1 мы можем сказать Graphviz:
    #
    # "визуально помести Спортсмена
    # ниже области Спорт".
    #
    # Эта стрелка НЕ ВИДНА.
    # ========================================================

    for _, row in df.iterrows():

        child = clean(
            row["Термин"]
        )

        original_parent = clean(
            row["Родительский узел"]
        )

        l1 = clean(
            row["Мета-Класс (L1)"]
        )

        if not child:
            continue

        # Главные узлы сами наверху.
        if child in {
            "Спорт",
            "Физическая культура",
        }:
            continue

        # Если реальный родитель уже существует
        # среди терминов статьи —
        # невидимая связь не нужна.
        if original_parent in terms:
            continue

        # L1 должен сам быть реальным термином.
        if l1 not in terms:
            continue

        if child == l1:
            continue

        graph.edge(
            term_to_id[l1],
            term_to_id[child],

            # Абсолютно невидимая линия.
            style="invis",

            # Но Graphviz учитывает её
            # при вычислении уровней.
            constraint="true",

            # Вес небольшой —
            # реальные Is-A / Part-Of важнее.
            weight="2",
        )

    return graph


def main() -> None:

    df = load_terminology()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    graph = build_plain_graph(df)

    output_path = (
        OUTPUT_DIR
        / "as_is_terminology_graph_plain"
    )

    rendered = graph.render(
        filename=str(output_path),
        cleanup=True,
    )

    print("=" * 60)
    print("PLAIN AS-IS GRAPH GENERATED")
    print("=" * 60)

    print(
        f"\nТерминов: {len(df)}"
    )

    print(
        f"Файл: {rendered}"
    )


if __name__ == "__main__":
    main()