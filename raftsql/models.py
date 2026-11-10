"""
User-facing re-export module.
Allows: from raftsql import models; models.CharField, models.Q, etc.
"""
# Base model
from .orm.model import Model

# Scalar fields
from .orm.fields import (
    AutoField,
    IntegerField,
    BigIntegerField,
    SmallIntegerField,
    PositiveIntegerField,
    FloatField,
    DecimalField,
    CharField,
    TextField,
    EmailField,
    SlugField,
    BooleanField,
    DateField,
    DateTimeField,
    TimeField,
    JSONField,
    UUIDField,
    BinaryField,
    ArrayField,
)

# File / image fields
from .orm.fields import (
    FileField,
    ImageField,
    FieldFile,
)

# Relation fields
from .orm.fields import (
    ForeignKey,
    OneToOneField,
    ManyToManyField,
)

# on_delete constants  (models.CASCADE, models.SET_NULL, ...)
from .orm.fields import CASCADE, SET_NULL, PROTECT, RESTRICT, DO_NOTHING

# Meta constraints
from .orm.fields import CheckConstraint, UniqueConstraint

# Query helpers  (models.Q, models.F, models.Count, ...)
from .orm.q import Q
from .orm.f import F
from .orm.aggregates import Count, Sum, Avg, Max, Min

# Advanced expressions
from .orm.expressions import (
    Window,
    RowNumber, Rank, DenseRank, PercentRank, CumeDist, Ntile,
    Lag, Lead, FirstValue, LastValue, NthValue,
    Coalesce, Value,
    Subquery, OuterRef,
    Case, When,
    Cast,
)

# Generic relations
from .orm.contenttypes import GenericForeignKey
