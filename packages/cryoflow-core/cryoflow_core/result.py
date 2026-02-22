"""A convenient wrapper function to make the `returns` library easier to use."""

from typing import Callable, Type, TypeVar

from returns.result import Result

ExcT = TypeVar('ExcT', bound=Exception)
A = TypeVar('A')
B = TypeVar('B')


def bind_safe(
    error_cls: Type[ExcT],
) -> Callable[[Callable[[A], Result[B, Exception]], str], Callable[[A], Result[B, ExcT]]]:
    """Curry a @safe-decorated function into a bind-compatible form with error mapping.

    Takes an exception class and returns a function that wraps a @safe function
    for use with Result.bind(), converting any Failure to the given error class.

    Args:
        error_cls: The exception class to wrap failures with.

    Returns:
        A function that accepts a @safe function and an error message string,
        and returns a callable suitable for use with Result.bind().

    Example:
        >>> bind_config = bind_safe(ConfigLoadError)
        >>> result = (
        ...     _read_file(path)
        ...     .bind(bind_config(_parse_toml, 'Failed to parse TOML config'))
        ... )
    """

    def inner(
        fn: Callable[[A], Result[B, Exception]],
        error_msg: str,
    ) -> Callable[[A], Result[B, ExcT]]:
        return lambda x: fn(x).alt(lambda e: error_cls(f'{error_msg}: {e}'))

    return inner
