"""Static smoke tests: no postgres, no redis, no live API. Just confirm that
the app imports cleanly and the bundled graph payload is well-formed.

The real integration check is the readiness probe in the running cluster
(GET /health hitting the api Service). What we cover here is everything
upstream of that: code parses, settings load, seed is structurally valid.
"""


def test_app_imports_with_expected_metadata():
    from app.main import app

    assert app.title == "ProdX API"


def test_seed_graph_has_nodes_and_edges():
    from app.seed import PRODX_GRAPH

    assert isinstance(PRODX_GRAPH, dict)
    nodes = PRODX_GRAPH.get("nodes")
    edges = PRODX_GRAPH.get("edges")
    assert isinstance(nodes, list) and len(nodes) > 0, "seed must define at least one node"
    assert isinstance(edges, list) and len(edges) > 0, "seed must define at least one edge"


def test_seed_node_ids_are_unique():
    from app.seed import PRODX_GRAPH

    ids = [n["id"] for n in PRODX_GRAPH["nodes"]]
    assert len(ids) == len(set(ids)), f"duplicate node ids: {ids}"


def test_seed_edges_reference_existing_nodes():
    from app.seed import PRODX_GRAPH

    node_ids = {n["id"] for n in PRODX_GRAPH["nodes"]}
    for edge in PRODX_GRAPH["edges"]:
        assert edge["source"] in node_ids, f"edge source {edge['source']!r} not a node"
        assert edge["target"] in node_ids, f"edge target {edge['target']!r} not a node"


def test_graph_payload_schema_round_trip():
    """Seed payload must validate against the API's request schema."""
    from app.schemas import GraphPayload
    from app.seed import PRODX_GRAPH

    payload = GraphPayload(**PRODX_GRAPH)
    assert payload.nodes == PRODX_GRAPH["nodes"]
    assert payload.edges == PRODX_GRAPH["edges"]
