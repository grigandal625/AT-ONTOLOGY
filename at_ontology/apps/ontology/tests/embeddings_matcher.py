from __future__ import annotations

"""
embeddings_matcher.py
─────────────────────
Семантическое сопоставление вершин онтологий на основе векторных эмбеддингов.

Установка зависимостей (один раз в активированном окружении):
    pip install sentence-transformers

Модель загружается автоматически при первом запуске (~120 МБ),
затем кэшируется локально.
"""

import re
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable

# Импортируем только базовые структуры и утилиты из SF,
# НЕ импортируем ничего из embeddings_matcher (избегаем цикла)
from at_ontology.apps.ontology.tests.similarity_flooding import (
    MatchResult,
    _Edge,
    _Graph,
    _PCGEdge,
    _load_graph,
    _build_pcg,
    _flood,
    _normalize_dict,
    _filter_one_to_one,
    _get_parent_label,
    _token_sim,
)

type PairKey = tuple[str, str]

# ─────────────────────────────────────────────────────────────────────────────
# Модель по умолчанию
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "cointegrated/rubert-tiny2"

_model_cache: dict[str, object] = {}


def _get_model(model_name: str):
    if model_name not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "Установи библиотеку:\n"
                "  pip install sentence-transformers\n"
                "После этого модель (~120 МБ) загрузится автоматически."
            )
        print(f'  Загружаем модель {model_name}...')
        _model_cache[model_name] = SentenceTransformer(model_name)
        print('  Модель загружена.')
    return _model_cache[model_name]


# ─────────────────────────────────────────────────────────────────────────────
# Текстовое представление вершины
# ─────────────────────────────────────────────────────────────────────────────

def _get_vertex_text(vertex: object) -> str:
    """
    Формирует текст для эмбеддинга.
    Берём label + первый вопрос из свойств (если есть) для контекста.
    """
    label = getattr(vertex, 'label', None) or vertex.name

    props = getattr(vertex, 'properties', None)
    if isinstance(props, list) and props:
        try:
            val = props[0].value
            if isinstance(val, dict) and 'question' in val:
                return f"{label}. {val['question']}"
        except Exception:
            pass

    return label


# ─────────────────────────────────────────────────────────────────────────────
# Вычисление эмбеддингов
# ─────────────────────────────────────────────────────────────────────────────

def _compute_embeddings(
    vertices: dict[str, object],
    model,
    batch_size: int = 64,
) -> dict[str, object]:
    ids   = list(vertices.keys())
    texts = [_get_vertex_text(vertices[vid]) for vid in ids]

    print(f'  Кодируем {len(texts)} вершин...')
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return {vid: vectors[i] for i, vid in enumerate(ids)}


def _cosine_sim(v1, v2) -> float:
    """
    Косинусная схожесть нормализованных векторов → [0..1].
    Так как векторы L2-нормализованы, косинус = скалярное произведение.
    Сдвигаем из [-1,1] в [0,1].
    """
    import numpy as np
    return float((np.dot(v1, v2) + 1.0) / 2.0)


# ─────────────────────────────────────────────────────────────────────────────
# Построение σ⁰ на основе эмбеддингов
# ─────────────────────────────────────────────────────────────────────────────

