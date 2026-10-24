import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_API_KEY_ROLE, DEFAULT_API_KEY_ROLE
from .binary_sensor import SlskdDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the slskd button."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    role = entry.options.get(
        CONF_API_KEY_ROLE,
        entry.data.get(CONF_API_KEY_ROLE, DEFAULT_API_KEY_ROLE),
    )

    _LOGGER.debug("Setting up slskd button platform (role=%s)", role)

    # The rescan action requires write privileges
    if role == "readwrite":
        async_add_entities([SlskdRescanSharesButton(coordinator)])
        _LOGGER.debug("SlskdRescanSharesButton added")
    else:
        _LOGGER.debug("Skipping SlskdRescanSharesButton due to readonly role")


class SlskdRescanSharesButton(ButtonEntity):
    """Button to trigger a rescan of slskd shared files."""

    _attr_name = "slskd Rescan Shares"
    _attr_icon = "mdi:folder-refresh"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_rescan_shares"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Triggering slskd share rescan...")
        try:
            # The slskd-api method for PUT /api/v0/shares is start_scan
            await self.hass.async_add_executor_job(
                self.coordinator.client.shares.start_scan
            )
            _LOGGER.info("Share rescan requested successfully.")
        except Exception as err:
            _LOGGER.error("Failed to trigger share rescan: %s", err)