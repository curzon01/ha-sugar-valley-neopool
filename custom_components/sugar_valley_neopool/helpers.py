"""Helper functions for NeoPool MQTT integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, overload

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def get_nested_value(data: dict[str, Any], path: str) -> Any | None:
    """Get a value from nested dictionary using dot notation path.

    Example: get_nested_value(data, "NeoPool.pH.Data")
    returns data["NeoPool"]["pH"]["Data"]
    """
    keys = path.split(".")
    value = data

    try:
        for key in keys:
            if isinstance(value, dict):
                value = value[key]
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)]
            else:
                return None
    except (KeyError, IndexError, TypeError):
        return None
    else:
        return value


def parse_runtime_duration(duration_str: str) -> float | None:
    """Parse NeoPool runtime duration format (DDDThh:mm:ss) to hours.

    Example: "123T04:30:00" -> 123*24 + 4 + 30/60 = 2956.5 hours
    """
    if not duration_str or "T" not in duration_str:
        return None

    try:
        days_part, time_part = duration_str.split("T")
        days = int(days_part)
        hours, minutes, seconds = map(int, time_part.split(":"))

        total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
        return round(total_hours, 2)
    except (ValueError, AttributeError):
        _LOGGER.warning("Failed to parse runtime duration: %s", duration_str)
        return None


def parse_json_payload(payload: str | bytes | bytearray) -> dict[str, Any] | None:
    """Parse MQTT JSON payload safely."""
    try:
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        return json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        _LOGGER.debug("Failed to parse JSON payload: %s", ex)
        return None


def lookup_by_value(mapping: dict[Any, str], value: str) -> Any | None:
    """Reverse lookup: find key by value in a dictionary."""
    for key, val in mapping.items():
        if val == value:
            return key
    return None


def bit_to_bool(value: str | int) -> bool | None:
    """Convert bit string/int to boolean."""
    if value in ("1", 1):
        return True
    if value in ("0", 0):
        return False
    return None


def int_to_bool(value: str | int) -> bool:
    """Convert any positive integer to True."""
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


@overload
def safe_float(value: Any) -> float | None: ...
@overload
def safe_float(value: Any, default: None) -> float | None: ...
@overload
def safe_float(value: Any, default: float) -> float: ...
def safe_float(value: Any, default: float | None = None) -> float | None:
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


@overload
def safe_int(value: Any) -> int | None: ...
@overload
def safe_int(value: Any, default: None) -> int | None: ...
@overload
def safe_int(value: Any, default: int) -> int: ...
def safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert value to int."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def validate_nodeid(nodeid: str | None) -> bool:
    """Validate NodeID is present and not 'hidden' or masked.

    Args:
        nodeid: The NodeID value to validate.

    Returns:
        True if NodeID is valid (present, not hidden, and not masked), False otherwise.
    """
    if nodeid is None or nodeid == "":
        return False
    if isinstance(nodeid, str):
        nodeid_lower = nodeid.lower()
        # Check for literal hidden values
        if nodeid_lower in ["hidden", "hidden_by_default"]:
            return False
        # Check for masked NodeID pattern (contains XXXX when SetOption157 is 0)
        if "xxxx" in nodeid_lower:
            return False
    return True


def normalize_nodeid(nodeid: str | None) -> str:
    """Normalize NodeID for use in unique_ids and identifiers.

    The real NodeID from Tasmota is a hex string like '4C7525BFB344'.
    Masked NodeIDs have spaces like 'XXXX XXXX XXXX XXXX XXXX 3435'.
    This function removes spaces and ensures a clean identifier.

    Args:
        nodeid: The NodeID value to normalize, or None.

    Returns:
        Normalized NodeID string (uppercase, no spaces), or empty string if None.
    """
    if not nodeid:
        return ""
    # Remove spaces and convert to uppercase for consistency
    return nodeid.replace(" ", "").upper()


def is_masked_unique_id(unique_id: str) -> bool:
    """Check if a unique_id contains a masked NodeID pattern.

    Masked NodeIDs appear when Tasmota SetOption157 is disabled (0).
    They contain 'XXXX' patterns like 'neopool_mqtt_XXXX XXXX XXXX XXXX XXXX 3435_ph_data'.

    Args:
        unique_id: The entity unique_id to check.

    Returns:
        True if the unique_id contains masked NodeID pattern, False otherwise.
    """
    if not unique_id:
        return False
    return "xxxx" in unique_id.lower()


def extract_entity_key_from_masked_unique_id(unique_id: str) -> str | None:
    """Extract the entity key from a masked unique_id.

    Given: 'neopool_mqtt_XXXX XXXX XXXX XXXX XXXX 3435_ph_data'
    Returns: 'ph_data'

    The format is: neopool_mqtt_{masked_nodeid}_{entity_key}
    where masked_nodeid contains spaces and 'XXXX' patterns.

    Args:
        unique_id: The masked unique_id to extract from.

    Returns:
        The entity key (e.g., 'ph_data'), or None if extraction failed.
    """
    if not unique_id or not unique_id.startswith("neopool_mqtt_"):
        return None

    # Remove the prefix
    remainder = unique_id[len("neopool_mqtt_") :]

    # The entity_key is the part after the last underscore that follows a digit
    # Pattern: {masked_nodeid}_{entity_key}
    # masked_nodeid ends with digits like "3435"
    # We need to find where the masked NodeID ends and entity_key begins

    # Split by underscore and find where NodeID ends
    # NodeID pattern ends with digits, entity_key starts with letters
    parts = remainder.rsplit("_", 1)

    # Keep splitting until we find a part that looks like an entity key
    # (doesn't contain XXXX and isn't just digits)
    while len(parts) == 2:
        potential_key = parts[1]
        potential_nodeid = parts[0]

        # If the potential_nodeid still contains XXXX or ends with digits followed by _
        # and potential_key looks like an entity key (no XXXX, not just digits)
        if "xxxx" not in potential_key.lower() and not potential_key.isdigit():
            # Check if we need to include more parts in the key
            # e.g., "hydrolysis_runtime_total" should be the full key
            if "xxxx" in potential_nodeid.lower():
                # Found the boundary - potential_key is the start of entity_key
                # But we may have split too early, need to find the real boundary
                # The NodeID ends where XXXX pattern ends followed by digits
                break

        parts = potential_nodeid.rsplit("_", 1)
        if len(parts) == 2:
            parts = [parts[0], parts[1] + "_" + potential_key]
        else:
            break

    if len(parts) == 2 and "xxxx" in parts[0].lower():
        return parts[1]

    return None


async def async_query_setoption157(hass: HomeAssistant, mqtt_topic: str) -> bool | None:
    """Query SetOption157 status from Tasmota via MQTT.

    Shared helper function used by ConfigFlow, OptionsFlow, and migration.

    Args:
        hass: Home Assistant instance
        mqtt_topic: The MQTT topic prefix for the device

    Returns:
        True if enabled, False if disabled, None if query failed.
    """
    # Import mqtt here to avoid circular imports
    from homeassistant.components import mqtt  # noqa: PLC0415
    from homeassistant.core import callback  # noqa: PLC0415

    if not mqtt_topic:
        _LOGGER.warning("No MQTT topic provided, cannot query SetOption157")
        return None

    result: bool | None = None
    event = asyncio.Event()

    @callback
    def message_received(msg: mqtt.ReceiveMessage) -> None:
        """Handle SetOption157 response."""
        nonlocal result
        try:
            payload = json.loads(msg.payload)
            # Response format: {"SetOption157":"ON"} or {"SetOption157":"OFF"}
            so157_value = payload.get("SetOption157")
            if so157_value is not None:
                result = so157_value.upper() == "ON"
                _LOGGER.debug("SetOption157 status for %s: %s", mqtt_topic, result)
                event.set()
        except (json.JSONDecodeError, AttributeError) as err:
            _LOGGER.debug("Failed to parse SetOption157 response: %s", err)

    # Subscribe to result topic
    result_topic = f"stat/{mqtt_topic}/RESULT"
    unsubscribe = await mqtt.async_subscribe(hass, result_topic, message_received, qos=1)

    try:
        # Send query command (empty payload queries current value)
        command_topic = f"cmnd/{mqtt_topic}/SetOption157"
        await mqtt.async_publish(hass, command_topic, "", qos=1, retain=False)

        # Wait for response with timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=5.0)
        except TimeoutError:
            _LOGGER.warning("Timeout waiting for SetOption157 response from %s", mqtt_topic)
    finally:
        unsubscribe()

    return result


async def async_set_setoption157(hass: HomeAssistant, mqtt_topic: str, enable: bool) -> bool:
    """Set SetOption157 on Tasmota device via MQTT.

    Args:
        hass: Home Assistant instance
        mqtt_topic: The MQTT topic prefix for the device
        enable: True to enable (show NodeID), False to disable (mask NodeID)

    Returns:
        True if the command was sent successfully, False otherwise.
    """
    # Import mqtt here to avoid circular imports
    from homeassistant.components import mqtt  # noqa: PLC0415

    if not mqtt_topic:
        _LOGGER.warning("No MQTT topic provided, cannot set SetOption157")
        return False

    command_topic = f"cmnd/{mqtt_topic}/SetOption157"
    payload = "1" if enable else "0"

    try:
        await mqtt.async_publish(hass, command_topic, payload, qos=1, retain=False)
    except Exception:
        _LOGGER.exception("Failed to send SetOption157 command to %s", mqtt_topic)
        return False
    else:
        _LOGGER.debug("Sent SetOption157 %s to %s", payload, mqtt_topic)
        return True
