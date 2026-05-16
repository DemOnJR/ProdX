import redis

_client: redis.Redis | None = None


def init_redis(url: str) -> None:
    global _client
    _client = redis.Redis.from_url(url, decode_responses=True)


def get_client() -> redis.Redis:
    assert _client is not None
    return _client


def _key(graph_id: str) -> str:
    return f"graph:{graph_id}"


def get_graph(graph_id: str) -> str | None:
    return get_client().get(_key(graph_id))


def set_graph(graph_id: str, value: str, ttl_seconds: int) -> None:
    get_client().setex(_key(graph_id), ttl_seconds, value)


def invalidate_graph(graph_id: str) -> None:
    get_client().delete(_key(graph_id))
