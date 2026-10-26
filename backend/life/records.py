import json
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from . import schemas as S
from .models import Record, Audit, now

SCHEMAS = {"project": S.Project, "task": S.Task, "event": S.Event, "service": S.Service,
           "course": S.Course, "study": S.Study, "note": S.Note, "custom_type": S.CustomType, "custom": S.Custom}

def owned(db, model, id, owner):
    row = db.scalar(select(model).where(model.id == id, model.owner == owner))
    if row is None: raise HTTPException(404, "Not found")
    return row

def audit(db, owner, id, action, data):
    db.add(Audit(owner=owner, entity_id=id, action=action, snapshot=json.dumps(data, ensure_ascii=False)))

def serialize(row):
    return {"id": row.id, "kind": row.kind, "title": row.title, "data": json.loads(row.data),
            "version": row.version, "created_at": row.created_at, "updated_at": row.updated_at}

def validate(db, owner, kind, data):
    try: result = SCHEMAS[kind].model_validate(data).model_dump(mode="json")
    except ValidationError as e: raise HTTPException(422, str(e))
    if kind == "study":
        course = owned(db, Record, result["course_id"], owner)
        if course.kind != "course" or result["step"] not in json.loads(course.data)["steps"]:
            raise HTTPException(422, "Unknown course step")
    if kind == "custom":
        definition = owned(db, Record, result["type_id"], owner)
        if definition.kind != "custom_type": raise HTTPException(422, "Expected custom type")
        fields = json.loads(definition.data)["fields"]
        if set(result["values"]) != set(fields): raise HTTPException(422, "Custom fields do not match definition")
        for name, typ in fields.items():
            value = result["values"][name]
            valid = {"text": type(value) is str, "integer": type(value) is int, "boolean": type(value) is bool,
                     "date": type(value) is str}[typ]
            if typ == "date" and valid:
                from datetime import date
                try: date.fromisoformat(value)
                except ValueError: valid = False
            if not valid: raise HTTPException(422, "Invalid field: " + name)
    return result

def create(db, owner, body):
    data = validate(db, owner, body.kind, body.data)
    row = Record(owner=owner, kind=body.kind, title=body.title, data=json.dumps(data, ensure_ascii=False))
    db.add(row); db.flush()
    audit(db, owner, row.id, "record.created", serialize(row))
    return row
