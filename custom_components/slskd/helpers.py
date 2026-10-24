from slskd_api import SlskdClient


def get_server_state(client: SlskdClient) -> dict:
    """Return the slskd server state.

    slskd 0.26.2+ restricts GET /api/v0/server to Administrator API keys, so read
    the same ServerState from GET /api/v0/application, which any key can access.
    """
    app_state = client.application.state() or {}
    server = dict(app_state.get("server") or {})
    server.setdefault("username", (app_state.get("user") or {}).get("username"))
    return server