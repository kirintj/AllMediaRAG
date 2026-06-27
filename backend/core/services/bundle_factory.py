"""BundleFactory -- centralised construction of domain Bundles from InfraBundle.

Why a factory instead of direct construction:
    Each Bundle class (RetrievalBundle, ProcessingBundle, GenerationBundle)
    accepts an InfraBundle and internally creates its own service dependencies
    (RetrievalPipeline, GenerationService, CitationVerifier).  Without a
    factory, every caller (API endpoints, orchestrator, tests) must know
    which Bundle classes exist and how to wire them -- violating the
    Dependency Inversion Principle and making it hard to swap bundle
    implementations later.

    BundleFactory encapsulates this knowledge in one place:
    - Callers ask for "a retrieval bundle" without importing RetrievalBundle.
    - Adding a new Bundle type (e.g. EvaluationBundle) only requires a new
      method here, not changes to every caller.
    - Testing callers is simpler: mock the factory, not three separate classes.

Design decisions:
    1. **InfraBundle as the single input**: The factory receives one
       InfraBundle and passes it to every Bundle constructor.  This
       ensures all Bundles share the same infrastructure wiring --
       the same embedding service, cache manager, LLM client, etc.
       No Bundle gets a stale or different InfraBundle.

    2. **No caching of Bundles**: Each create_* call constructs a fresh
       Bundle.  If the caller wants to reuse a Bundle, it holds the
       reference itself.  This avoids hidden mutable state inside the
       factory and makes the lifecycle explicit.

    3. **Lazy imports for the concrete Bundle classes**: The factory
       imports RetrievalBundle, ProcessingBundle, and GenerationBundle
       at the module level.  Since these are pure Python classes with
       no heavy __init__ (the heavy lifting happens inside InfraBundle
       construction), the import cost is negligible.  If circular
       imports ever become an issue, the imports can be moved inside
       the methods.

    4. **Why not a single create_all() method**: Exposing individual
       create_* methods lets callers request only the Bundles they
       need.  An API endpoint that only handles retrieval doesn't need
       to construct a GenerationBundle.  A convenience create_all()
       method could be added later if callers consistently need all
       three.
"""

from __future__ import annotations

import logging
from typing import Any

from core.services.retrieval_bundle import RetrievalBundle
from core.services.processing_bundle import ProcessingBundle
from core.services.generation_bundle import GenerationBundle

logger = logging.getLogger(__name__)


class BundleFactory:
    """Centralised factory for constructing domain Bundles from an InfraBundle.

    Usage::

        infra = create_infra(settings)
        factory = BundleFactory(infra)

        retrieval = factory.create_retrieval_bundle()
        processing = factory.create_processing_bundle()
        generation = factory.create_generation_bundle()

    Args:
        infra: An ``InfraBundle`` instance (from
            ``core.services.create_infra``).  All Bundles created by
            this factory share the same InfraBundle, ensuring consistent
            infrastructure wiring.
    """

    def __init__(self, infra: Any) -> None:
        """Create a BundleFactory bound to an InfraBundle.

        Why store infra rather than individual services:
            The InfraBundle is the single source of truth for all
            infrastructure dependencies.  Storing it whole (rather
            than extracting specific fields) means the factory
            doesn't need to change when a new field is added to
            InfraBundle -- each Bundle accesses what it needs.
        """
        self._infra = infra
        logger.info("BundleFactory created")

    # ------------------------------------------------------------------
    # Bundle construction methods
    # ------------------------------------------------------------------

    def create_retrieval_bundle(self) -> RetrievalBundle:
        """Create a RetrievalBundle for query retrieval operations.

        The RetrievalBundle wraps RetrievalPipeline with a slim protocol
        (retrieve + classify_query), cache-aside, and error wrapping.

        Returns:
            A fresh RetrievalBundle instance bound to the shared InfraBundle.
        """
        logger.debug("Creating RetrievalBundle")
        return RetrievalBundle(self._infra)

    def create_processing_bundle(self) -> ProcessingBundle:
        """Create a ProcessingBundle for document processing operations.

        The ProcessingBundle wraps DocumentProcessor with a slim protocol
        (process_document + extract_images) and error wrapping.

        Returns:
            A fresh ProcessingBundle instance bound to the shared InfraBundle.
        """
        logger.debug("Creating ProcessingBundle")
        return ProcessingBundle(self._infra)

    def create_generation_bundle(self) -> GenerationBundle:
        """Create a GenerationBundle for answer generation operations.

        The GenerationBundle wraps GenerationService + CitationVerifier
        with a slim protocol (generate + verify_citation) and error
        wrapping.  It creates its own RetrievalPipeline internally for
        the GenerationService to use during query_stream.

        Returns:
            A fresh GenerationBundle instance bound to the shared InfraBundle.
        """
        logger.debug("Creating GenerationBundle")
        return GenerationBundle(self._infra)
