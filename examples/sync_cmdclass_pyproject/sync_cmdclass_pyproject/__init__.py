from typing import Any, Callable, Optional, Sequence, Set, Tuple


def foo(
    a: Any,
    b: Callable[[], Tuple[int, int, str]],
    c: Set[str],
    d: Optional[Sequence[int]] = None,
    e: Any = None,
) -> None:
    pass


print("Hello world")
foo(a=1, b=lambda: (1, 2, "hoge"), c=set(), d=None, e=None)
