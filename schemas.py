"""
Database Schemas for Student Event Performance Analyzer

Each Pydantic model corresponds to one MongoDB collection.
Collection name is the lowercase of the class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date as DateType


class Student(BaseModel):
    """
    Students collection schema
    Collection name: "student"
    """
    roll_number: str = Field(..., description="Unique roll number e.g., 249Y1A3901")
    name: str = Field(..., description="Full name of the student")
    branch: str = Field(..., description="Department / Branch e.g., AI & ML")
    current_semester: int = Field(..., ge=1, le=12, description="Current semester number")
    academic_year: str = Field(..., description="Academic year label e.g., 2024-25")


class Event(BaseModel):
    """
    Events collection schema (represents an event occurrence series)
    Collection name: "event"
    """
    name: str = Field(..., description="Event name e.g., AI Symposium")
    branch: Optional[str] = Field(None, description="Branch primarily associated (optional)")
    academic_year: Optional[str] = Field(None, description="Academic year for this event series (optional)")


ParticipationStatus = Literal["Attended", "Missed"]


class Participation(BaseModel):
    """
    Participation collection schema (one document per student per event occurrence)
    Collection name: "participation"
    """
    roll_number: str = Field(..., description="Student roll number")
    event_name: str = Field(..., description="Event name")
    event_date: DateType = Field(..., description="Date of event conducted")
    semester: int = Field(..., ge=1, le=12, description="Semester when event occurred")
    status: ParticipationStatus = Field(..., description="Participation status")
    academic_year: str = Field(..., description="Academic year label (e.g., 2024-25)")
    branch: str = Field(..., description="Branch of the student")


# The Flames database viewer can introspect these schemas via /schema endpoint