def _build_sigma0_embeddings(
    graph_a: _Graph,
    graph_b: _Graph,
    emb_a: dict[str, object],
    emb_b: dict[str, object],
    parent_weight: float = 0.20,
    token_weight:  float = 0.10,
) -> dict[PairKey, float]:
    """
    σ⁰ = взвешенная комбинация:
      (1 - parent_weight - token_weight) × косинус эмбеддингов   ← семантика
      token_weight                        × токенная схожесть     ← аббревиатуры
      parent_weight                       × схожесть родителей    ← контекст

    Эмбеддинги понимают что «Машина вывода» ≈ «Механизм логического вывода».
    Токенная схожесть помогает с «НФ» ↔ «неформализованных».
    Родительский контекст разделяет одинаковые названия под разными разделами.
    """
    emb_weight = 1.0 - parent_weight - token_weight
    sigma0: dict[PairKey, float] = {}

    for vid_a, v_a in graph_a.vertices.items():
        vec_a = emb_a.get(vid_a)
        if vec_a is None:
            continue
        label_a  = getattr(v_a, 'label', None) or v_a.name
        parent_a = _get_parent_label(vid_a, graph_a)

        for vid_b, v_b in graph_b.vertices.items():
            vec_b = emb_b.get(vid_b)
            if vec_b is None:
                continue
            label_b  = getattr(v_b, 'label', None) or v_b.name
            parent_b = _get_parent_label(vid_b, graph_b)

            sem_sim = _cosine_sim(vec_a, vec_b)
            tok_sim = _token_sim(label_a, label_b)

            if parent_a and parent_b:
                par_sim = _token_sim(parent_a, parent_b)
            else:
                par_sim = 0.5  # нет родителя — нейтральный вклад

            score = emb_weight * sem_sim + token_weight * tok_sim + parent_weight * par_sim

            if score > 0:
                sigma0[(vid_a, vid_b)] = score

    return sigma0


# ─────────────────────────────────────────────────────────────────────────────
# Публичный класс
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingsSimilarityMatcher:
    """
    Сопоставление онтологий на основе семантических эмбеддингов
    с опциональным структурным распространением Similarity Flooding.

    Шаги:
    1. Загружаем русскоязычную модель sentence-transformers.
    2. Кодируем вершины обеих онтологий в векторы.
    3. σ⁰ = эмбеддинги + токенная схожесть + контекст родителя.
    4. Опционально: итерации SF для структурного уточнения.
    5. Фильтр «один к одному».

    Параметры
    ---------
    ontology_a, ontology_b : объекты Ontology из at_ontology_parser
    model_name             : имя модели, по умолчанию "cointegrated/rubert-tiny2"
    use_sf                 : применять ли итерации SF (True — учитывает структуру)
    sf_iterations          : макс. итераций SF
    min_score              : порог отсечения (эмбеддинги точнее, можно 0.3–0.5)
    vertex_filter          : (vertex) -> bool
                             Для реальных онтологий:
                               lambda v: v.name.startswith("Topic_")
    """

    def __init__(
        self,
        ontology_a: object,
        ontology_b: object,
        model_name:    str                           = DEFAULT_MODEL,
        use_sf:        bool                          = True,
        sf_iterations: int                           = 20,
        min_score:     float                         = 0.3,
        vertex_filter: Callable[[object], bool] | None = None,
    ) -> None:
        self.ontology_a    = ontology_a
        self.ontology_b    = ontology_b
        self.model_name    = model_name
        self.use_sf        = use_sf
        self.sf_iterations = sf_iterations
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

        graph_a._build_indices()
        graph_b._build_indices()

        model = _get_model(self.model_name)

        print('Вычисляем эмбеддинги онтологии A...')
        emb_a = _compute_embeddings(graph_a.vertices, model)

        print('Вычисляем эмбеддинги онтологии B...')
        emb_b = _compute_embeddings(graph_b.vertices, model)

        print('Строим σ⁰ (эмбеддинги + токены + контекст родителя)...')
        sigma0 = _build_sigma0_embeddings(graph_a, graph_b, emb_a, emb_b)
        print(f'  {len(sigma0)} пар с σ⁰ > 0')

        if self.use_sf:
            print('Строим PCG...')
            pcg_edges = _build_pcg(graph_a, graph_b)
            print(f'  {len(pcg_edges)} рёбер в PCG')

            print('Итерации SF (формула C)...')
            sigma = _flood(
                sigma0, pcg_edges, graph_a, graph_b,
                self.sf_iterations,
            )
        else:
            sigma = _normalize_dict(dict(sigma0))

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