"""Malware scanning for user-uploaded attachments, via a local ClamAV install.

Uses `clamscan` (one-shot process, reloads the signature DB every call —
~20-25s latency on this machine) rather than `clamd`/`clamdscan` (daemon +
socket, would be much faster for repeated scans). Deliberate simplicity
trade-off for the PoC — see decision_log.md. Scanning is mandatory and
blocking: nothing downstream (PDF parsing, classification, LLM) ever sees an
attachment that hasn't passed this check.
"""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from multiagent_poc.config import settings

# clamscan exit codes: 0 = no virus found, 1 = virus(es) found, 2 = an error occurred
CLEAN, INFECTED, SCAN_ERROR = 0, 1, 2


class AttachmentRejected(Exception):
    """Raised when an attachment fails the malware scan or basic size/type checks."""


@dataclass
class ScanResult:
    clean: bool
    detail: str


def scan_file(path: Path, timeout_seconds: int = 120) -> ScanResult:
    if not path.exists():
        raise AttachmentRejected(f"attachment not found: {path}")

    if path.stat().st_size > settings.max_attachment_size_bytes:
        raise AttachmentRejected(
            f"attachment exceeds max size ({settings.max_attachment_size_bytes} bytes)"
        )

    result = subprocess.run(
        [settings.clamscan_path, "--database", settings.clamav_db_path, str(path)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )

    if result.returncode == CLEAN:
        return ScanResult(clean=True, detail="no threats found")
    if result.returncode == INFECTED:
        raise AttachmentRejected(f"malware scan flagged this file: {result.stdout.strip()}")
    raise AttachmentRejected(f"malware scan could not complete: {result.stdout} {result.stderr}".strip())
