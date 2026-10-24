import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_API_KEY_ROLE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_API_KEY_ROLE,
    API_KEY_ROLES,
)


class SlskdConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for slskd."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            api_key = user_input[CONF_API_KEY]
            role = user_input[CONF_API_KEY_ROLE]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Validate the API key against an endpoint appropriate to the role
            try:
                from slskd_api import SlskdClient
                client = SlskdClient(host=host, api_key=api_key)
                if role == "readwrite":
                    state = await self.hass.async_add_executor_job(
                        client.server.state
                    )
                    if not state:
                        errors["base"] = "cannot_connect"
                else:
                    # read-only validation: use a known read-only endpoint
                    await self.hass.async_add_executor_job(
                        client.transfers.get_all_downloads
                    )
            except Exception:
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"slskd ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_API_KEY: api_key,
                        CONF_API_KEY_ROLE: role,
                    },
                )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default="http://localhost:5030"): str,
            vol.Required(CONF_API_KEY): str,
            vol.Required(
                CONF_API_KEY_ROLE, default=DEFAULT_API_KEY_ROLE
            ): vol.In(API_KEY_ROLES),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SlskdOptionsFlowHandler()


class SlskdOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for slskd integration."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # self.config_entry is set automatically by modern Home Assistant.
        entry = getattr(self, "config_entry", None)

        current_role = DEFAULT_API_KEY_ROLE
        current_interval = DEFAULT_SCAN_INTERVAL
        if entry is not None:
            current_role = entry.options.get(
                CONF_API_KEY_ROLE,
                entry.data.get(CONF_API_KEY_ROLE, DEFAULT_API_KEY_ROLE),
            )
            current_interval = entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )

        schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL, default=current_interval
            ): int,
            vol.Optional(
                CONF_API_KEY_ROLE, default=current_role
            ): vol.In(API_KEY_ROLES),
        })

        return self.async_show_form(step_id="init", data_schema=schema)