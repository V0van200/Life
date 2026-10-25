import csv
import io
import json
import os
import secrets
import time
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from .db import session
from .models import User, LoginSession, Record, Account, Operation, Obligation, Link, Audit, now
from .security import current_user, bearer, digest, verify
from . import schemas as S, records, finance, calendar

app = FastAPI(title="Life Core API", version="0.1.0", description="Personal modular backend. Money amounts are integer minor units; dates use ISO 8601.")
app.add_middleware(CORSMiddleware,
    allow_origins=[s.strip() for s in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if s.strip()],
    allow_methods=["GET","POST","PUT","OPTIONS"], allow_headers=["Authorization","Content-Type"],
    allow_credentials=False)

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={"detail":"Concurrent or duplicate write. Retry with the same idempotency key."})

@app.exception_handler(StaleDataError)
async def stale_error(request, exc):
    return JSONResponse(status_code=409, content={"detail":"Record changed. Reload and reconcile edits."})

@app.middleware("http")
async def headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/health")
def health(db=Depends(session)):
    db.execute(text("SELECT 1"))
    return {"status":"ok", "version":"0.1.0"}

@app.post("/api/v1/auth/login")
def login(body:S.Login, db=Depends(session)):
    user=db.scalar(select(User).where(User.username==body.username))
    # Dummy hash work keeps nonexistent user response similar to wrong password.
    stored=user.password if user else "00000000000000000000000000000000:"+"0"*128
    if not verify(body.password, stored) or user is None: raise HTTPException(401,"Invalid credentials")
    token=secrets.token_urlsafe(48)
    expires=int(time.time())+60*60*12
    db.add(LoginSession(digest=digest(token),owner=user.id,expires=expires)); db.commit()
    return {"access_token":token,"token_type":"bearer","expires_at":expires}

@app.post("/api/v1/auth/logout", status_code=204)
def logout(owner=Depends(current_user), credentials=Depends(bearer), db=Depends(session)):
    row=db.get(LoginSession,digest(credentials.credentials))
    if row: db.delete(row); db.commit()
    return Response(status_code=204)

@app.get("/api/v1/modules")
def modules(owner=Depends(current_user)):
    return {"record_types":list(records.SCHEMAS),"features":["accounts","operations","obligations","calendar","links","audit","csv_export"]}

@app.get("/api/v1/records")
def list_records(kind:str|None=None, limit:int=Query(50,ge=1,le=200), offset:int=Query(0,ge=0), owner=Depends(current_user),db=Depends(session)):
    q=select(Record).where(Record.owner==owner)
    if kind: q=q.where(Record.kind==kind)
    return [records.serialize(r) for r in db.scalars(q.order_by(Record.created_at,Record.id).limit(limit).offset(offset))]

@app.post("/api/v1/records",status_code=201)
def create_record(body:S.RecordIn,owner=Depends(current_user),db=Depends(session)):
    row=records.create(db,owner,body); db.commit()
    return records.serialize(row)

@app.get("/api/v1/records/{id}")
def get_record(id:str,owner=Depends(current_user),db=Depends(session)):
    return records.serialize(records.owned(db,Record,id,owner))

@app.put("/api/v1/records/{id}")
def update_record(id:str,body:S.RecordUpdate,owner=Depends(current_user),db=Depends(session)):
    row=records.owned(db,Record,id,owner)
    if row.version!=body.version: raise HTTPException(409,"Version conflict")
    if row.kind in ("custom_type","course","study"):
        raise HTTPException(409,"This definition/evidence is immutable in v1; create a new version as a new record")
    if row.kind=="service":
        # Materialized amounts/dates are contractual snapshots, not regenerated silently.
        exists=db.scalar(select(Obligation.id).where(Obligation.service_id==id).limit(1))
        if exists and body.data != json.loads(row.data):
            raise HTTPException(409,"Service has scheduled obligations; create a replacement service and deactivate the old one")
    data=records.validate(db,owner,row.kind,body.data)
    row.title=body.title; row.data=json.dumps(data,ensure_ascii=False); row.updated_at=now()
    db.flush(); records.audit(db,owner,id,"record.updated",records.serialize(row)); db.commit()
    return records.serialize(row)

