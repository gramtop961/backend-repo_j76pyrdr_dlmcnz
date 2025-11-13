import os
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Student, Event, Participation

app = FastAPI(title="Student Event Performance Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class YearBranchQuery(BaseModel):
    academic_year: str
    branch: str


@app.get("/")
def read_root():
    return {"message": "Student Event Performance Analyzer Backend"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ------------------- API MODELS -------------------
class StudentCreate(Student):
    pass


class EventCreate(Event):
    pass


class ParticipationCreate(Participation):
    pass


# ------------------- API ROUTES -------------------
@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
    try:
        # ensure unique roll_number
        existing = db["student"].find_one({"roll_number": student.roll_number})
        if existing:
            raise HTTPException(status_code=400, detail="Student with this roll number already exists")
        _id = create_document("student", student)
        return {"id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/students")
def list_students(academic_year: str = Query(...), branch: str = Query(...)):
    try:
        docs = get_documents("student", {"academic_year": academic_year, "branch": branch})
        # Sort by roll_number naturally if possible
        docs.sort(key=lambda x: x.get("roll_number", ""))
        for d in docs:
            d["id"] = str(d.pop("_id", ""))
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/students/{roll_number}")
def get_student(roll_number: str):
    try:
        doc = db["student"].find_one({"roll_number": roll_number})
        if not doc:
            raise HTTPException(status_code=404, detail="Student not found")
        doc["id"] = str(doc.pop("_id", ""))
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events", status_code=201)
def create_event(event: EventCreate):
    try:
        _id = create_document("event", event)
        return {"id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
def list_events(academic_year: Optional[str] = None, branch: Optional[str] = None):
    try:
        filter_q: Dict[str, Any] = {}
        if academic_year:
            filter_q["academic_year"] = academic_year
        if branch:
            filter_q["branch"] = branch
        docs = get_documents("event", filter_q)
        for d in docs:
            d["id"] = str(d.pop("_id", ""))
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/participations", status_code=201)
def create_participation(p: ParticipationCreate):
    try:
        _id = create_document("participation", p)
        return {"id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/participations/{roll_number}")
def get_participations_for_student(roll_number: str, academic_year: Optional[str] = None):
    try:
        filter_q: Dict[str, Any] = {"roll_number": roll_number}
        if academic_year:
            filter_q["academic_year"] = academic_year
        docs = get_documents("participation", filter_q)
        for d in docs:
            d["id"] = str(d.pop("_id", ""))
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/{roll_number}")
def student_stats(roll_number: str, academic_year: Optional[str] = None):
    """Return aggregated counts per event for a student: held, attended, missed"""
    try:
        filter_q: Dict[str, Any] = {"roll_number": roll_number}
        if academic_year:
            filter_q["academic_year"] = academic_year
        docs = list(db["participation"].find(filter_q))
        # Aggregate by event_name
        summary: Dict[str, Dict[str, int]] = {}
        details: Dict[str, List[Dict[str, Any]]] = {}
        for d in docs:
            event_name = d.get("event_name")
            if event_name not in summary:
                summary[event_name] = {"held": 0, "attended": 0, "missed": 0}
                details[event_name] = []
            summary[event_name]["held"] += 1
            status = d.get("status")
            if status == "Attended":
                summary[event_name]["attended"] += 1
            else:
                summary[event_name]["missed"] += 1
            details[event_name].append({
                "date": d.get("event_date"),
                "semester": d.get("semester"),
                "status": d.get("status"),
            })
        # Convert to list
        result = []
        for name, counts in summary.items():
            result.append({
                "event_name": name,
                "held": counts["held"],
                "attended": counts["attended"],
                "missed": counts["missed"],
                "details": details[name],
            })
        return {"roll_number": roll_number, "summary": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/roll-numbers")
def list_roll_numbers(academic_year: str = Query(...), branch: str = Query(...)):
    """Return sequential list of roll numbers for a given year and branch"""
    try:
        docs = db["student"].find({"academic_year": academic_year, "branch": branch}, {"roll_number": 1, "_id": 0})
        roll_numbers = sorted([d["roll_number"] for d in docs])
        return {"roll_numbers": roll_numbers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Schema introspection for helper tools
@app.get("/schema")
def get_schema_models():
    return {
        "student": Student.model_json_schema(),
        "event": Event.model_json_schema(),
        "participation": Participation.model_json_schema(),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
