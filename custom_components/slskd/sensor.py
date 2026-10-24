import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .binary_sensor import SlskdDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up slskd sensors."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SlskdSearchResultSensor(coordinator),
        SlskdLastDownloadSensor(coordinator),
        SlskdDownloadSpeedSensor(coordinator),
        SlskdUploadSpeedSensor(coordinator),
        SlskdActiveDownloadsSensor(coordinator),
        SlskdCompletedDownloadsSensor(coordinator),
        SlskdQueuedDownloadsSensor(coordinator),
        SlskdErroredDownloadsSensor(coordinator),
        SlskdTotalDownloadsSensor(coordinator),
        SlskdDownloadProgressSensor(coordinator),
        SlskdActiveUploadsSensor(coordinator),
        SlskdSharedFilesSensor(coordinator),
    ])


class SlskdSearchResultSensor(SensorEntity):
    """Sensor reporting the total file count of the last slskd search."""

    _attr_name = "slskd Last Search Result Total"
    _attr_native_unit_of_measurement = "files"
    _attr_unique_id = "slskd_last_search_result_total"
    _attr_icon = "mdi:file-search-outline"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_last_search_result_total"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.last_search_result_count

    @property
    def extra_state_attributes(self):
        return {
            "search_id": self.coordinator.last_search_id,
            "search_state": self.coordinator.last_search_state,
            "results": self.coordinator.last_search_results,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdLastDownloadSensor(SensorEntity):
    """Sensor reporting the status of the last initiated download."""

    _attr_name = "slskd Last Download Status"
    _attr_unique_id = "slskd_last_download_status"
    _attr_icon = "mdi:download-circle-outline"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_last_download_status"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        # Return "None" instead of None to avoid Home Assistant showing "Unknown"
        if self.coordinator.last_download_state is None:
            return "None"
        return self.coordinator.last_download_state

    @property
    def extra_state_attributes(self):
        filename = self.coordinator.last_download_filename
        size = self.coordinator.last_download_size
        transferred = self.coordinator.last_download_bytes_transferred
        speed = self.coordinator.last_download_average_speed
        attrs = {
            "username": self.coordinator.last_download_username,
            "filename": filename.split("\\")[-1] if filename else None,
            "full_path": filename,
            "bytes_transferred": transferred,
            "size": size,
            "average_speed_bps": speed,
        }
        if size and transferred is not None and size > 0:
            attrs["progress_pct"] = round(transferred / size * 100, 1)
        return attrs

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdDownloadSpeedSensor(SensorEntity):
    """Sensor reporting the aggregate current download speed."""

    _attr_name = "slskd Download Speed"
    _attr_unique_id = "slskd_download_speed"
    _attr_native_unit_of_measurement = "B/s"
    _attr_device_class = "data_rate"
    _attr_state_class = "measurement"
    _attr_icon = "mdi:download"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_download_speed"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return round(self.coordinator.current_download_speed_bps, 0)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdUploadSpeedSensor(SensorEntity):
    """Sensor reporting the aggregate current upload speed."""

    _attr_name = "slskd Upload Speed"
    _attr_unique_id = "slskd_upload_speed"
    _attr_native_unit_of_measurement = "B/s"
    _attr_device_class = "data_rate"
    _attr_state_class = "measurement"
    _attr_icon = "mdi:upload"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_upload_speed"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return round(self.coordinator.current_upload_speed_bps, 0)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdActiveDownloadsSensor(SensorEntity):
    _attr_name = "slskd Active Downloads"
    _attr_unique_id = "slskd_active_downloads"
    _attr_icon = "mdi:download-box"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_active_downloads"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.active_downloads_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdCompletedDownloadsSensor(SensorEntity):
    _attr_name = "slskd Completed Downloads"
    _attr_unique_id = "slskd_completed_downloads"
    _attr_icon = "mdi:download-circle"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_completed_downloads"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.completed_downloads_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdQueuedDownloadsSensor(SensorEntity):
    _attr_name = "slskd Queued Downloads"
    _attr_unique_id = "slskd_queued_downloads"
    _attr_icon = "mdi:tray-full"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_queued_downloads"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.queued_downloads_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdErroredDownloadsSensor(SensorEntity):
    _attr_name = "slskd Errored Downloads"
    _attr_unique_id = "slskd_errored_downloads"
    _attr_icon = "mdi:download-off"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_errored_downloads"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.errored_downloads_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdTotalDownloadsSensor(SensorEntity):
    _attr_name = "slskd Total Downloads"
    _attr_unique_id = "slskd_total_downloads"
    _attr_icon = "mdi:download-multiple"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_total_downloads"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.total_downloads_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdDownloadProgressSensor(SensorEntity):
    _attr_name = "slskd Download Progress"
    _attr_unique_id = "slskd_download_progress"
    _attr_icon = "mdi:progress-download"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = "measurement"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_download_progress"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.download_progress_pct

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdActiveUploadsSensor(SensorEntity):
    _attr_name = "slskd Active Uploads"
    _attr_unique_id = "slskd_active_uploads"
    _attr_icon = "mdi:upload-box"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_active_uploads"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.active_uploads_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class SlskdSharedFilesSensor(SensorEntity):
    _attr_name = "slskd Shared Files"
    _attr_unique_id = "slskd_shared_files"
    _attr_icon = "mdi:folder-multiple"
    _attr_native_unit_of_measurement = "files"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_shared_files"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.shared_files_count

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success