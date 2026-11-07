# ── Imports & Type Definitions ──────────────────────────────────────────
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Audio Device Data Model ───────────────────────────────────────────
@dataclass
class AudioDevice:
    """Represents a discovered physical or virtual PipeWire audio output sink."""
    id: str                         # PipeWire node.name (e.g. alsa_output.pci-...)
    name: str                       # Human-readable description
    node_id: int                    # PipeWire numeric object ID
    is_default: bool = False
    channels: int = 2
    bus: str = ""
    icon_name: str = "audio-speakers"
    properties: Dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        default_tag = " [Default]" if self.is_default else ""
        return f"{self.name} (ID: {self.node_id}, Target: {self.id}){default_tag}"


# ── Device Discovery & Monitor ─────────────────────────────────────────
class DeviceMonitor:
    """Monitors and enumerates PipeWire audio output devices."""

    def __init__(self):
        self._pw_dump_available = shutil.which("pw-dump") is not None

    def get_default_sink_name(self) -> Optional[str]:
        """Detect the system default audio sink name via pactl or wpctl."""
        if shutil.which("pactl"):
            try:
                res = subprocess.run(
                    ["pactl", "get-default-sink"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=2,
                )
                output = res.stdout.strip()
                if output:
                    return output
            except Exception as e:
                logger.debug("Failed getting default sink via pactl: %s", e)

        if shutil.which("wpctl"):
            try:
                res = subprocess.run(
                    ["wpctl", "status"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=2,
                )
                # Look for * indicator under Sinks
                in_sinks = False
                for line in res.stdout.splitlines():
                    if "Sinks:" in line:
                        in_sinks = True
                        continue
                    if in_sinks:
                        if line.strip().startswith("├─") or line.strip().startswith("└─"):
                            if "Sources:" in line or "Filters:" in line or "Streams:" in line:
                                break
                        if "*" in line:
                            # e.g.: │  *   57. Built-in Audio Analog Stereo        [vol: 0.58]
                            # Extract node id or description
                            return line.split("*")[1].strip().split(".")[0].strip()
            except Exception as e:
                logger.debug("Failed getting default sink via wpctl: %s", e)

        return None

    def list_devices(self) -> List[AudioDevice]:
        """Enumerate all available Audio/Sink endpoints from PipeWire."""
        if not self._pw_dump_available:
            logger.warning("pw-dump utility not found. Unable to query PipeWire directly.")
            return []

        default_sink = self.get_default_sink_name()
        devices: List[AudioDevice] = []

        try:
            res = subprocess.run(
                ["pw-dump"],
                capture_output=True,
                text=True,
                check=True,
                timeout=3,
            )
            raw_nodes = json.loads(res.stdout)
            
            for item in raw_nodes:
                if item.get("type") != "PipeWire:Interface:Node":
                    continue
                
                info = item.get("info", {})
                props = info.get("props", {})
                
                # We only want audio output sinks
                if props.get("media.class") != "Audio/Sink":
                    continue

                node_id = item.get("id", 0)
                node_name = props.get("node.name", f"sink_{node_id}")
                description = (
                    props.get("node.description")
                    or props.get("device.description")
                    or props.get("node.nick")
                    or node_name
                )
                
                is_default = False
                if default_sink:
                    if default_sink == node_name or default_sink == str(node_id):
                        is_default = True

                channels = 2
                pos = props.get("audio.position")
                if pos and isinstance(pos, list):
                    channels = len(pos)

                bus = props.get("device.bus", "")
                icon_name = props.get("device.icon-name", "audio-speakers")

                device = AudioDevice(
                    id=node_name,
                    name=description,
                    node_id=node_id,
                    is_default=is_default,
                    channels=channels,
                    bus=bus,
                    icon_name=icon_name,
                    properties=props,
                )
                devices.append(device)

        except Exception as e:
            logger.error("Error reading PipeWire audio sinks: %s", e)

        return devices

