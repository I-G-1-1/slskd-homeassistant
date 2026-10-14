from datetime import timedelta
import logging
from slskd_api import SlskdClient

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SlskdDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch slskd server state with automatic polling and debug logging."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.entry = entry
        self.entry_id = entry.entry_id
        self.uid_prefix = f"slskd_{entry.entry_id}"

        self.client = SlskdClient(
            host=entry.data[CONF_HOST],
            api_key=entry.data[CONF_API_KEY],
        )

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_HOST])},
            name="slskd Server",
            manufacturer="slskd",
            model="Soulseek Client",
            configuration_url=entry.data[CONF_HOST],
        )
        self.last_search_id: str | None = None
        self.last_search_result_count: int | None = None
        self.last_search_state: str | None = None
        self.last_search_results: list | None = None
        self.last_download_username: str | None = None
        self.last_download_filename: str | None = None
        self.last_download_state: str | None = None
        self.last_download_bytes_transferred: int | None = None
        self.last_download_size: int | None = None
        self.last_download_average_speed: float | None = None
        self.active_downloads_count: int = 0
        self.completed_downloads_count: int = 0
        self.queued_downloads_count: int = 0
        self.errored_downloads_count: int = 0
        self.total_downloads_count: int = 0
        self.download_progress_pct: float = 0.0
        self.active_uploads_count: int = 0
        self.shared_files_count: int = 0
        self.current_download_speed_bps: float = 0.0
        self.current_upload_speed_bps: float = 0.0
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name="slskd server state",
            update_interval=timedelta(seconds=scan_interval),
            update_method=self.async_update_data,
        )

    async def async_update_data(self):
        """Fetch data from slskd, including the latest search and download."""
        _LOGGER.debug("Fetching slskd server state...")
        try:
            data = await self.hass.async_add_executor_job(self.client.server.state)
        except Exception as err:
            _LOGGER.error("Error fetching slskd server state: %s", err)
            raise UpdateFailed from err

        # --- Latest search ---
        try:
            searches = await self.hass.async_add_executor_job(
                self.client.searches.get_all
            )
            if searches:
                latest = max(
                    searches,
                    key=lambda s: s.get("startedAt") or "",
                )
                self.last_search_id = latest.get("id")
                self.last_search_result_count = (
                    latest.get("fileCount")
                    or latest.get("file_count")
                    or 0
                )
                self.last_search_state = latest.get("state") or "Unknown"

                if (
                    self.last_search_state
                    and self.last_search_state.startswith("Completed")
                ):
                    responses = await self.hass.async_add_executor_job(
                        self.client.searches.search_responses,
                        self.last_search_id,
                    )
                    self.last_search_results = _extract_top_results(responses)
        except Exception as err:
            _LOGGER.warning("Could not fetch searches: %s", err)

        # --- Latest download ---
        try:
            all_downloads = await self.hass.async_add_executor_job(
                self.client.transfers.get_all_downloads
            )
            best = None
            for user_obj in all_downloads or []:
                username = user_obj.get("username")
                for directory in user_obj.get("directories", []):
                    for f in directory.get("files", []):
                        ts = (
                            f.get("startedAt")
                            or f.get("enqueuedAt")
                            or ""
                        )
                        if best is None or ts > best[0]:
                            best = (ts, username, f)
            if best:
                _, username, f = best
                self.last_download_username = username
                self.last_download_filename = f.get("filename")
                self.last_download_state = f.get("state") or "Unknown"
                self.last_download_bytes_transferred = (
                    f.get("bytesTransferred")
                    or f.get("bytes_transferred")
                    or 0
                )
                self.last_download_size = f.get("size") or 0
                self.last_download_average_speed = (
                    f.get("averageSpeed")
                    or f.get("average_speed")
                    or 0.0
                )
                _LOGGER.debug(
                    "Latest download: %s from %s state=%s",
                    self.last_download_filename,
                    username,
                    self.last_download_state,
                )
        except Exception as err:
            _LOGGER.warning("Could not fetch downloads: %s", err)

        # --- Download statistics ---
        active_dl = 0
        completed_dl = 0
        queued_dl = 0
        errored_dl = 0
        total_dl_speed = 0.0
        try:
            all_downloads = await self.hass.async_add_executor_job(
                self.client.transfers.get_all_downloads
            )
            for user_obj in all_downloads or []:
                for directory in user_obj.get("directories", []):
                    for f in directory.get("files", []):
                        state = f.get("state") or ""
                        if state == "InProgress":
                            active_dl += 1
                            total_dl_speed += (
                                f.get("averageSpeed")
                                or f.get("average_speed")
                                or 0
                            )
                        elif state == "Queued" or state.startswith("Queued"):
                            queued_dl += 1
                        elif state.startswith("Completed, Succeeded"):
                            completed_dl += 1
                        elif state.startswith("Completed, Errored") or state == "Errored":
                            errored_dl += 1
                        # "Completed, Cancelled" is not counted in any category
        except Exception as err:
            _LOGGER.warning("Could not fetch downloads: %s", err)

        self.active_downloads_count = active_dl
        self.completed_downloads_count = completed_dl
        self.queued_downloads_count = queued_dl
        self.errored_downloads_count = errored_dl
        self.total_downloads_count = active_dl + completed_dl + queued_dl + errored_dl

        # Progress: completed / (completed + active + queued + errored)
        denom = completed_dl + active_dl + queued_dl + errored_dl
        self.download_progress_pct = (
            round(completed_dl / denom * 100, 1) if denom > 0 else 0.0
        )
        self.current_download_speed_bps = total_dl_speed

        # --- Upload statistics ---
        active_ul = 0
        total_ul_speed = 0.0
        try:
            all_uploads = await self.hass.async_add_executor_job(
                self.client.transfers.get_all_uploads
            )
            for user_obj in all_uploads or []:
                for directory in user_obj.get("directories", []):
                    for f in directory.get("files", []):
                        state = f.get("state") or ""
                        if state == "InProgress":
                            active_ul += 1
                            total_ul_speed += (
                                f.get("averageSpeed")
                                or f.get("average_speed")
                                or 0
                            )
        except Exception as err:
            _LOGGER.warning("Could not fetch uploads: %s", err)

        self.active_uploads_count = active_ul
        self.current_upload_speed_bps = total_ul_speed

        # --- Shared files ---
        try:
            shares_data = await self.hass.async_add_executor_job(
                self.client.shares.get_all
            )
            total_files = 0

            # The response can be a dict with "local" and "remote",
            # or a list of share objects.
            if isinstance(shares_data, dict):
                # Dict case: sum files from "local" and "remote"
                for key in ("local", "remote"):
                    for s in shares_data.get(key) or []:
                        total_files += (
                            s.get("files")
                            or s.get("fileCount")
                            or 0
                        )
            elif isinstance(shares_data, list):
                # List case: iterate directly
                for s in shares_data:
                    total_files += (
                        s.get("files")
                        or s.get("fileCount")
                        or 0
                    )

            self.shared_files_count = total_files
        except Exception as err:
            _LOGGER.warning("Could not fetch shares: %s", err)

        return data


