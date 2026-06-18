from __future__ import annotations
"""
ontology_union.py
─────────────────
Компонент объединения прикладных онтологий курсов/дисциплин.

При объединении O_i и O_j:
  1. Проверяем точные совпадения (по legacy_db_id или одинаковому label).
  2. Для остальных вызываем компонент пересечения (OntologyIntersection).
  3. Подобные вершины сливаем в одну (имя и label берём из O_i).
  4. Уникальные вершины добавляем как есть.
  5. Восстанавливаем связи.

Использование:
    from ontology_union import OntologyUnion

    result = OntologyUnion(ontology_a, ontology_b).run()
    print(f"Вершин в результате: {len(result.vertices)}")
"""

from dataclasses import dataclass, field
from typing import Callable
from ontology_intersection import (
    OntologyIntersection,
    IntersectionResult,
    SimilarPair,
    _is_topic,
    _get_label,
    _load_graph,
    _Graph,
)


# ─── Структуры результата объединения ────────────────────────────────────────

@dataclass
class MergedVertex:
    """Вершина результирующей онтологии."""
    name: str                   # имя из O_i (или O_j если только в O_j)
    label: str                  # label из O_i
    source: str                 # 'a', 'b', 'merged'
    original_a: object | None   # исходная вершина из O_i
    original_b: object | None   # исходная вершина из O_j
    similarity: float = 0.0     # σ для merged, иначе 0


@dataclass
class MergedEdge:
    """Связь результирующей онтологии."""
    source_name: str
    target_name: str
    rel_type: str


@dataclass
class UnionResult:
    """Результат операции объединения."""
    vertices: list[MergedVertex]
    edges: list[MergedEdge]
    ontology_a_name: str
    ontology_b_name: str
    exact_matches: int      # точные совпадения
    similar_pairs: int      # подобные пары (из пересечения)
    unique_from_a: int      # уникальные из O_i
    unique_from_b: int      # уникальные из O_j

    def summary(self) -> str:
        return (
            f"Объединение «{self.ontology_a_name}» ∪ «{self.ontology_b_name}»\n"
            f"  Вершин в результате : {len(self.vertices)}\n"
            f"  Рёбер в результате  : {len(self.edges)}\n"
            f"  Точных совпадений   : {self.exact_matches}\n"
            f"  Подобных пар (SF)   : {self.similar_pairs}\n"
            f"  Уникальных из O_i   : {self.unique_from_a}\n"
            f"  Уникальных из O_j   : {self.unique_from_b}"
        )


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _get_legacy_id(vertex: object) -> int | None:
    """Читаем legacy_db_id из metadata вершины."""
    meta = getattr(vertex, 'metadata', None)
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta.get('legacy_db_id')
    return getattr(meta, 'legacy_db_id', None)


def _get_rel_type_str(rel: object) -> str:
    rel_type = getattr(rel, 'type', None)
    if rel_type is None:
        return 'unknown'
    if hasattr(rel_type, 'alias'):
        return rel_type.alias
    if hasattr(rel_type, 'name'):
        return rel_type.name
    return 'unknown'


def _get_vertex_end(rel_end: object) -> object | None:
    if hasattr(rel_end, 'value'):
        return rel_end.value
    return rel_end


# ─── Публичный класс ──────────────────────────────────────────────────────────

