from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable

type PairKey = tuple[str, str]

@dataclass
class MatchResult:
    vertex_a: object
    vertex_b: object
    score: float
    initial_score: float


@dataclass
class _Edge:
    source_id: str
    target_id: str
    label: str


@dataclass
class _Graph:
    vertices: dict[str, object] = field(default_factory=dict)
    edges: list[_Edge] = field(default_factory=list)

    def out_edges(self, vertex_id: str) -> list[_Edge]:
        return [e for e in self.edges if e.source_id == vertex_id]

    def in_edges(self, vertex_id: str) -> list[_Edge]:
        return [e for e in self.edges if e.target_id == vertex_id]


@dataclass
class _PCGEdge:
    from_pair: PairKey
    to_pair: PairKey

# Шаг 1. Загрузка онтологии из at_ontology_parser
def _default_vertex_filter(vertex: object) -> bool:

    return True


def _get_rel_label(relationship: object) -> str:

    rel_type = getattr(relationship, 'type', None)
    if rel_type is None:
        return 'unknown'
    if hasattr(rel_type, 'alias'):
        return rel_type.alias.rsplit('.', 1)[-1]
    if hasattr(rel_type, 'name'):
        return rel_type.name
    return 'unknown'


def _get_vertex_from_rel_end(rel_end: object) -> object | None:
    if hasattr(rel_end, 'value'):
        return rel_end.value
    return rel_end


def _load_graph(
    ontology: object,
    vertex_filter: Callable[[object], bool] | None = None,
) -> _Graph:
    if vertex_filter is None:
        vertex_filter = _default_vertex_filter

    g = _Graph()

    for name, vertex in ontology.vertices.items():
        if vertex_filter(vertex):
            g.vertices[name] = vertex

    for _rel_name, rel in ontology.relationships.items():
        try:
            src = _get_vertex_from_rel_end(rel.source)
            tgt = _get_vertex_from_rel_end(rel.target)
        except AttributeError:
            continue

        if src is None or tgt is None:
            continue
        if not vertex_filter(src) or not vertex_filter(tgt):
            continue

        g.edges.append(_Edge(
            source_id=src.name,
            target_id=tgt.name,
            label=_get_rel_label(rel),
        ))

    return g


# Шаг 2. Начальная схожесть σ₀ по именам и свойствам
def _levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n

    prev = list(range(m + 1))
    for i, ch_a in enumerate(a, 1):
        curr = [i] + [0] * m
        for j, ch_b in enumerate(b, 1):
            if ch_a == ch_b:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev = curr

    return prev[m]


def _string_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a, b = a.lower(), b.lower()
    if a == b:
        return 1.0
    return 1.0 - _levenshtein(a, b) / max(len(a), len(b))


def _label_sim(v_a: object, v_b: object) -> float:
    name_score = _string_sim(v_a.name, v_b.name)

    label_a = getattr(v_a, 'label', None) or v_a.name
    label_b = getattr(v_b, 'label', None) or v_b.name
    label_score = _string_sim(label_a, label_b)

    return 0.35 * name_score + 0.65 * label_score


def _get_property_names(vertex: object) -> set[str]:
    props = getattr(vertex, 'properties', None)
    if props is None:
        return set()

    if isinstance(props, dict):
        return set(props.keys())

    try:
        return {pa.definition.name for pa in props.select_related('definition').all()}
    except Exception:
        pass

    try:
        return {pa.definition.name for pa in props}
    except Exception:
        return set()


def _property_sim(v_a: object, v_b: object) -> float:
    props_a = _get_property_names(v_a)
    props_b = _get_property_names(v_b)

    if not props_a or not props_b:
        return 0.0

    return len(props_a & props_b) / len(props_a | props_b)


def _initial_sigma(v_a: object, v_b: object) -> float:
    return 0.80 * _label_sim(v_a, v_b) + 0.20 * _property_sim(v_a, v_b)

# Шаг 3. Построение графа попарных совпадений (PCG)
def _build_pcg(graph_a: _Graph, graph_b: _Graph) -> list[_PCGEdge]:
    edges_b_by_label: dict[str, list[_Edge]] = defaultdict(list)
    for e in graph_b.edges:
        edges_b_by_label[e.label].append(e)

    pcg_edges: list[_PCGEdge] = []
    for e_a in graph_a.edges:
        for e_b in edges_b_by_label.get(e_a.label, []):
            pcg_edges.append(_PCGEdge(
                from_pair=(e_a.source_id, e_b.source_id),
                to_pair=(e_a.target_id, e_b.target_id),
            ))

    return pcg_edges

