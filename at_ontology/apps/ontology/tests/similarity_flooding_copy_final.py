from __future__ import annotations

import re
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
    score: float          # итоговая σ [0..1]
    initial_score: float  # σ⁰ до итераций


@dataclass
class _Edge:
    source_id: str
    target_id: str
    label: str


@dataclass
class _Graph:
    """
    Граф онтологии с O(1)-индексами рёбер.
    Индексы строятся лениво при первом обращении.
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
# Шаг 2. Вычисление схожести строк
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


def _char_sim(a: str, b: str) -> float:
    """Посимвольная схожесть на основе расстояния Левенштейна."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return 1.0 - _levenshtein(a, b) / max(len(a), len(b))


def _tokenize(text: str) -> list[str]:
    """
    Разбивает строку на слова, приводит к нижнему регистру,
    убирает короткие стоп-слова и знаки препинания.
    Например: 'Перечень типовых НФ-задач (ЭС)' ->
              ['перечень', 'типовых', 'нф-задач', 'эс']
    """
    # Разбиваем по пробелам и знакам препинания кроме дефиса
    tokens = re.split(r'[\s,.()\[\]/\\]+', text.lower())
    # Убираем пустые и однобуквенные (кроме аббревиатур и русских предлогов)
    stop = {'в', 'и', 'на', 'с', 'к', 'о', 'по', 'из', 'за', 'для', 'от',
            'до', 'со', 'во', 'об', 'при', 'или', 'не', 'а', 'но'}
    return [t for t in tokens if len(t) > 1 and t not in stop]


def _is_abbrev(word: str) -> bool:
    """
    Проверяет, является ли слово аббревиатурой.
    Считаем аббревиатурой: только заглавные буквы, длина 2-5,
    или слово вида «нф-задач» «соз» «иэс» «мас» «дис».
    """
    # Аббревиатура в верхнем регистре: ЭС, МАС, ИЭС, ДИС, НФ, СОЗ
    if word.isupper() and 2 <= len(word) <= 5:
        return True
    # Аббревиатура в нижнем регистре (после tokenize): эс, мас, иэс, дис, нф, соз
    known = {'эс', 'мас', 'иэс', 'дис', 'нф', 'соз', 'бз', 'пр', 'пр', 'ии',
             'аи', 'рии', 'стс', 'имвиа', 'рво', 'иос', 'зом'}
    if word.lower() in known:
        return True
    return False


def _abbrev_matches_words(abbrev: str, words: list[str]) -> float:
    """
    Проверяет, раскрывается ли аббревиатура в слова из списка.
    Например: 'нф' -> ['неформализованных'] -> совпадение по первым буквам.
    Возвращает [0..1]: 1.0 если все буквы аббревиатуры совпали.

    Принцип: ищем подмножество слов из words, первые буквы которых
    в нужном порядке образуют аббревиатуру.
    """
    a = abbrev.lower().replace('-', '')
    if len(a) < 2:
        return 0.0

    # Берём первые буквы всех слов из списка
    initials = [w[0] for w in words if w]
    initials_str = ''.join(initials)

    # Ищем аббревиатуру как подпоследовательность в инициалах
    idx = 0
    matched = 0
    for ch in a:
        while idx < len(initials_str):
            if initials_str[idx] == ch:
                matched += 1
                idx += 1
                break
            idx += 1

    return matched / len(a)


def _best_token_match(token: str, other_tokens: list[str]) -> float:
    """
    Для одного токена из строки A находит максимальную схожесть
    с любым токеном из строки B.

    Если токен — аббревиатура, проверяем:
      1. Прямое совпадение (иэс == иэс)
      2. Раскрытие в слова (иэс → интеллектуальных экспертных систем)
    Если токен — обычное слово:
      1. Прямое совпадение по Левенштейну с каждым токеном B
      2. Совпадение с аббревиатурой из B (обратное раскрытие)
    """
    if not other_tokens:
        return 0.0

    best = 0.0

    if _is_abbrev(token):
        # 1. Прямое совпадение с токенами B
        for ot in other_tokens:
            best = max(best, _char_sim(token, ot))
        # 2. Раскрытие аббревиатуры в слова B
        best = max(best, _abbrev_matches_words(token, other_tokens))
    else:
        # 1. Посимвольная схожесть с каждым токеном B
        for ot in other_tokens:
            if _is_abbrev(ot):
                # B-токен — аббревиатура, проверяем раскрытие в сторону A
                best = max(best, _abbrev_matches_words(ot, [token]))
            else:
                best = max(best, _char_sim(token, ot))

    return best


def _token_sim(a: str, b: str) -> float:
    """
    Токенная схожесть двух строк.

    Алгоритм:
    1. Токенизируем обе строки.
    2. Для каждого токена из A находим лучшее совпадение в B.
    3. Для каждого токена из B находим лучшее совпадение в A.
    4. Итог = среднее по обоим направлениям (симметричное).

    Примеры:
    "Перечень типовых неформализованных задач" vs
    "Типовые НФ-задачи для динамических ИЭС"
    → 'типовых'↔'типовые': ~0.85, 'неформализованных'↔'нф': ~0.50,
      'задач'↔'задачи': ~0.85 → итог ~0.65
    """
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)

    if not tokens_a or not tokens_b:
        return _char_sim(a, b)

    # A→B: для каждого токена A ищем лучшее в B
    score_ab = sum(_best_token_match(t, tokens_b) for t in tokens_a) / len(tokens_a)
    # B→A: для каждого токена B ищем лучшее в A
    score_ba = sum(_best_token_match(t, tokens_a) for t in tokens_b) / len(tokens_b)

    return (score_ab + score_ba) / 2.0


