from __future__ import annotations
"""
ontology_intersection.py
────────────────────────
Компонент пересечения прикладных онтологий курсов/дисциплин.

Реализует алгоритм Similarity Flooding (формула C, Melnik et al. 2002)
с контекстным σ⁰ (label + родитель + дети).

Использование:
    from ontology_intersection import OntologyIntersection

    result = OntologyIntersection(ontology_a, ontology_b).run(top_k=20)
    for pair in result.pairs:
        print(pair.label_a, '<->', pair.label_b, pair.score)
"""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable


# ─── Типы ────────────────────────────────────────────────────────────────────

type PairKey = tuple[str, str]


# ─── Результат пересечения ────────────────────────────────────────────────────

@dataclass
class SimilarPair:
    """Пара схожих вершин из двух онтологий."""
    vertex_a: object          # вершина из O_i (первая онтология)
    vertex_b: object          # вершина из O_j (вторая онтология)
    score: float              # итоговая схожесть σ ∈ [0, 1]
    initial_score: float      # начальная схожесть σ⁰


@dataclass
class IntersectionResult:
    """Результат операции пересечения."""
    pairs: list[SimilarPair]
    ontology_a_name: str
    ontology_b_name: str

    def __len__(self) -> int:
        return len(self.pairs)


# ─── Внутренние структуры ────────────────────────────────────────────────────

@dataclass
class _Edge:
    source_id: str
    target_id: str
    label: str


@dataclass
class _Graph:
    vertices: dict[str, object] = field(default_factory=dict)
    edges: list[_Edge] = field(default_factory=list)
    _out_index: dict[str, list[_Edge]] = field(default_factory=dict, repr=False)
    _in_index:  dict[str, list[_Edge]] = field(default_factory=dict, repr=False)

    def build_indices(self) -> None:
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


@dataclass
class _PCGEdge:
    from_pair: PairKey
    to_pair: PairKey


# ─── Блок фильтрации вершин-тем ──────────────────────────────────────────────

def _is_topic(vertex: object) -> bool:
    """
    Блок фильтрации вершин-тем.
    Оставляем только Topic_* — компетенции исключаются автоматически.
    """
    return vertex.name.startswith('Topic_')


def _get_rel_label(rel: object) -> str:
    rel_type = getattr(rel, 'type', None)
    if rel_type is None:
        return 'unknown'
    if hasattr(rel_type, 'alias'):
        return rel_type.alias.rsplit('.', 1)[-1]
    if hasattr(rel_type, 'name'):
        return rel_type.name
    return 'unknown'


def _get_vertex_end(rel_end: object) -> object | None:
    if hasattr(rel_end, 'value'):
        return rel_end.value
    return rel_end


def _load_graph(ontology: object, vertex_filter: Callable) -> _Graph:
    """Блок загрузки онтологии в граф с применением фильтра вершин-тем."""
    g = _Graph()
    for name, vertex in ontology.vertices.items():
        if vertex_filter(vertex):
            g.vertices[name] = vertex

    for _rname, rel in ontology.relationships.items():
        try:
            src = _get_vertex_end(rel.source)
            tgt = _get_vertex_end(rel.target)
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


# ─── Вычисление схожести строк ────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)
    if n == 0: return m
    if m == 0: return n
    prev = list(range(m + 1))
    for i, ch_a in enumerate(a, 1):
        curr = [i] + [0] * m
        for j, ch_b in enumerate(b, 1):
            curr[j] = (prev[j-1] if ch_a == ch_b
                       else 1 + min(prev[j], curr[j-1], prev[j-1]))
        prev = curr
    return prev[m]


def _str_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    return 1.0 - _levenshtein(a, b) / max(len(a), len(b))


def _get_label(vertex: object) -> str:
    return (getattr(vertex, 'label', None) or vertex.name).strip()


# ─── Контекстное σ⁰ ──────────────────────────────────────────────────────────

