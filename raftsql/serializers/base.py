"""
Base Serializer — DRF-style input/output, framework-agnostic.
No external dependencies beyond the Python standard library.
"""
import asyncio
from typing import Any, Dict, List, Optional


class Serializer:
    """
    Base serializer.  Subclass this (or ModelSerializer) and override
    to_representation(), to_internal_value(), create(), and update().

    Usage::

        class PostSerializer(Serializer):
            def to_representation(self, instance):
                return {"id": instance.id, "title": instance.title}

            def to_internal_value(self, data):
                return {"title": data["title"]}

            def create(self, validated_data):
                return Post.objects.create(**validated_data)

            def update(self, instance, validated_data):
                for k, v in validated_data.items():
                    setattr(instance, k, v)
                instance.save()
                return instance

        # Serialize
        s = PostSerializer(post_instance)
        print(s.data)

        # Deserialize + save (sync)
        s = PostSerializer(data={"title": "Hello"})
        if s.is_valid():
            post = s.save()

        # Deserialize + save (async)
        s = PostSerializer(data={"title": "Hello"})
        if await s.is_valid_async():
            post = await s.asave()

        # Partial update
        s = PostSerializer(post_instance, data={"title": "New"}, partial=True)
        if s.is_valid():
            post = s.save()

        # List serialization
        s = PostSerializer(queryset, many=True)
        print(s.data)  # list of dicts
    """

    def __init__(
        self,
        instance: Any = None,
        *,
        data: Optional[Dict[str, Any]] = None,
        many: bool = False,
        partial: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.instance = instance
        self.initial_data: Dict[str, Any] = data if data is not None else {}
        self._validated_data: Optional[Dict[str, Any]] = None
        self._cached_data: Optional[Any] = None
        self._errors: Optional[Dict[str, List[str]]] = None
        self.many = many
        self.partial = partial
        self.context: Dict[str, Any] = context or {}

    # ── Output ────────────────────────────────────────────────────────────

    @property
    def data(self) -> Any:
        """Serialized representation of the instance(s)."""
        if self._cached_data is not None:
            return self._cached_data
        if self.instance is not None:
            if self.many:
                self._cached_data = [self.to_representation(item) for item in self.instance]
            else:
                self._cached_data = self.to_representation(self.instance)
        else:
            self._cached_data = {}
        return self._cached_data

    # ── Validation ────────────────────────────────────────────────────────

    @property
    def errors(self) -> Dict[str, List[str]]:
        """Validation errors after is_valid() returns False."""
        return self._errors or {}

    @property
    def validated_data(self) -> Dict[str, Any]:
        """Validated input data — only accessible after a successful is_valid()."""
        if self._validated_data is None:
            raise AssertionError(
                "You must call .is_valid() before accessing .validated_data"
            )
        return self._validated_data

    def _run_validation(self, raise_exception: bool = False) -> bool:
        self._errors = {}
        try:
            validated = self.to_internal_value(self.initial_data)
            validated = self.validate(validated)
            self._validated_data = validated
            return True
        except Exception as exc:
            if not self._errors:
                self._errors = {"non_field_errors": [str(exc)]}
            if raise_exception:
                raise
            return False

    def is_valid(self, raise_exception: bool = False) -> bool:
        """Validate input data synchronously.  Returns True if valid."""
        return self._run_validation(raise_exception)

    async def is_valid_async(self, raise_exception: bool = False) -> bool:
        """
        Async version of is_valid().

        Validation is pure Python (no I/O), so this runs inline — no thread
        pool wrapping.  Override this method if you need async DB lookups
        inside your validate_<field>() hooks.
        """
        return self._run_validation(raise_exception)

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, **extra: Any) -> Any:
        """
        Persist validated data.  Calls create() or update() automatically.
        *extra* keyword arguments are merged into validated_data (last-wins).
        """
        if self._validated_data is None:
            raise AssertionError("You must call .is_valid() before .save()")
        merged = {**self._validated_data, **extra}
        if self.instance is not None:
            self.instance = self.update(self.instance, merged)
        else:
            self.instance = self.create(merged)
        self._cached_data = None  # invalidate output cache
        return self.instance

    async def asave(self, **extra: Any) -> Any:
        """Async version of save()."""
        if self._validated_data is None:
            raise AssertionError("You must call .is_valid() before .asave()")
        merged = {**self._validated_data, **extra}
        if self.instance is not None:
            self.instance = await self.aupdate(self.instance, merged)
        else:
            self.instance = await self.acreate(merged)
        self._cached_data = None
        return self.instance

    # ── Override these ────────────────────────────────────────────────────

    def create(self, validated_data: Dict[str, Any]) -> Any:
        """Create and return a new instance from validated_data."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.create() must be implemented."
        )

    def update(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        """Update and return *instance* using validated_data."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.update() must be implemented."
        )

    async def acreate(self, validated_data: Dict[str, Any]) -> Any:
        """Async create — by default wraps sync create() in a thread."""
        return await asyncio.to_thread(self.create, validated_data)

    async def aupdate(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        """Async update — by default wraps sync update() in a thread."""
        return await asyncio.to_thread(self.update, instance, validated_data)

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        """Convert a model instance to a JSON-serializable dict."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.to_representation() must be implemented."
        )

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw input to internal Python values.
        Default implementation passes all keys through, running any
        validate_<field>() hooks that exist on the serializer.
        """
        validated: Dict[str, Any] = {}
        for key, value in data.items():
            hook = getattr(self, f"validate_{key}", None)
            if callable(hook):
                value = hook(value)
            validated[key] = value
        return validated

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-field validation hook.  Override for custom logic."""
        return data