def _normalise_path(p: str) -> str:
    """Strip leading backslashes and normalise separators for comparison."""
    return p.replace("\\\\", "\\").lstrip("\\")


def _find_download(downloads, filename: str) -> dict | None:
    """Find a specific file transfer in the downloads response.

    The user-specific endpoint returns a single user object:
      {"username": "...", "directories": [{"directory": "...", "files": [{transfer}]}]}
    The all-users endpoint returns a list of such objects.
    Both shapes are handled here.
    """
    target = _normalise_path(filename)
    # Normalise to a list of user objects regardless of which endpoint was called.
    user_objects = [downloads] if isinstance(downloads, dict) else (downloads or [])
    for user_obj in user_objects:
        for directory in user_obj.get("directories", []):
            for f in directory.get("files", []):
                if _normalise_path(f.get("filename", "")) == target:
                    return f
    return None


def _extract_top_results(responses, limit: int = 10) -> list:
    """Flatten search responses into a sorted top-N file list."""
    files = []
    for response in responses or []:
        username = response.get("username", "")
        upload_speed = response.get("uploadSpeed", 0)
        for f in response.get("files", []):
            files.append({
                "username": username,
                "filename": f.get("filename", ""),
                "size": f.get("size", 0),
                "bitrate": f.get("bitRate", 0),
                "bit_depth": f.get("bitDepth", 0),
                "sample_rate": f.get("sampleRate", 0),
                "upload_speed": upload_speed,
            })
    files.sort(key=lambda x: (x["upload_speed"], x["bitrate"], x["size"]), reverse=True)
    return files[:limit]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the binary sensor."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SlskdConnectionBinarySensor(coordinator)])


class SlskdConnectionBinarySensor(BinarySensorEntity):
    """Binary sensor for slskd connection status."""

    _attr_name = "slskd Connected"
    _attr_device_class = "connectivity"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.uid_prefix}_connected"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self):
        """Register entity with coordinator to receive updates automatically."""
        self.coordinator.async_add_listener(self.async_write_ha_state)
        # Ensure first poll happens immediately if coordinator hasn't run yet
        if self.coordinator.last_update_success is None:
            await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return True if server is connected."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("isConnected", False)

    @property
    def extra_state_attributes(self):
        """Additional attributes."""
        if not self.coordinator.data:
            return {}
        return {
            "username": self.coordinator.data.get("username"),
            "listen_port": self.coordinator.data.get("listenPort"),
            "uptime": self.coordinator.data.get("uptime"),
        }

    @property
    def available(self) -> bool:
        """Return True if the coordinator data is valid."""
        return self.coordinator.last_update_success