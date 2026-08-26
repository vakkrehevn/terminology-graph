from pathlib import Path

import networkx as nx
import pandas as pd

from src.graph_builder import (
    build_graph,
    load_graph_data,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFECTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "structural_defects.csv"
)


def make_issue(
    code: str,
    issue_type: str,
    severity: str,
    node: str,
    description: str,
    status: str = "candidate",
) -> dict:
    """
    Создаёт единый объект диагностического сообщения.

    status:
        defect     — формальное противоречие;
        candidate  — структурный признак, требующий интерпретации.
    """

    return {
        "code": code,
        "type": issue_type,
        "severity": severity,
        "status": status,
        "node": node,
        "description": description,
    }


def detect_cycles(graph: nx.DiGraph) -> list[dict]:
    """
    Ищет циклы непосредственно в графе отношений.
    """

    issues = []

    cycles = list(nx.simple_cycles(graph))

    for index, cycle in enumerate(cycles, start=1):

        labels = [
            graph.nodes[node]["label"]
            for node in cycle
        ]

        cycle_text = " -> ".join(labels + [labels[0]])

        issues.append(
            make_issue(
                code=f"STR-CYCLE-{index:03d}",
                issue_type="GRAPH_CYCLE",
                severity="HIGH",
                node=labels[0],
                status="defect",
                description=(
                    "Обнаружен цикл отношений: "
                    f"{cycle_text}"
                ),
            )
        )

    return issues


def detect_isolated_nodes(
    graph: nx.DiGraph,
) -> list[dict]:

    issues = []

    isolated = list(nx.isolates(graph))

    for index, node in enumerate(
        isolated,
        start=1,
    ):
        label = graph.nodes[node]["label"]

        issues.append(
            make_issue(
                code=f"STR-ISOLATED-{index:03d}",
                issue_type="ISOLATED_NODE",
                severity="MEDIUM",
                node=label,
                description=(
                    "Узел не связан ни с одним другим "
                    "понятием графа."
                ),
            )
        )

    return issues


def detect_root_with_parent(
    graph: nx.DiGraph,
) -> list[dict]:
    """
    Если узел помечен отношением Root,
    но при этом имеет родителя, это формальное
    противоречие текущей модели.
    """

    issues = []
    counter = 1

    for source, target, data in graph.edges(data=True):

        if data["relation"] != "Root":
            continue

        source_label = graph.nodes[source]["label"]
        target_label = graph.nodes[target]["label"]

        issues.append(
            make_issue(
                code=f"STR-ROOT-{counter:03d}",
                issue_type="ROOT_WITH_PARENT",
                severity="HIGH",
                node=source_label,
                status="defect",
                description=(
                    f"Узел '{source_label}' имеет тип связи "
                    f"Root, но одновременно связан с родителем "
                    f"'{target_label}'."
                ),
            )
        )

        counter += 1

    return issues


def detect_disconnected_structure(
    graph: nx.DiGraph,
) -> list[dict]:
    """
    Проверяет связность всей терминосистемы.

    Несвязность сама по себе пока рассматривается
    как кандидат на дефект.
    """

    components = list(
        nx.weakly_connected_components(graph)
    )

    if len(components) <= 1:
        return []

    sizes = sorted(
        [len(component) for component in components],
        reverse=True,
    )

    return [
        make_issue(
            code="STR-COMP-001",
            issue_type="DISCONNECTED_STRUCTURE",
            severity="MEDIUM",
            node="ONTOLOGY",
            status="candidate",
            description=(
                "Терминосистема состоит из "
                f"{len(components)} слабосвязных компонент. "
                f"Размеры компонент: {sizes}."
            ),
        )
    ]


def detect_overloaded_parents(
    graph: nx.DiGraph,
    threshold: int = 5,
) -> list[dict]:
    """
    Ищет узлы с большим количеством непосредственных детей.

    threshold — эвристический порог, а не универсальный закон.
    """

    issues = []
    counter = 1

    for node, child_count in graph.in_degree():

        if child_count < threshold:
            continue

        label = graph.nodes[node]["label"]

        issues.append(
            make_issue(
                code=f"STR-HUB-{counter:03d}",
                issue_type="OVERLOADED_PARENT",
                severity="LOW",
                node=label,
                status="candidate",
                description=(
                    f"Узел имеет {child_count} "
                    "непосредственных потомков. "
                    f"Использован эвристический порог >= {threshold}."
                ),
            )
        )

        counter += 1

    return issues


def detect_mixed_relation_types(
    graph: nx.DiGraph,
) -> list[dict]:
    """
    Проверяет, используются ли для одного родительского
    узла несколько разных типов отношений.

    Например:

        X Is-A -> Спорт
        Y Part-Of -> Спорт
        Z Attribute -> Спорт

    Это не обязательно ошибка, но может показывать
    смешение разных уровней онтологического описания.
    """

    issues = []
    counter = 1

    for parent in graph.nodes():

        incoming_edges = graph.in_edges(
            parent,
            data=True,
        )

        relation_types = {
            data["relation"]
            for _, _, data in incoming_edges
        }

        if len(relation_types) <= 1:
            continue

        parent_label = graph.nodes[parent]["label"]

        relations = ", ".join(
            sorted(relation_types)
        )

        issues.append(
            make_issue(
                code=f"STR-MIXREL-{counter:03d}",
                issue_type="MIXED_RELATION_TYPES",
                severity="MEDIUM",
                node=parent_label,
                status="candidate",
                description=(
                    "Для потомков одного родительского узла "
                    "используются разные типы отношений: "
                    f"{relations}."
                ),
            )
        )

        counter += 1

    return issues


def run_structural_analysis(
    graph: nx.DiGraph,
) -> pd.DataFrame:

    issues = []

    issues.extend(
        detect_cycles(graph)
    )

    issues.extend(
        detect_isolated_nodes(graph)
    )

    issues.extend(
        detect_root_with_parent(graph)
    )

    issues.extend(
        detect_disconnected_structure(graph)
    )

    issues.extend(
        detect_overloaded_parents(graph)
    )

    issues.extend(
        detect_mixed_relation_types(graph)
    )

    return pd.DataFrame(issues)


def print_report(
    defects: pd.DataFrame,
) -> None:

    print("=" * 70)
    print("STRUCTURAL ANALYSIS")
    print("=" * 70)

    print(
        f"\nВсего диагностических сообщений: "
        f"{len(defects)}"
    )

    if defects.empty:
        print("\nСтруктурные проблемы не обнаружены.")
        return

    print("\nПо статусу:")
    print(
        defects["status"].value_counts()
    )

    print("\nПо типу:")
    print(
        defects["type"].value_counts()
    )

    print("\n" + "=" * 70)
    print("НАЙДЕННЫЕ ПРОБЛЕМЫ")
    print("=" * 70)

    for _, row in defects.iterrows():

        print(
            f"\n[{row['code']}] "
            f"{row['severity']} | "
            f"{row['status']}"
        )

        print(
            f"Тип: {row['type']}"
        )

        print(
            f"Узел: {row['node']}"
        )

        print(
            f"Описание: {row['description']}"
        )


def save_report(
    defects: pd.DataFrame,
) -> None:

    defects.to_csv(
        DEFECTS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"\nОтчёт сохранён:\n{DEFECTS_PATH}"
    )


def main() -> None:

    nodes, edges = load_graph_data()

    graph = build_graph(
        nodes,
        edges,
    )

    defects = run_structural_analysis(
        graph
    )

    print_report(
        defects
    )

    save_report(
        defects
    )


if __name__ == "__main__":
    main()