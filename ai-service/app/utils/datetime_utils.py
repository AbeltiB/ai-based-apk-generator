"""
ai-service/app/utils/datetime_utils.py
Timezone-aware datetime utilities for production.
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


def to_iso_string(dt: Optional[datetime] = None) -> str:
    """
    Convert datetime to ISO 8601 string with timezone.
    
    Args:
        dt: Datetime object (defaults to now)
        
    Returns:
        ISO 8601 formatted string with timezone
    """
    if dt is None:
        dt = utc_now()
    
    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.isoformat()


def from_iso_string(iso_string: str) -> datetime:
    """
    Parse ISO 8601 string to timezone-aware datetime.
    
    Args:
        iso_string: ISO 8601 formatted string
        
    Returns:
        Timezone-aware datetime object
    """
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    
    # Ensure UTC if no timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt


def timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(utc_now().timestamp() * 1000)


def age_seconds(dt: datetime) -> float:
    """
    Calculate age of datetime in seconds from now.
    
    Args:
        dt: Past datetime
        
    Returns:
        Age in seconds
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return (utc_now() - dt).total_seconds()