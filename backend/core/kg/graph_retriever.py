"""Graph retriever: resolve query entities → graph_candidates → chunk IDs."""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

LAW_PATTERN = re.compile(
    r'(?:中华人民共和国)?[一-鿿]{2,20}(?:法|条例|规定|办法|决定|'
    r'意见|通知|细则|准则|通则|方案|标准)(?:（[^）]+）)?'
)


class GraphRetriever:
    """Orchestrates entity resolution and graph candidate expansion."""

    def __init__(self, graph_store: Any):
        self._graph_store = graph_store
        self._alias_map: dict[str, str] = {}  # alias_text → canonical_name
        self._all_aliases: set[str] = set()

    def load_aliases(self) -> None:
        """Load all aliases from Neo4j at startup for in-memory lookup."""
        try:
            with self._graph_store._driver.session() as session:
                result = session.run(
                    "MATCH (a:Alias)-[:RESOLVES_TO]->(e:Entity) "
                    "RETURN a.text AS alias, e.name AS canonical"
                )
                for record in result:
                    alias = record["alias"]
                    canonical = record["canonical"]
                    self._alias_map[alias] = canonical
                    self._all_aliases.add(alias)
            logger.info("Loaded %d aliases for entity resolution", len(self._all_aliases))
        except Exception as e:
            logger.warning("Failed to load aliases: %s", e)

    def resolve_entities(self, query: str) -> list[str]:
        """Find canonical entity names in the query."""
        resolved = set()

        # Alias match (in-memory, no Neo4j call)
        for alias in self._all_aliases:
            if alias in query:
                resolved.add(self._alias_map[alias])

        # Regex match for law names
        for match in LAW_PATTERN.finditer(query):
            name = match.group()
            if name in self._alias_map:
                resolved.add(self._alias_map[name])
            else:
                resolved.add(name)

        return list(resolved)

    def search(self, query: str, max_chunks: int = 20) -> list[str]:
        """Full pipeline: resolve → expand → map → chunk IDs."""
        seed_entities = self.resolve_entities(query)
        if not seed_entities:
            return []
        return self._graph_store.graph_candidates(seed_entities, max_chunks=max_chunks)