def _get_parent_label(vid: str, graph: _Graph) -> str | None:
    """Возвращает label родительской вершины по Hierarchy-ребру."""
    for e in graph._in_index.get(vid, []):
        if e.label == 'Hierarchy':
            parent = graph.vertices.get(e.source_id)
            if parent:
                return _get_label(parent)
    return None


def _get_children_labels(vid: str, graph: _Graph) -> list[str]:
    """Возвращает labels дочерних вершин по Hierarchy-рёбрам."""
    result = []
    for e in graph._out_index.get(vid, []):
        if e.label == 'Hierarchy':
            child = graph.vertices.get(e.target_id)
            if child:
                result.append(_get_label(child))
    return result


def _children_sim(vid_a: str, vid_b: str,
                  graph_a: _Graph, graph_b: _Graph) -> float:
    """
    Схожесть множеств дочерних вершин.
    Для каждого ребёнка A ищем лучшее совпадение среди детей B.
    """
    ch_a = _get_children_labels(vid_a, graph_a)
    ch_b = _get_children_labels(vid_b, graph_b)

    if not ch_a and not ch_b:
        return 0.5   # оба листа — нейтрально
    if not ch_a or not ch_b:
        return 0.0   # разная глубина

    score_ab = sum(max(_str_sim(a, b) for b in ch_b) for a in ch_a) / len(ch_a)
    score_ba = sum(max(_str_sim(b, a) for a in ch_a) for b in ch_b) / len(ch_b)
    return (score_ab + score_ba) / 2.0


def _compute_sigma0(
    v_a: object, v_b: object,
    graph_a: _Graph, graph_b: _Graph,
) -> float:
    """
    Блок поиска общих вершин / начальная схожесть σ⁰.

    σ⁰ = 0.50 × sim(label_a, label_b)
       + 0.30 × sim(parent_a, parent_b)
       + 0.20 × children_sim(a, b)

    Контекст родителя разделяет одноимённые вершины под разными разделами.
    Контекст детей помогает найти семантически близкие вершины с разными именами.
    """
    self_sim = _str_sim(_get_label(v_a), _get_label(v_b))

    parent_a = _get_parent_label(v_a.name, graph_a)
    parent_b = _get_parent_label(v_b.name, graph_b)

    if parent_a and parent_b:
        par_sim = _str_sim(parent_a, parent_b)
    elif parent_a or parent_b:
        par_sim = 0.2   # один корневой — слабый сигнал
    else:
        par_sim = 0.5   # оба корневые — нейтрально

    child_sim = _children_sim(v_a.name, v_b.name, graph_a, graph_b)

    return 0.50 * self_sim + 0.30 * par_sim + 0.20 * child_sim


# ─── Граф попарной связности (PCG) ────────────────────────────────────────────

def _build_pcg(graph_a: _Graph, graph_b: _Graph) -> list[_PCGEdge]:
    """Строим PCG: ребро (u_a,u_b)→(v_a,v_b) если совпадают типы рёбер."""
    edges_b_by_label: dict[str, list[_Edge]] = defaultdict(list)
    for e in graph_b.edges:
        edges_b_by_label[e.label].append(e)

    pcg: list[_PCGEdge] = []
    for e_a in graph_a.edges:
        for e_b in edges_b_by_label.get(e_a.label, []):
            pcg.append(_PCGEdge(
                from_pair=(e_a.source_id, e_b.source_id),
                to_pair=(e_a.target_id, e_b.target_id),
            ))
    return pcg


# ─── Итерации Similarity Flooding (формула C) ────────────────────────────────

def _normalize(d: dict[PairKey, float]) -> dict[PairKey, float]:
    if not d:
        return d
    max_val = max(d.values())
    if max_val == 0:
        return d
    return {k: v / max_val for k, v in d.items()}