@app.post("/api/v1/services/{id}/deactivate")
def deactivate(id:str,owner=Depends(current_user),db=Depends(session)):
    row=records.owned(db,Record,id,owner)
    if row.kind!="service": raise HTTPException(422,"Expected service")
    data=json.loads(row.data); data["active"]=False; row.data=json.dumps(data); row.updated_at=now()
    records.audit(db,owner,id,"service.deactivated",data); db.commit()
    return {"active":False,"note":"Existing obligations retained; deactivation stops future materialization"}

@app.post("/api/v1/links",status_code=201)
def link(body:S.LinkIn,owner=Depends(current_user),db=Depends(session)):
    records.owned(db,Record,body.source,owner); records.owned(db,Record,body.target,owner)
    if body.source==body.target: raise HTTPException(422,"Cannot link a record to itself")
    row=Link(owner=owner,**body.model_dump()); db.add(row); db.flush()
    records.audit(db,owner,row.id,"link.created",body.model_dump()); db.commit()
    return {"id":row.id,**body.model_dump()}

@app.get("/api/v1/links")
def links(record_id:str,owner=Depends(current_user),db=Depends(session)):
    records.owned(db,Record,record_id,owner)
    q=select(Link).where(Link.owner==owner, (Link.source==record_id)|(Link.target==record_id))
    return [{"id":r.id,"source":r.source,"target":r.target,"relation":r.relation} for r in db.scalars(q)]

@app.post("/api/v1/accounts",status_code=201)
def account(body:S.AccountIn,owner=Depends(current_user),db=Depends(session)):
    row=Account(owner=owner,**body.model_dump()); db.add(row); db.flush()
    records.audit(db,owner,row.id,"account.created",body.model_dump()); db.commit()
    return {"id":row.id,**body.model_dump()}

@app.get("/api/v1/accounts")
def accounts(owner=Depends(current_user),db=Depends(session)):
    return finance.balances(db,owner)

@app.post("/api/v1/operations",status_code=201)
def operation(body:S.OperationIn,owner=Depends(current_user),db=Depends(session)):
    if body.key.startswith("obligation:"): raise HTTPException(422,"Reserved key prefix")
    row=finance.post(db,owner,body); db.commit(); return finance.operation_dict(row)

@app.get("/api/v1/operations")
def operations(limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),owner=Depends(current_user),db=Depends(session)):
    q=select(Operation).where(Operation.owner==owner).order_by(Operation.occurred_at,Operation.id).limit(limit).offset(offset)
    return [finance.operation_dict(row) for row in db.scalars(q)]

@app.post("/api/v1/obligations/generate")
def generate(start:date,end:date,owner=Depends(current_user),db=Depends(session)):
    calendar.materialize(db,owner,start,end); db.commit()
    return {"status":"generated","start":start,"end":end}

@app.get("/api/v1/obligations")
def obligations(start:date,end:date,owner=Depends(current_user),db=Depends(session)):
    if end<start or (end-start).days>366: raise HTTPException(422,"Invalid range")
    q=select(Obligation).where(Obligation.owner==owner,Obligation.due>=start.isoformat(),Obligation.due<=end.isoformat()).order_by(Obligation.due,Obligation.id)
    return [{"id":o.id,"service_id":o.service_id,"due":o.due,"amount_minor":o.amount_minor,"currency":o.currency,"operation_id":o.operation_id} for o in db.scalars(q)]

@app.post("/api/v1/obligations/{id}/pay")
def pay(id:str,body:S.PayIn,owner=Depends(current_user),db=Depends(session)):
    row=calendar.pay(db,owner,id,body); db.commit(); return finance.operation_dict(row)

