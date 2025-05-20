from uuid import uuid4

from fastapi.routing import APIRoute


def uuid4_str() -> str:
    """Generate a random UUID4 string."""
    return str(uuid4())


def rgb(r, g, b):
    """RGB text."""
    return f'\033[38;2;{r};{g};{b}m'


def generate_unique_id(route: APIRoute) -> str:
    """Generate a unique ID for a route."""
    return f'{route.tags[0]}-{route.name}'
