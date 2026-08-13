from enum import Enum


class ATSProvider(str, Enum):
    GREENHOUSE = "GREENHOUSE"
    LEVER = "LEVER"
    ASHBY = "ASHBY"


class MonitoringPriority(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class WorkMode(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class JobStatus(str, Enum):
    ACTIVE = "ACTIVE"
    UNKNOWN = "UNKNOWN"
    CLOSED = "CLOSED"


class CrawlerStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NotificationChannel(str, Enum):
    TELEGRAM = "TELEGRAM"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class UserJobStateType(str, Enum):
    SAVED = "SAVED"
    IGNORED = "IGNORED"