class OntologyUnion:
    """
    Компонент объединения прикладных онтологий курсов/дисциплин.

    Параметры
    ---------
    ontology_a        : первая онтология O_i (имена берутся отсюда)
    ontology_b        : вторая онтология O_j
    intersection_min_score : порог схожести для пересечения (по умолчанию 0.80)
    intersection_sf_weight : вес SF в пересечении (по умолчанию 0.3)
    vertex_filter     : фильтр вершин; по умолчанию только Topic_*
    verbose           : выводить прогресс
    """

    def __init__(
        self,
        ontology_a: object,
        ontology_b: object,
        intersection_min_score: float = 0.85,
        intersection_sf_weight: float = 0.3,
        vertex_filter: Callable[[object], bool] | None = None,
        verbose: bool = True,
    ) -> None:
        self.ontology_a             = ontology_a
        self.ontology_b             = ontology_b
        self.intersection_min_score = intersection_min_score
        self.intersection_sf_weight = intersection_sf_weight
        self.vertex_filter          = vertex_filter if vertex_filter is not None else _is_topic
        self.verbose                = verbose

    def run(self) -> UnionResult:
        vb = self.verbose

        if vb: print('\n=== КОМПОНЕНТ ОБЪЕДИНЕНИЯ ===')

        # ── 1. Загружаем онтологии ────────────────────────────────────────────
        if vb: print('Блок загрузки онтологий...')
        graph_a = _load_graph(self.ontology_a, self.vertex_filter)
        graph_b = _load_graph(self.ontology_b, self.vertex_filter)
        graph_a.build_indices()
        graph_b.build_indices()

        if vb:
            print(f'  O_i: {len(graph_a.vertices)} вершин')
            print(f'  O_j: {len(graph_b.vertices)} вершин')

        # ── 2. Блок проверки точных совпадений ────────────────────────────────
        if vb: print('Блок проверки точных совпадений...')

        # Сопоставление по legacy_db_id (если есть)
        legacy_map_a: dict[int, str] = {}
        for vid, v in graph_a.vertices.items():
            lid = _get_legacy_id(v)
            if lid is not None:
                legacy_map_a[lid] = vid

        exact_a_to_b: dict[str, str] = {}   # vid_a → vid_b (точные совпадения)
        for vid_b, v_b in graph_b.vertices.items():
            lid_b = _get_legacy_id(v_b)
            if lid_b is not None and lid_b in legacy_map_a:
                vid_a = legacy_map_a[lid_b]
                exact_a_to_b[vid_a] = vid_b
                continue
            # Запасной вариант: точное совпадение label
            label_b = _get_label(v_b).lower()
            for vid_a, v_a in graph_a.vertices.items():
                if _get_label(v_a).lower() == label_b:
                    exact_a_to_b[vid_a] = vid_b
                    break

        if vb: print(f'  Найдено точных совпадений: {len(exact_a_to_b)}')

        # ── 3. Вызов компонента пересечения для остальных вершин ─────────────
        remaining_a = {k: v for k, v in graph_a.vertices.items()
                       if k not in exact_a_to_b}
        remaining_b = {k: v for k, v in graph_b.vertices.items()
                       if k not in set(exact_a_to_b.values())}

        similar_a_to_b: dict[str, tuple[str, float]] = {}  # vid_a → (vid_b, score)
        intersection_result: IntersectionResult | None = None

        if remaining_a and remaining_b:
            if vb: print('Блок вызова компонента пересечения...')

            # Создаём «урезанные» онтологии только из оставшихся вершин
            # Для этого используем оригинальные онтологии, но ограничиваем
            # фильтром по оставшимся вершинам
            remaining_a_names = set(remaining_a.keys())
            remaining_b_names = set(remaining_b.keys())

            def filter_remaining_a(v: object) -> bool:
                return self.vertex_filter(v) and v.name in remaining_a_names

            def filter_remaining_b(v: object) -> bool:
                return self.vertex_filter(v) and v.name in remaining_b_names

            # Запускаем пересечение с ограниченным фильтром
            intersector = OntologyIntersection(
                ontology_a=self.ontology_a,
                ontology_b=self.ontology_b,
                min_score=self.intersection_min_score,
                sf_weight=self.intersection_sf_weight,
                vertex_filter=filter_remaining_a,
                verbose=vb,
            )
            # Для O_j используем отдельный граф с фильтром
            from ontology_intersection import (
                _compute_sigma0, _build_pcg, _flood, _filter_one_to_one,
                _normalize, _is_topic
            )
            graph_a_rem = _load_graph(self.ontology_a, filter_remaining_a)
            graph_b_rem = _load_graph(self.ontology_b, filter_remaining_b)
            graph_a_rem.build_indices()
            graph_b_rem.build_indices()

            sigma0: dict = {}
            for vid_a, v_a in graph_a_rem.vertices.items():
                for vid_b, v_b in graph_b_rem.vertices.items():
                    s = _compute_sigma0(v_a, v_b, graph_a_rem, graph_b_rem)
                    if s > 0:
                        sigma0[(vid_a, vid_b)] = s

            if vb: print(f'  Пар с σ⁰>0: {len(sigma0)}')

            pcg = _build_pcg(graph_a_rem, graph_b_rem)
            sigma = _flood(
                sigma0, pcg, graph_a_rem, graph_b_rem,
                iterations=10,
                sf_weight=self.intersection_sf_weight,
                convergence_threshold=1e-4,
                verbose=vb,
            )
            filtered = _filter_one_to_one(
                sigma, graph_a_rem, graph_b_rem,
                self.intersection_min_score,
            )
            for (vid_a, vid_b), score in filtered:
                similar_a_to_b[vid_a] = (vid_b, score)

            if vb: print(f'  Подобных пар: {len(similar_a_to_b)}')
        else:
            if vb: print('  Все вершины O_j уже сопоставлены точно, пересечение не нужно.')

        # ── 4. Блок слияния подобных вершин ──────────────────────────────────
        if vb: print('Блок слияния подобных вершин...')

        merged_vertices: list[MergedVertex] = []
        # Отображение: старое имя вершины → имя в результирующей онтологии
        name_map_a: dict[str, str] = {}   # vid_a → merged_name
        name_map_b: dict[str, str] = {}   # vid_b → merged_name
        used_b: set[str] = set()

        # Точные совпадения → берём имя и label из O_i
        for vid_a, vid_b in exact_a_to_b.items():
            v_a = graph_a.vertices[vid_a]
            v_b = graph_b.vertices[vid_b]
            merged = MergedVertex(
                name=vid_a,
                label=_get_label(v_a),
                source='merged',
                original_a=v_a,
                original_b=v_b,
                similarity=1.0,
            )
            merged_vertices.append(merged)
            name_map_a[vid_a] = vid_a
            name_map_b[vid_b] = vid_a
            used_b.add(vid_b)

        # Подобные пары → берём имя и label из O_i
        for vid_a, (vid_b, score) in similar_a_to_b.items():
            v_a = graph_a.vertices.get(vid_a)
            v_b = graph_b.vertices.get(vid_b)
            if v_a is None or v_b is None:
                continue
            merged = MergedVertex(
                name=vid_a,
                label=_get_label(v_a),   # ← имя всегда из O_i
                source='merged',
                original_a=v_a,
                original_b=v_b,
                similarity=score,
            )
            merged_vertices.append(merged)
            name_map_a[vid_a] = vid_a
            name_map_b[vid_b] = vid_a
            used_b.add(vid_b)

        if vb: print(f'  Слито вершин: {len(merged_vertices)}')

        # ── 5. Блок добавления уникальных вершин ─────────────────────────────
        if vb: print('Блок добавления уникальных вершин...')

        unique_a = 0
        for vid_a, v_a in graph_a.vertices.items():
            if vid_a not in name_map_a:
                merged_vertices.append(MergedVertex(
                    name=vid_a,
                    label=_get_label(v_a),
                    source='a',
                    original_a=v_a,
                    original_b=None,
                ))
                name_map_a[vid_a] = vid_a
                unique_a += 1

        unique_b = 0
        for vid_b, v_b in graph_b.vertices.items():
            if vid_b not in name_map_b:
                # Уникальные из O_j получают новое имя с суффиксом _b
                new_name = f"{vid_b}_b"
                merged_vertices.append(MergedVertex(
                    name=new_name,
                    label=_get_label(v_b),
                    source='b',
                    original_a=None,
                    original_b=v_b,
                ))
                name_map_b[vid_b] = new_name
                unique_b += 1

        if vb:
            print(f'  Уникальных из O_i: {unique_a}')
            print(f'  Уникальных из O_j: {unique_b}')

        # ── 6. Блок восстановления связей ─────────────────────────────────────
        if vb: print('Блок восстановления связей...')

        merged_edges: list[MergedEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()

        def _add_edge(src_name: str, tgt_name: str, rel_type: str) -> None:
            key = (src_name, tgt_name, rel_type)
            if key not in seen_edges:
                seen_edges.add(key)
                merged_edges.append(MergedEdge(
                    source_name=src_name,
                    target_name=tgt_name,
                    rel_type=rel_type,
                ))

        # Связи из O_i
        for _rname, rel in self.ontology_a.relationships.items():
            try:
                src = _get_vertex_end(rel.source)
                tgt = _get_vertex_end(rel.target)
            except AttributeError:
                continue
            if src is None or tgt is None:
                continue
            if not self.vertex_filter(src) or not self.vertex_filter(tgt):
                continue
            src_mapped = name_map_a.get(src.name)
            tgt_mapped = name_map_a.get(tgt.name)
            if src_mapped and tgt_mapped:
                _add_edge(src_mapped, tgt_mapped, _get_rel_type_str(rel))

        # Связи из O_j (только если концы не уже покрыты связями из O_i)
        for _rname, rel in self.ontology_b.relationships.items():
            try:
                src = _get_vertex_end(rel.source)
                tgt = _get_vertex_end(rel.target)
            except AttributeError:
                continue
            if src is None or tgt is None:
                continue
            if not self.vertex_filter(src) or not self.vertex_filter(tgt):
                continue
            src_mapped = name_map_b.get(src.name)
            tgt_mapped = name_map_b.get(tgt.name)
            if src_mapped and tgt_mapped:
                _add_edge(src_mapped, tgt_mapped, _get_rel_type_str(rel))

        if vb: print(f'  Связей в результате: {len(merged_edges)}')

        return UnionResult(
            vertices=merged_vertices,
            edges=merged_edges,
            ontology_a_name=getattr(self.ontology_a, 'name', ''),
            ontology_b_name=getattr(self.ontology_b, 'name', ''),
            exact_matches=len(exact_a_to_b),
            similar_pairs=len(similar_a_to_b),
            unique_from_a=unique_a,
            unique_from_b=unique_b,
        )


def print_union(result: UnionResult) -> None:
    """Красивый вывод результата объединения."""
    print(f'\n{result.summary()}')
    print(f'\nСлитые вершины (подобные пары):')
    merged = [v for v in result.vertices if v.source == 'merged' and v.similarity < 1.0]
    merged.sort(key=lambda v: -v.similarity)
    for v in merged:
        la = v.label[:40]
        lb = _get_label(v.original_b)[:40] if v.original_b else '—'
        print(f'  [{v.similarity:.3f}] {la:<42} ← {lb}')
