from pathlib import Path

import networkx as nx
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

NODES_PATH = PROJECT_ROOT / "data" / "processed" / "nodes.csv"
EDGES_PATH = PROJECT_ROOT / "data" / "processed" / "edges.csv"


def load_graph_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Загружает подготовленные узлы и рёбра."""

    nodes = pd.read_csv(NODES_PATH)
    edges = pd.read_csv(EDGES_PATH)

    return nodes, edges


def build_graph(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> nx.DiGraph:
    """
    Строит ориентированный граф терминосистемы.

    Направление ребра:
        дочерний термин -> родительский термин

    Например:
        Массовый спорт -> Спорт
    """

    graph = nx.DiGraph()

    # Добавляем узлы
    for _, row in nodes.iterrows():
        graph.add_node(
            row["node_id"],
            label=row["label"],
            origin=row["origin"],
            meta_class_l1=row["meta_class_l1"],
            functional_class_l2=row["functional_class_l2"],
            criterion=row["criterion"],
            defect_note=row["defect_note"],
        )

    # Добавляем рёбра
    for _, row in edges.iterrows():
        graph.add_edge(
            row["source_id"],
            row["target_id"],
            relation=row["relation"],
        )

    return graph


def print_graph_info(graph: nx.DiGraph) -> None:
    """Выводит базовую статистику графа."""

    print("=" * 60)
    print("AS-IS ONTOLOGY GRAPH")
    print("=" * 60)

    print(f"\nКоличество узлов: {graph.number_of_nodes()}")
    print(f"Количество рёбер: {graph.number_of_edges()}")

    statutory_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if data["origin"] == "statutory"
    ]

    helper_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if data["origin"] == "helper"
    ]

    print(f"Термины статьи: {len(statutory_nodes)}")
    print(f"Вспомогательные узлы: {len(helper_nodes)}")

    relation_counts = {}

    for _, _, data in graph.edges(data=True):
        relation = data["relation"]

        relation_counts[relation] = (
            relation_counts.get(relation, 0) + 1
        )

    print("\nТипы рёбер:")

    for relation, count in sorted(
        relation_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(f"  {relation}: {count}")


def find_top_parents(
    graph: nx.DiGraph,
    limit: int = 10,
) -> None:
    """
    Показывает узлы, к которым относится больше всего других узлов.

    Поскольку направление child -> parent,
    количество детей определяется через in_degree.
    """

    ranking = sorted(
        graph.in_degree(),
        key=lambda item: item[1],
        reverse=True,
    )

    print("\n" + "=" * 60)
    print("НАИБОЛЕЕ НАГРУЖЕННЫЕ РОДИТЕЛЬСКИЕ УЗЛЫ")
    print("=" * 60)

    for node_id, child_count in ranking[:limit]:
        label = graph.nodes[node_id]["label"]

        print(
            f"{label}: "
            f"{child_count} непосредственных потомков"
        )


def find_graph_components(graph: nx.DiGraph) -> None:
    """
    Анализирует слабосвязные компоненты графа.
    """

    components = list(
        nx.weakly_connected_components(graph)
    )

    components.sort(
        key=len,
        reverse=True,
    )

    print("\n" + "=" * 60)
    print("КОМПОНЕНТЫ ГРАФА")
    print("=" * 60)

    print(
        f"\nКоличество слабосвязных компонентов: "
        f"{len(components)}"
    )

    for index, component in enumerate(
        components,
        start=1,
    ):
        labels = sorted(
            graph.nodes[node]["label"]
            for node in component
        )

        print(
            f"\nКомпонента {index}: "
            f"{len(component)} узлов"
        )

        # Не выводим огромные компоненты полностью
        for label in labels[:10]:
            print(f"  - {label}")

        if len(labels) > 10:
            print(
                f"  ... ещё {len(labels) - 10}"
            )


def main() -> None:
    nodes, edges = load_graph_data()

    graph = build_graph(
        nodes,
        edges,
    )

    print_graph_info(graph)
    find_top_parents(graph)
    find_graph_components(graph)


if __name__ == "__main__":
    main()