@app.get("/api/v1/calendar")
def get_calendar(start:date,end:date,owner=Depends(current_user),db=Depends(session)):
    if end<start or (end-start).days>366: raise HTTPException(422,"Invalid range")
    return {"timezone":"UTC","items":calendar.timeline(db,owner,start,end)}

@app.get("/api/v1/courses/{id}/progress")
def progress(id:str,owner=Depends(current_user),db=Depends(session)):
    course=records.owned(db,Record,id,owner)
    if course.kind!="course": raise HTTPException(422,"Expected course")
    steps=json.loads(course.data)["steps"]; completed=set(); seconds=0
    from datetime import datetime
    for r in db.scalars(select(Record).where(Record.owner==owner,Record.kind=="study")):
        d=json.loads(r.data)
        if d["course_id"]==id:
            completed.add(d["step"])
            seconds+=(datetime.fromisoformat(d["end"])-datetime.fromisoformat(d["start"])).total_seconds()
    return {"total":len(steps),"completed":len(completed),"percent":round(len(completed)/len(steps)*100,2),"actual_minutes":round(seconds/60,2)}

@app.get("/api/v1/audit")
def audit(limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),owner=Depends(current_user),db=Depends(session)):
    q=select(Audit).where(Audit.owner==owner).order_by(Audit.at,Audit.id).limit(limit).offset(offset)
    return [{"id":r.id,"entity_id":r.entity_id,"action":r.action,"at":r.at,"snapshot":json.loads(r.snapshot)} for r in db.scalars(q)]

@app.get("/api/v1/export/operations.csv")
def export(owner=Depends(current_user),db=Depends(session)):
    out=io.StringIO(); writer=csv.writer(out)
    fields=["id","kind","account_id","target_id","amount_minor","occurred_at","title","record_id"]
    writer.writerow(fields)
    def safe(value):
        # Prevent Excel formula interpretation for user text. Numeric amounts stay numeric.
        if isinstance(value,str) and value.lstrip().startswith(("=","+","-","@","\t","\r")): return "'"+value
        return value
    for r in db.scalars(select(Operation).where(Operation.owner==owner).order_by(Operation.occurred_at,Operation.id)):
        writer.writerow([safe(getattr(r,k)) for k in fields])
    return Response(content="\ufeff"+out.getvalue(),media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":'attachment; filename="life-operations.csv"'})

@app.get("/api/v1/finance/summary")
def financial_summary(start:date,end:date,owner=Depends(current_user),db=Depends(session)):
    """Cash flows and unpaid commitments; no addition of unlike currencies."""
    from datetime import datetime, timedelta, timezone
    if end<start or (end-start).days>366: raise HTTPException(422,"Invalid range")
    lo=datetime.combine(start,datetime.min.time(),timezone.utc)
    hi=datetime.combine(end+timedelta(days=1),datetime.min.time(),timezone.utc)
    currencies={a.id:a.currency for a in db.scalars(select(Account).where(Account.owner==owner))}
    totals={}
    def bucket(currency):
        return totals.setdefault(currency,{"currency":currency,"income_minor":0,"expense_minor":0,
            "loan_received_minor":0,"loan_repayment_minor":0,"unpaid_minor":0,"balance_minor":0})
    for a in finance.balances(db,owner): bucket(a["currency"])["balance_minor"]+=a["balance_minor"]
    for op in db.scalars(select(Operation).where(Operation.owner==owner)):
        if op.kind!="transfer" and lo <= datetime.fromisoformat(op.occurred_at) < hi:
            bucket(currencies[op.account_id])[op.kind+"_minor"]+=op.amount_minor
    for due in db.scalars(select(Obligation).where(Obligation.owner==owner,Obligation.due>=start.isoformat(),
            Obligation.due<=end.isoformat(),Obligation.operation_id.is_(None))):
        bucket(due.currency)["unpaid_minor"]+=due.amount_minor
    return {"start":start,"end":end,"currencies":list(totals.values()),
            "forecast_scope":"Only explicitly generated obligations. Balance is current; flows use selected UTC range."}