def _label_sim(v_a: object, v_b: object) -> float:
    """
    Схожесть двух вершин по name и label.
    Для label используем токенную схожесть — она учитывает аббревиатуры
    и разные формулировки одного смысла.
    Для name (Topic_N) используем посимвольную схожесть.
    """
    name_score = _char_sim(v_a.name, v_b.name)

    label_a = getattr(v_a, 'label', None) or v_a.name
    label_b = getattr(v_b, 'label', None) or v_b.name
    label_score = _token_sim(label_a, label_b)

    return 0.15 * name_score + 0.85 * label_score


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


def _get_parent_label(vertex_id: str, graph: _Graph) -> str | None:
    """
    Возвращает label родительской вершины (источника Hierarchy-ребра).
    Учитывает контекст — «Основные понятия» под разными родителями
    получают разные оценки схожести.
    """
    for e in graph._in_index.get(vertex_id, []):
        if e.label == 'Hierarchy':
            parent = graph.vertices.get(e.source_id)
            if parent:
                return getattr(parent, 'label', None) or parent.name
    return None


def _initial_sigma(
    v_a: object,
    v_b: object,
    graph_a: _Graph,
    graph_b: _Graph,
) -> float:
    """
    σ⁰ = взвешенная комбинация:
      - токенная схожесть label/name вершин  (85%)
      - схожесть набора свойств              (15%)
    Если у обеих вершин есть родители — добавляем контекст:
      70% своя схожесть + 30% токенная схожесть родителей.
    """
    text_sim = 0.85 * _label_sim(v_a, v_b) + 0.15 * _property_sim(v_a, v_b)

    parent_a = _get_parent_label(v_a.name, graph_a)
    parent_b = _get_parent_label(v_b.name, graph_b)

    if parent_a and parent_b:
        parent_sim = _token_sim(parent_a, parent_b)
        return 0.70 * text_sim + 0.30 * parent_sim

    return text_sim


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
# Шаг 4. Итерации Similarity Flooding — формула C (Melnik et al. 2002)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_dict(d: dict[PairKey, float]) -> dict[PairKey, float]:
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

    σ⁰ прибавляется на КАЖДОЙ итерации — текстовая схожесть
    постоянно «тянет» результат, не давая структуре вытолкнуть
    в лидеры пары с нулевым σ⁰.
    """
    if not pcg_edges:
        print('  PCG пуст — итерации не нужны, используем σ⁰')
        return dict(sigma0)

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

    incoming: dict[PairKey, list[tuple[PairKey, float]]] = defaultdict(list)
    for e in pcg_edges:
        src_a, src_b = e.from_pair
        w = 1.0 / (out_degree_a.get(src_a, 1) * out_degree_b.get(src_b, 1))
        incoming[e.to_pair].append((e.from_pair, w))

    current = _normalize_dict(dict(sigma0))

    for iteration in range(iterations):
        increments: dict[PairKey, float] = {}
        for pair, sources in incoming.items():
            inc = sum(current.get(src, 0.0) * w for src, w in sources)
            if inc > 0:
                increments[pair] = inc

        combined: dict[PairKey, float] = dict(sigma0)
        for pair, val in current.items():
            combined[pair] = combined.get(pair, 0.0) + val
        for pair, inc in increments.items():
            combined[pair] = combined.get(pair, 0.0) + inc

        new_sigma = _normalize_dict(combined)

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

    Улучшения по сравнению с базовым SF:
    — Токенная схожесть вместо посимвольной: учитывает аббревиатуры
      (НФ ↔ неформализованных, ИЭС ↔ интеллектуальных экспертных систем)
      и разные формулировки одного смысла.
    — Контекст родительской вершины: «Основные понятия» под разными
      родителями получают пониженную схожесть.
    — Нормализация на каждой итерации: структурные связи не могут
      полностью вытеснить текстовую схожесть.

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
        print('Загружаем граф A...')
        graph_a = _load_graph(self.ontology_a, self.vertex_filter)
        print(f'  {len(graph_a.vertices)} вершин, {len(graph_a.edges)} рёбер')

        print('Загружаем граф B...')
        graph_b = _load_graph(self.ontology_b, self.vertex_filter)
        print(f'  {len(graph_b.vertices)} вершин, {len(graph_b.edges)} рёбер')

        if not graph_a.vertices or not graph_b.vertices:
            print('Одна из онтологий пуста.')
            return []

        # Строим индексы заранее — нужны для _get_parent_label
        graph_a._build_indices()
        graph_b._build_indices()

        print('Строим σ⁰ (токенная схожесть + контекст родителя)...')
        sigma0: dict[PairKey, float] = {}
        for vid_a, v_a in graph_a.vertices.items():
            for vid_b, v_b in graph_b.vertices.items():
                s = _initial_sigma(v_a, v_b, graph_a, graph_b)
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


# ─────────────────────────────────────────────────────────────────────────────
# Утилита отладки схожести
# ─────────────────────────────────────────────────────────────────────────────

def debug_sim(a: str, b: str) -> None:
    """
    Выводит пошаговое вычисление токенной схожести двух строк.
    Удобно для проверки конкретных пар вручную.
    """
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    print(f'\nA: "{a}"  →  {tokens_a}')
    print(f'B: "{b}"  →  {tokens_b}')
    print()
    print('Совпадения A→B:')
    for t in tokens_a:
        best_score = _best_token_match(t, tokens_b)
        best_tok = max(tokens_b, key=lambda tb: _best_token_match(t, [tb]), default='—')
        print(f'  {t:25s} → {best_tok:25s} : {best_score:.3f}')
    print(f'\nИтог token_sim = {_token_sim(a, b):.3f}')