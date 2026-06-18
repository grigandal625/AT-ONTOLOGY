from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable

# ─────────────────────────────────────────────────────────────────────────────
# Типы
# ─────────────────────────────────────────────────────────────────────────────

type PairKey = tuple[str, str]


# ─────────────────────────────────────────────────────────────────────────────
# Структуры данных
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatchResult:
    vertex_a: object
    vertex_b: object
    score: float        # итоговая σ [0..1]
    initial_score: float  # σ₀ до итераций


@dataclass
class _Edge:
    source_id: str
    target_id: str
    label: str


@dataclass
class _Graph:
    """
    Граф онтологии с O(1)-индексами рёбер.
    Без индексов out_edges давал O(n) на каждый вызов,
    что при 195 вершинах × 500 рёбер × 20 итераций приводило к зависанию.
    """
    vertices: dict[str, object] = field(default_factory=dict)
    edges: list[_Edge] = field(default_factory=list)
    _out_index: dict[str, list[_Edge]] = field(default_factory=dict, repr=False)
    _in_index:  dict[str, list[_Edge]] = field(default_factory=dict, repr=False)

    def _build_indices(self) -> None:
        if self._out_index:
            return
        for vid in self.vertices:
            self._out_index[vid] = []
            self._in_index[vid]  = []
        for e in self.edges:
            if e.source_id in self._out_index:
                self._out_index[e.source_id].append(e)
            if e.target_id in self._in_index:
                self._in_index[e.target_id].append(e)

    def out_edges(self, vertex_id: str) -> list[_Edge]:
        self._build_indices()
        return self._out_index.get(vertex_id, [])

    def in_edges(self, vertex_id: str) -> list[_Edge]:
        self._build_indices()
        return self._in_index.get(vertex_id, [])


@dataclass
class _PCGEdge:
    from_pair: PairKey
    to_pair: PairKey


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 1. Загрузка графа из at_ontology_parser
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 2. Начальная схожесть σ⁰
# ─────────────────────────────────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)
    if n == 0: return m
    if m == 0: return n
    prev = list(range(m + 1))
    for i, ch_a in enumerate(a, 1):
        curr = [i] + [0] * m
        for j, ch_b in enumerate(b, 1):
            curr[j] = prev[j-1] if ch_a == ch_b else 1 + min(prev[j], curr[j-1], prev[j-1])
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
    """
    Схожесть по name (системный slug) и label (человеческое название).
    Label весит больше — он несёт смысловую нагрузку.
    """
    name_score  = _string_sim(v_a.name, v_b.name)
    label_a = getattr(v_a, 'label', None) or v_a.name
    label_b = getattr(v_b, 'label', None) or v_b.name
    label_score = _string_sim(label_a, label_b)
    return 0.2 * name_score + 0.8 * label_score


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
    """
    σ⁰ = 0.85 · label_sim + 0.15 · property_sim
    Текстовая составляющая доминирует — структура лишь корректирует.
    """
    return 0.85 * _label_sim(v_a, v_b) + 0.15 * _property_sim(v_a, v_b)


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 3. Граф попарной связности (PCG)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 4. Итерации Similarity Flooding — формула C из Melnik et al.
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_dict(d: dict[PairKey, float]) -> dict[PairKey, float]:
    """Делим все значения на максимум → диапазон [0..1]."""
    if not d:
        return d
    max_val = max(d.values())
    if max_val == 0:
        return d
    return {k: v / max_val for k, v in d.items()}


def _flood(
    sigma0: dict[PairKey, float],
    pcg_edges: list[_PCGEdge],
    graph_a: _Graph,
    graph_b: _Graph,
    iterations: int = 20,
    convergence_threshold: float = 1e-4,
) -> dict[PairKey, float]:
    """
    Формула C из Melnik et al. 2002:
        σⁱ⁺¹ = normalize(σ⁰ + σⁱ + φ(σ⁰ + σⁱ))

    Ключевое отличие от «Basic»:
    — σ⁰ прибавляется на КАЖДОЙ итерации, не только в начале.
    — Это не даёт структурным связям полностью задавить текстовую схожесть.
    — Нормализация после каждой итерации держит значения в [0..1].
    """
    if not pcg_edges:
        print('  PCG пуст — итерации не нужны, используем σ⁰')
        return dict(sigma0)

    # Строим индексы один раз
    graph_a._build_indices()
    graph_b._build_indices()

    out_degree_a = {
        vid: max(len(graph_a._out_index.get(vid, [])), 1)
        for vid in graph_a.vertices
    }
    out_degree_b = {
        vid: max(len(graph_b._out_index.get(vid, [])), 1)
        for vid in graph_b.vertices
    }

    # Предвычисляем веса рёбер PCG один раз
    incoming: dict[PairKey, list[tuple[PairKey, float]]] = defaultdict(list)
    for e in pcg_edges:
        src_a, src_b = e.from_pair
        w = 1.0 / (out_degree_a.get(src_a, 1) * out_degree_b.get(src_b, 1))
        incoming[e.to_pair].append((e.from_pair, w))

    current = _normalize_dict(dict(sigma0))

    for iteration in range(iterations):
        # φ(current): распространение через PCG
        increments: dict[PairKey, float] = {}
        for pair, sources in incoming.items():
            inc = sum(current.get(src, 0.0) * w for src, w in sources)
            if inc > 0:
                increments[pair] = inc

        # Формула C: σ⁰ + σⁱ + φ(σⁱ) — всё суммируем
        combined: dict[PairKey, float] = dict(sigma0)
        for pair, val in current.items():
            combined[pair] = combined.get(pair, 0.0) + val
        for pair, inc in increments.items():
            combined[pair] = combined.get(pair, 0.0) + inc

        new_sigma = _normalize_dict(combined)

        # Проверка сходимости
        delta = sum(
            abs(new_sigma.get(p, 0.0) - current.get(p, 0.0))
            for p in set(new_sigma) | set(current)
        )
        current = new_sigma

        print(f'  Итерация {iteration + 1:2d}: Δ={delta:.6f}')
        if delta < convergence_threshold:
            print(f'  Сошлось за {iteration + 1} итераций')
            break
    else:
        print(f'  Достигнут лимит {iterations} итераций')

    return current


