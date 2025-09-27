from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, List, Optional


@dataclass
class TranscriptEntry:
    role: str
    content: str
    timestamp: float


@dataclass
class BookingStatus:
    status: str = "pending"  # pending | confirmed | failed
    booking_id: Optional[str] = None
    room_id: Optional[str] = None
    check_in_time: Optional[str] = None
    key_token: Optional[str] = None
    payment_required: bool = False


@dataclass
class SessionRecord:
    session_id: str
    call_type: str  # outreach | booking
    brief: Dict[str, str] = field(default_factory=dict)
    transcript: List[TranscriptEntry] = field(default_factory=list)
    summary: Optional[Dict[str, str]] = None
    booking_status: BookingStatus = field(default_factory=BookingStatus)


class SessionStore:
    """Thread-safe in-memory session cache."""

    def __init__(self) -> None:
        self._records: Dict[str, SessionRecord] = {}
        self._lock = RLock()

    def upsert(self, record: SessionRecord) -> None:
        with self._lock:
            self._records[record.session_id] = record

    def get(self, session_id: str) -> Optional[SessionRecord]:
        with self._lock:
            return self._records.get(session_id)

    def all(self) -> List[SessionRecord]:
        with self._lock:
            return list(self._records.values())

    def append_transcript(self, session_id: str, entry: TranscriptEntry) -> None:
        with self._lock:
            record = self._records.setdefault(
                session_id,
                SessionRecord(session_id=session_id, call_type="unknown"),
            )
            record.transcript.append(entry)

    def update_summary(self, session_id: str, summary: Dict[str, str]) -> None:
        with self._lock:
            record = self._records.setdefault(
                session_id,
                SessionRecord(session_id=session_id, call_type="unknown"),
            )
            record.summary = summary

    def update_booking_status(self, session_id: str, booking_status: BookingStatus) -> None:
        with self._lock:
            record = self._records.setdefault(
                session_id,
                SessionRecord(session_id=session_id, call_type="unknown"),
            )
            record.booking_status = booking_status


session_store = SessionStore()
