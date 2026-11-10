"""
GenericForeignKey — polymorphic FK to any Model.

Usage::

    class Comment(Model):
        content_type = CharField(max_length=200)   # stores "module.ClassName"
        object_id    = IntegerField()
        content_object = GenericForeignKey('content_type', 'object_id')

    # Attach a comment to a Post
    comment.content_object = post_instance     # sets content_type + object_id
    fetched_comment.content_object             # → lazily fetches and returns the Post

No extra DB table is required — the model label is stored inline as a VARCHAR.
Use ``GenericRelation`` (reverse accessor) if you need reverse lookups (not yet
implemented; use raw filter instead).
"""
from typing import Any, Optional


class GenericForeignKey:
    """Descriptor that implements a generic FK using a content-type string + pk integer."""

    def __init__(self, ct_field: str = "content_type", fk_field: str = "object_id") -> None:
        self.ct_field = ct_field
        self.fk_field = fk_field
        self._attr_name: Optional[str] = None

    def __set_name__(self, owner: Any, name: str) -> None:
        self._attr_name = name

    # ------------------------------------------------------------------
    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        label: Optional[str] = obj.__dict__.get(self.ct_field)
        pk_val = obj.__dict__.get(self.fk_field)
        if not label or pk_val is None:
            return None

        cache_key = f"_gfk_{self._attr_name}_cache"
        if cache_key in obj.__dict__:
            return obj.__dict__[cache_key]

        model_cls = _resolve_model_label(label)
        if model_cls is None:
            return None

        try:
            instance = model_cls.objects.get(pk=pk_val)
            obj.__dict__[cache_key] = instance
            return instance
        except Exception:
            return None

    def __set__(self, obj: Any, value: Any) -> None:
        cache_key = f"_gfk_{self._attr_name}_cache"
        if value is None:
            obj.__dict__[self.ct_field] = None
            obj.__dict__[self.fk_field] = None
            obj.__dict__.pop(cache_key, None)
        else:
            model_cls = type(value)
            label = f"{model_cls.__module__}.{model_cls.__name__}"
            pk_val = value.__dict__.get(value._get_pk_column())
            obj.__dict__[self.ct_field] = label
            obj.__dict__[self.fk_field] = pk_val
            obj.__dict__[cache_key] = value


# ------------------------------------------------------------------
def _resolve_model_label(label: str) -> Optional[Any]:
    """
    Look up a Model class from a label string like "myapp.models.Post" or "Post".

    Scans ``_MODEL_REGISTRY`` (populated automatically by ModelMeta).
    Returns the first match, or None if not found.
    """
    from .model import _MODEL_REGISTRY
    for cls in _MODEL_REGISTRY:
        full_label = f"{cls.__module__}.{cls.__name__}"
        if full_label == label or cls.__name__ == label:
            return cls
    return None