# ─────────────────────────────────────────────────────────────────────────────
# Шаг 5. Фильтрация: один к одному
# ─────────────────────────────────────────────────────────────────────────────

def _filter_one_to_one(
    sigma: dict[PairKey, float],
    graph_a: _Graph,
    graph_b: _Graph,
) -> list[tuple[PairKey, float]]:
    """
    Жадный алгоритм «устойчивого паросочетания»:
    берём пары по убыванию σ, каждую вершину используем не более одного раза.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# Публичный класс
# ─────────────────────────────────────────────────────────────────────────────

class OntologySimilarityMatcher:
    """
    Сопоставление двух онтологий алгоритмом Similarity Flooding
    (формула C, Melnik et al. 2002).

    Параметры
    ---------
    ontology_a, ontology_b : объекты Ontology из at_ontology_parser
    iterations             : макс. итераций (по умолчанию 20)
    min_score              : порог отсечения (по умолчанию 0.05)
    vertex_filter          : (vertex) -> bool
                             Для реальных онтологий:
                               lambda v: v.name.startswith("Topic_")
    """

    def __init__(
        self,
        ontology_a: object,
        ontology_b: object,
        iterations: int = 20,
        min_score: float = 0.05,
        vertex_filter: Callable[[object], bool] | None = None,
    ) -> None:
        self.ontology_a    = ontology_a
        self.ontology_b    = ontology_b
        self.iterations    = iterations
        self.min_score     = min_score
        self.vertex_filter = vertex_filter

    def run(self, top_k: int | None = None) -> list[MatchResult]:
        print(f'Загружаем граф A...')
        graph_a = _load_graph(self.ontology_a, self.vertex_filter)
        print(f'  {len(graph_a.vertices)} вершин, {len(graph_a.edges)} рёбер')

        print(f'Загружаем граф B...')
        graph_b = _load_graph(self.ontology_b, self.vertex_filter)
        print(f'  {len(graph_b.vertices)} вершин, {len(graph_b.edges)} рёбер')

        if not graph_a.vertices or not graph_b.vertices:
            print('Одна из онтологий пуста.')
            return []

        print('Строим σ⁰...')
        sigma0: dict[PairKey, float] = {}
        for vid_a, v_a in graph_a.vertices.items():
            for vid_b, v_b in graph_b.vertices.items():
                s = _initial_sigma(v_a, v_b)
                if s > 0:
                    sigma0[(vid_a, vid_b)] = s
        print(f'  {len(sigma0)} пар с σ⁰ > 0')

        print('Строим PCG...')
        pcg_edges = _build_pcg(graph_a, graph_b)
        print(f'  {len(pcg_edges)} рёбер в PCG')

        print('Итерации SF (формула C)...')
        sigma = _flood(sigma0, pcg_edges, graph_a, graph_b, self.iterations)

        print('Фильтрация (один к одному)...')
        filtered = _filter_one_to_one(sigma, graph_a, graph_b)

        results = [
            MatchResult(
                vertex_a=graph_a.vertices[vid_a],
                vertex_b=graph_b.vertices[vid_b],
                score=score,
                initial_score=sigma0.get((vid_a, vid_b), 0.0),
            )
            for (vid_a, vid_b), score in filtered
            if score >= self.min_score
        ]

        results.sort(key=lambda r: -r.score)
        if top_k is not None:
            results = results[:top_k]

        print(f'Готово. Найдено {len(results)} соответствий.')
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Утилита вывода
# ─────────────────────────────────────────────────────────────────────────────

def print_results(results: list[MatchResult], show_initial: bool = False) -> None:
    print()
    header = f"{'Вершина A':<32} {'Вершина B':<32} {'σ':>7}"
    if show_initial:
        header += f"  {'σ⁰':>7}"
    print(header)
    print('-' * len(header))

    for r in results:
        name_a = (getattr(r.vertex_a, 'label', None) or r.vertex_a.name)[:30]
        name_b = (getattr(r.vertex_b, 'label', None) or r.vertex_b.name)[:30]
        bar  = '█' * int(r.score * 20)
        line = f'{name_a:<32} {name_b:<32} {r.score:>6.3f}'
        if show_initial:
            line += f'  {r.initial_score:>6.3f}'
        print(f'{line}  {bar}')