def _flood(
    sigma0: dict[PairKey, float],
    pcg: list[_PCGEdge],
    graph_a: _Graph,
    graph_b: _Graph,
    iterations: int,
    sf_weight: float,
    convergence_threshold: float,
    verbose: bool,
) -> dict[PairKey, float]:
    """
    Similarity Flooding, формула C:
        σⁱ⁺¹ = normalize(σ⁰ + sf_weight · φ(σⁱ))

    sf_weight ограничивает вклад структуры — текстовый σ⁰ остаётся доминирующим.
    """
    if not pcg:
        if verbose:
            print('  PCG пуст — используем σ⁰')
        return dict(sigma0)

    graph_a.build_indices()
    graph_b.build_indices()

    out_a = {vid: max(len(graph_a._out_index.get(vid, [])), 1)
             for vid in graph_a.vertices}
    out_b = {vid: max(len(graph_b._out_index.get(vid, [])), 1)
             for vid in graph_b.vertices}

    # Предвычисляем входящие рёбра PCG с весами (один раз)
    incoming: dict[PairKey, list[tuple[PairKey, float]]] = defaultdict(list)
    for e in pcg:
        sa, sb = e.from_pair
        w = 1.0 / (out_a.get(sa, 1) * out_b.get(sb, 1))
        incoming[e.to_pair].append((e.from_pair, w))

    current = _normalize(dict(sigma0))

    for it in range(iterations):
        increments: dict[PairKey, float] = {}
        for pair, sources in incoming.items():
            inc = sum(current.get(src, 0.0) * w for src, w in sources)
            if inc > 0:
                increments[pair] = inc

        combined: dict[PairKey, float] = dict(sigma0)
        for pair, inc in increments.items():
            combined[pair] = combined.get(pair, 0.0) + sf_weight * inc

        new_sigma = _normalize(combined)
        delta = sum(abs(new_sigma.get(p, 0.0) - current.get(p, 0.0))
                    for p in set(new_sigma) | set(current))
        current = new_sigma

        if verbose:
            print(f'  Итерация {it + 1:2d}: Δ={delta:.6f}')
        if delta < convergence_threshold:
            if verbose:
                print(f'  Сошлось за {it + 1} итераций')
            break
    else:
        if verbose:
            print(f'  Достигнут лимит {iterations} итераций')

    return current


# ─── Блок фильтра «один к одному» ────────────────────────────────────────────

def _filter_one_to_one(
    sigma: dict[PairKey, float],
    graph_a: _Graph,
    graph_b: _Graph,
    min_score: float,
) -> list[tuple[PairKey, float]]:
    """
    Жадное паросочетание: каждая вершина используется не более одного раза.
    Включает блок фильтра σ⁰ ≥ min_score.
    """
    sorted_pairs = sorted(sigma.items(), key=lambda x: -x[1])
    used_a: set[str] = set()
    used_b: set[str] = set()
    result: list[tuple[PairKey, float]] = []

    for (vid_a, vid_b), score in sorted_pairs:
        if score < min_score:
            break
        if (vid_a not in graph_a.vertices or
                vid_b not in graph_b.vertices):
            continue
        if vid_a in used_a or vid_b in used_b:
            continue
        used_a.add(vid_a)
        used_b.add(vid_b)
        result.append(((vid_a, vid_b), score))

    return result


# ─── Публичный класс ──────────────────────────────────────────────────────────

