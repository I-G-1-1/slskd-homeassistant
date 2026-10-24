DOMAIN = "slskd"

CONF_HOST = "host"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_API_KEY_ROLE = "api_key_role"

DEFAULT_SCAN_INTERVAL = 10  # seconds

# Backwards-compatible default: existing entries (created before the role
# option existed) are assumed to be using a readwrite-level key. Existing
# users with a readonly key can change this via the integration's
# "Configure" dialog.
DEFAULT_API_KEY_ROLE = "readwrite"
API_KEY_ROLES = ["readonly", "readwrite"]