# Шаг 4. Итерации Similarity Flooding
def _flood(
    sigma: dict[PairKey, float],
    pcg_edges: list[_PCGEdge],
    graph_a: _Graph,
    graph_b: _Graph,
    iterations: int = 10,
    convergence_threshold: float = 1e-4,
) -> dict[PairKey, float]:
    if not pcg_edges:
        print('  PCG пуст — итерации не нужны, используем σ₀')
        return sigma

    out_degree_a = {
        vid: max(len(graph_a.out_edges(vid)), 1)
        for vid in graph_a.vertices
    }
    out_degree_b = {
        vid: max(len(graph_b.out_edges(vid)), 1)
        for vid in graph_b.vertices
    }

    # Индекс: целевая пара → список исходных пар
    incoming: dict[PairKey, list[PairKey]] = defaultdict(list)
    for e in pcg_edges:
        incoming[e.to_pair].append(e.from_pair)

    current = dict(sigma)

    for iteration in range(iterations):
        new_sigma = dict(current)
        delta_total = 0.0

        for pair, sources in incoming.items():
            increment = sum(
                current.get(src, 0.0)
                / out_degree_a.get(src[0], 1)
                / out_degree_b.get(src[1], 1)
                for src in sources
            )
            prev = current.get(pair, 0.0)
            new_sigma[pair] = prev + increment
            delta_total += abs(new_sigma[pair] - prev)

        current = new_sigma

        if delta_total < convergence_threshold:
            print(f'  Сошлось за {iteration + 1} итераций (Δ={delta_total:.6f})')
            break
    else:
        print(f'  Достигнут лимит {iterations} итераций')

    return current

# Шаг 5. Нормализация и фильтрация
def _normalize(sigma: dict[PairKey, float]) -> dict[PairKey, float]:
    if not sigma:
        return sigma
    max_val = max(sigma.values())
    if max_val == 0:
        return sigma
    return {k: v / max_val for k, v in sigma.items()}


def _filter_one_to_one(
    sigma: dict[PairKey, float],
    graph_a: _Graph,
    graph_b: _Graph,
) -> list[tuple[PairKey, float]]:
    sorted_pairs = sorted(sigma.items(), key=lambda x: -x[1])

    used_a: set[str] = set()
    used_b: set[str] = set()
    result: list[tuple[PairKey, float]] = []

    for (vid_a, vid_b), score in sorted_pairs:
        if vid_a not in graph_a.vertices or vid_b not in graph_b.vertices:
            continue
        if vid_a in used_a or vid_b in used_b:
            continue
        used_a.add(vid_a)
        used_b.add(vid_b)
        result.append(((vid_a, vid_b), score))

    return result


class OntologySimilarityMatcher:
    def __init__(
        self,
        ontology_a: object,
        ontology_b: object,
        iterations: int = 20,
        min_score: float = 0.05,
        vertex_filter: Callable[[object], bool] | None = None,
    ) -> None:
        self.ontology_a = ontology_a
        self.ontology_b = ontology_b
        self.iterations = iterations
        self.min_score = min_score
        self.vertex_filter = vertex_filter

    def run(self, top_k: int | None = None) -> list[MatchResult]:
        print(f'Загружаем онтологию «{self.ontology_a}»...')
        graph_a = _load_graph(self.ontology_a, self.vertex_filter)
        print(f'  {len(graph_a.vertices)} вершин, {len(graph_a.edges)} рёбер')

        print(f'Загружаем онтологию «{self.ontology_b}»...')
        graph_b = _load_graph(self.ontology_b, self.vertex_filter)
        print(f'  {len(graph_b.vertices)} вершин, {len(graph_b.edges)} рёбер')

        if not graph_a.vertices or not graph_b.vertices:
            print('Одна из онтологий пуста — совпадений нет.')
            return []

        print('Строим начальную σ₀...')
        sigma: dict[PairKey, float] = {}
        initial: dict[PairKey, float] = {}

        for vid_a, v_a in graph_a.vertices.items():
            for vid_b, v_b in graph_b.vertices.items():
                s = _initial_sigma(v_a, v_b)
                if s > 0:
                    sigma[(vid_a, vid_b)] = s
                    initial[(vid_a, vid_b)] = s

        print(f'  {len(sigma)} пар с σ₀ > 0')

        print('Строим PCG...')
        pcg_edges = _build_pcg(graph_a, graph_b)
        print(f'  {len(pcg_edges)} рёбер в PCG')

        print('Запускаем итерации Similarity Flooding...')
        sigma = _flood(sigma, pcg_edges, graph_a, graph_b, self.iterations)

        print('Нормализуем σ...')
        sigma = _normalize(sigma)

        print('Фильтруем (один к одному)...')
        filtered = _filter_one_to_one(sigma, graph_a, graph_b)

        results = [
            MatchResult(
                vertex_a=graph_a.vertices[vid_a],
                vertex_b=graph_b.vertices[vid_b],
                score=score,
                initial_score=initial.get((vid_a, vid_b), 0.0),
            )
            for (vid_a, vid_b), score in filtered
            if score >= self.min_score
        ]

        results.sort(key=lambda r: -r.score)
        if top_k is not None:
            results = results[:top_k]

        print(f'Готово. Найдено {len(results)} соответствий.')
        return results


# Красивый вывод результатов
def print_results(results: list[MatchResult], show_initial: bool = False) -> None:
    print()
    header = f"{'Вершина A':<30} {'Вершина B':<30} {'σ (итог)':>10}"
    if show_initial:
        header += f"  {'σ₀ (имена)':>10}"
    print(header)
    print('-' * len(header))

    for r in results:
        name_a = (getattr(r.vertex_a, 'label', None) or r.vertex_a.name)[:28]
        name_b = (getattr(r.vertex_b, 'label', None) or r.vertex_b.name)[:28]
        bar = '█' * int(r.score * 20)
        line = f'{name_a:<30} {name_b:<30} {r.score:>9.3f}'
        if show_initial:
            line += f'  {r.initial_score:>9.3f}'
        print(f'{line}  {bar}')