class OntologyIntersection:
    """
    Компонент пересечения прикладных онтологий курсов/дисциплин.

    Находит множество пар семантически схожих вершин-тем:
        Vc = {(v, w, σ) | v ∈ V₁Topic, w ∈ V₂Topic, σ ≥ min_score}

    Параметры
    ---------
    ontology_a    : первая онтология (O_i)
    ontology_b    : вторая онтология (O_j)
    iterations    : макс. итераций SF (по умолчанию 10)
    min_score     : порог отсечения σ (по умолчанию 0.10)
    sf_weight     : вес структурного распространения (по умолчанию 0.3)
    vertex_filter : фильтр вершин; по умолчанию только Topic_*
    verbose       : выводить прогресс итераций
    """

    def __init__(
        self,
        ontology_a: object,
        ontology_b: object,
        iterations: int = 10,
        min_score: float = 0.10,
        sf_weight: float = 0.3,
        vertex_filter: Callable[[object], bool] | None = None,
        verbose: bool = True,
    ) -> None:
        self.ontology_a    = ontology_a
        self.ontology_b    = ontology_b
        self.iterations    = iterations
        self.min_score     = min_score
        self.sf_weight     = sf_weight
        self.vertex_filter = vertex_filter if vertex_filter is not None else _is_topic
        self.verbose       = verbose

    def run(self, top_k: int | None = None) -> IntersectionResult:
        vb = self.verbose

        if vb: print('Блок загрузки онтологий...')
        graph_a = _load_graph(self.ontology_a, self.vertex_filter)
        graph_b = _load_graph(self.ontology_b, self.vertex_filter)
        if vb:
            print(f'  O_i: {len(graph_a.vertices)} вершин, {len(graph_a.edges)} рёбер')
            print(f'  O_j: {len(graph_b.vertices)} вершин, {len(graph_b.edges)} рёбер')

        if not graph_a.vertices or not graph_b.vertices:
            if vb: print('Одна из онтологий пуста.')
            return IntersectionResult(
                pairs=[],
                ontology_a_name=getattr(self.ontology_a, 'name', ''),
                ontology_b_name=getattr(self.ontology_b, 'name', ''),
            )

        # Строим индексы — нужны для контекстного σ⁰
        graph_a.build_indices()
        graph_b.build_indices()

        if vb: print('Блок поиска общих вершин: вычисляем σ⁰...')
        sigma0: dict[PairKey, float] = {}
        for vid_a, v_a in graph_a.vertices.items():
            for vid_b, v_b in graph_b.vertices.items():
                s = _compute_sigma0(v_a, v_b, graph_a, graph_b)
                if s > 0:
                    sigma0[(vid_a, vid_b)] = s
        if vb: print(f'  {len(sigma0)} пар с σ⁰ > 0')

        if vb: print('Строим PCG...')
        pcg = _build_pcg(graph_a, graph_b)
        if vb: print(f'  {len(pcg)} рёбер в PCG')

        if vb: print(f'Итерации SF (вес={self.sf_weight})...')
        sigma = _flood(
            sigma0, pcg, graph_a, graph_b,
            self.iterations, self.sf_weight,
            convergence_threshold=1e-4,
            verbose=vb,
        )

        if vb: print('Блок фильтра «один к одному»...')
        filtered = _filter_one_to_one(sigma, graph_a, graph_b, self.min_score)

        pairs = [
            SimilarPair(
                vertex_a=graph_a.vertices[vid_a],
                vertex_b=graph_b.vertices[vid_b],
                score=score,
                initial_score=sigma0.get((vid_a, vid_b), 0.0),
            )
            for (vid_a, vid_b), score in filtered
        ]
        pairs.sort(key=lambda p: -p.score)
        if top_k is not None:
            pairs = pairs[:top_k]

        if vb: print(f'Готово. Найдено {len(pairs)} подобных пар.')

        return IntersectionResult(
            pairs=pairs,
            ontology_a_name=getattr(self.ontology_a, 'name', ''),
            ontology_b_name=getattr(self.ontology_b, 'name', ''),
        )


# ─── Утилиты вывода ──────────────────────────────────────────────────────────

def print_intersection(result: IntersectionResult, show_initial: bool = True) -> None:
    """Красивый вывод результата пересечения."""
    print(f'\nПересечение: «{result.ontology_a_name}» ∩ «{result.ontology_b_name}»')
    print(f'Найдено {len(result.pairs)} подобных пар\n')

    header = f"{'Вершина O_i':<38} {'Вершина O_j':<38} {'σ':>6}"
    if show_initial:
        header += f"  {'σ⁰':>6}"
    print(header)
    print('─' * len(header))

    for p in result.pairs:
        la = _get_label(p.vertex_a)[:36]
        lb = _get_label(p.vertex_b)[:36]
        bar = '█' * int(p.score * 15)
        line = f'{la:<38} {lb:<38} {p.score:>5.3f}'
        if show_initial:
            line += f'  {p.initial_score:>5.3f}'
        print(f'{line}  {bar}')
