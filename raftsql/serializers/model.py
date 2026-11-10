"""
ModelSerializer — auto-generates a serializer from a RaftSQL model.

Field discovery uses the model's own metadata (_fields, _relations, etc.)
so there are zero Django dependencies.
"""
from datetime import datetime, date, time
from typing import Any, Dict, List

from .base import Serializer


def _coerce(value: Any, field: Any) -> Any:
    """Cast *value* to the Python type expected by *field*, if needed."""
    if value is None or value == "":
        return None
    from raftsql.orm.fields import (
        AutoField, IntegerField, BigIntegerField, SmallIntegerField,
        FloatField, DecimalField, BooleanField, ForeignKey, OneToOneField,
    )
    if isinstance(field, (AutoField, IntegerField, BigIntegerField,
                          SmallIntegerField, ForeignKey, OneToOneField)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if isinstance(field, (FloatField, DecimalField)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if isinstance(field, BooleanField):
        if isinstance(value, str):
            return value.lower() not in ("false", "0", "no", "")
        return bool(value)
    return value


def _build_col_map(model: type) -> Dict[str, tuple]:
    """
    Scan *model* class members and return::

        { col_name: (attr_name, field_obj) }

    - Regular / file fields:  col_name  ==  attr_name   (e.g. ``'title'``)
    - ForeignKey / O2O:       col_name  ==  attr_name + '_id'  (e.g. ``'author_id'``)
    - ManyToManyField:        excluded  (no column on this table)
    """
    from raftsql.orm.fields import Field, ManyToManyField, ForeignKey, OneToOneField

    col_map: Dict[str, tuple] = {}
    for attr_name, val in vars(model).items():
        if attr_name.startswith("_") or attr_name == "Meta":
            continue
        if not isinstance(val, Field) or isinstance(val, ManyToManyField):
            continue
        if isinstance(val, (ForeignKey, OneToOneField)):
            col = model._relations.get(attr_name, {}).get("column", f"{attr_name}_id")
        else:
            col = attr_name
        col_map[col] = (attr_name, val)
    return col_map


class ModelSerializer(Serializer):
    """
    Automatically builds serialization / deserialization from a RaftSQL model.

    Minimal setup::

        class BlogSerializer(ModelSerializer):
            class Meta:
                model            = Blog
                fields           = '__all__'
                read_only_fields = ['id', 'created_at', 'updated_at']
                exclude          = []        # column names to always skip

    ``fields`` accepts either **column names** (``'author_id'``) or
    **attribute names** (``'author'``) — both work.

    ``auto_now`` / ``auto_now_add`` columns are always read-only regardless
    of ``read_only_fields``.

    Usage (async FastAPI)::

        @router.post("/blogs/")
        async def create_blog(
            title: str = Form(...),
            thumbnail: UploadFile = File(None),
        ):
            s = BlogSerializer(data={"title": title, "thumbnail": thumbnail})
            if await s.is_valid_async():
                blog = await s.asave()
                return s.data
            return s.errors

        @router.put("/blogs/{blog_id}")
        async def update_blog(blog_id: int, title: str = Form(...)):
            blog = await Blog.objects.aget(id=blog_id)
            s = BlogSerializer(blog, data={"title": title}, partial=True)
            if await s.is_valid_async():
                blog = await s.asave()
                return s.data
            return s.errors

    Usage (sync)::

        s = BlogSerializer(blog_instance)
        return s.data                        # serialize

        s = BlogSerializer(data={"title": "Hello"})
        if s.is_valid():
            blog = s.save()                  # create

        s = BlogSerializer(blog, data={"title": "Updated"}, partial=True)
        if s.is_valid():
            blog = s.save()                  # update

        s = BlogSerializer(queryset, many=True)
        return s.data                        # list

    Customization::

        class BlogSerializer(ModelSerializer):
            class Meta:
                model = Blog
                fields = '__all__'
                read_only_fields = ['id', 'created_at', 'updated_at']

            # Per-field validation
            def validate_title(self, value):
                if len(value) < 3:
                    raise ValueError("Title must be at least 3 characters.")
                return value

            # Cross-field validation
            def validate(self, data):
                if data.get('title') == data.get('content'):
                    raise ValueError("Title and content cannot be the same.")
                return data

            # Custom output
            def to_representation(self, instance):
                data = super().to_representation(instance)
                data['title_upper'] = data['title'].upper()
                return data
    """

    class Meta:
        model: Any = None
        fields: Any = "__all__"          # '__all__' or list of col/attr names
        read_only_fields: List[str] = []
        exclude: List[str] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.Meta.model is None:
            raise ValueError(f"{self.__class__.__name__} must define Meta.model")
        self._col_map: Dict[str, tuple] = _build_col_map(self.Meta.model)
        self._serializable_cols: List[str] = self._resolve_cols()
        self._writable_cols: List[str] = self._resolve_writable_cols()

    # ── Field resolution ──────────────────────────────────────────────────

    def _normalize_col(self, name: str) -> str:
        """Accept attr_name OR col_name; always return the col_name."""
        if name in self._col_map:
            return name
        for col, (attr, _) in self._col_map.items():
            if attr == name:
                return col
        return name  # unknown — pass through; will be filtered later

    def _resolve_cols(self) -> List[str]:
        meta = self.Meta
        exclude = set(getattr(meta, "exclude", []) or [])
        fields = getattr(meta, "fields", "__all__")
        if fields == "__all__":
            return [c for c in self._col_map if c not in exclude]
        normalized = [self._normalize_col(f) for f in fields]
        return [c for c in normalized if c in self._col_map and c not in exclude]

    def _resolve_writable_cols(self) -> List[str]:
        model = self.Meta.model
        read_only = {
            self._normalize_col(c)
            for c in (getattr(self.Meta, "read_only_fields", []) or [])
        }
        # auto_now / auto_now_add are always driven by the ORM — never user-writable
        always_ro = set(
            getattr(model, "_auto_now_cols", [])
            + getattr(model, "_auto_now_add_cols", [])
        )
        return [
            c for c in self._serializable_cols
            if c not in read_only and c not in always_ro
        ]

    # ── Serialization (output) ────────────────────────────────────────────

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        """
        Convert a model instance to a JSON-serializable dict.

        - FileField / ImageField  → URL string (or None)
        - ForeignKey              → raw ID integer (no extra query)
        - datetime / date / time  → ISO-8601 string
        - Everything else         → raw Python value
        """
        from raftsql.orm.fields import FileField, ForeignKey, OneToOneField

        data: Dict[str, Any] = {}
        for col in self._serializable_cols:
            attr_name, field_obj = self._col_map[col]
            # Use attr_name as the output key for FK/O2O (category not category_id)
            key = attr_name if isinstance(field_obj, (ForeignKey, OneToOneField)) else col
            if isinstance(field_obj, FileField):
                ff = getattr(instance, attr_name, None)
                data[key] = ff.url if (ff and ff.name) else None
            else:
                value = instance.__dict__.get(col)
                if isinstance(value, (datetime, date, time)):
                    value = value.isoformat()
                data[key] = value
        return data

    # ── Deserialization (input) ───────────────────────────────────────────

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and convert input data.

        Accepts both column names (``author_id``) and attribute names (``author``)
        as input keys.  Runs ``validate_<field>()`` hooks when present.
        """
        validated: Dict[str, Any] = {}
        errors: Dict[str, List[str]] = {}

        for col in self._writable_cols:
            attr_name, field_obj = self._col_map[col]

            if self.partial and col not in data and attr_name not in data:
                continue  # skip missing fields in partial updates

            # Accept both col_name ('author_id') and attr_name ('author') spellings
            value = data.get(col, data.get(attr_name))

            # Field-level validation hook: validate_<col> OR validate_<attr>
            hook = getattr(self, f"validate_{col}", None) or getattr(
                self, f"validate_{attr_name}", None
            )
            if callable(hook):
                try:
                    value = hook(value)
                except Exception as exc:
                    errors[col] = [str(exc)]
                    continue

            validated[col] = _coerce(value, field_obj)

        if errors:
            self._errors = errors
            raise ValueError("Validation failed")

        return validated

    # ── Persistence helpers ───────────────────────────────────────────────

    def _apply_to_instance(self, instance: Any, validated_data: Dict[str, Any]) -> None:
        """
        Write *validated_data* values onto *instance*.

        - FileField / ImageField  → ``setattr`` (triggers ``__set__``,
          which saves the file to storage and stores the path).
        - Everything else         → ``object.__setattr__`` with the column name
          (bypasses FK descriptor, sets the raw ``author_id`` directly).
        """
        from raftsql.orm.fields import FileField

        for col, value in validated_data.items():
            attr_name, field_obj = self._col_map[col]
            if isinstance(field_obj, FileField):
                setattr(instance, attr_name, value)
            else:
                object.__setattr__(instance, col, value)

    # ── Sync create / update ──────────────────────────────────────────────

    def create(self, validated_data: Dict[str, Any]) -> Any:
        instance = self.Meta.model()
        self._apply_to_instance(instance, validated_data)
        instance.save()
        return instance

    def update(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        self._apply_to_instance(instance, validated_data)
        instance.save()
        return instance

    # ── Async create / update ─────────────────────────────────────────────

    async def acreate(self, validated_data: Dict[str, Any]) -> Any:
        instance = self.Meta.model()
        self._apply_to_instance(instance, validated_data)
        await instance.asave()
        return instance

    async def aupdate(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        self._apply_to_instance(instance, validated_data)
        await instance.asave()
        return instance
