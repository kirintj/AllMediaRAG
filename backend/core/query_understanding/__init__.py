from .classifier import QueryClassifier

__all__ = ["QueryClassifier"]

# Lazy imports for modules that may not exist yet
try:
    from .hyde_generator import HyDEGenerator
    __all__.append("HyDEGenerator")
except ImportError:
    pass

try:
    from .multi_query import MultiQueryGenerator
    __all__.append("MultiQueryGenerator")
except ImportError:
    pass

try:
    from .router import QueryRouter
    __all__.append("QueryRouter")
except ImportError:
    pass
