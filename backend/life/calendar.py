import calendar
import json
from datetime import date, timedelta, datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from .models import Record, Obligation, Operation, Account
from .records import owned, audit
from .finance import post
from .schemas import OperationIn

def occurrence(anchor, repeat, interval, index):
    if repeat == "once": return anchor if index == 0 else None
    if repeat == "days": return anchor + timedelta(days=interval*index)
    months = interval*index*(12 if repeat == "yearly" else 1)
    month_index = anchor.year*12 + anchor.month - 1 + months
    year, month = divmod(month_index, 12); month += 1
    return date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))

def materialize(db, owner, start, end):
    if end < start or (end-start).days > 366: raise HTTPException(422, "Range must be 0..366 days")
    for service in db.scalars(select(Record).where(Record.owner==owner, Record.kind=="service").with_for_update()):
        data = json.loads(service.data)
        if not data["active"]: continue
        anchor = date.fromisoformat(data["first_due"])
        # Start near the requested range: runtime depends on the window, not service age.
        if data["repeat"] == "once": first = 0
        elif data["repeat"] == "days": first = max(0, (start-anchor).days // data["interval"] - 1)
        else:
            delta = (start.year-anchor.year)*12 + start.month-anchor.month
            period = data["interval"] * (12 if data["repeat"] == "yearly" else 1)
            first = max(0, delta // period - 1)
        for index in range(first, first+370):
            try: due = occurrence(anchor, data["repeat"], data["interval"], index)
            except (ValueError, OverflowError): break
            if due is None or due > end: break
            if due < start: continue
            existing = db.scalar(select(Obligation).where(Obligation.service_id==service.id, Obligation.due==due.isoformat()))
            if existing is None:
                db.add(Obligation(owner=owner, service_id=service.id, due=due.isoformat(),
                    amount_minor=data["amount_minor"], currency=data["currency"]))
    db.flush()

def pay(db, owner, id, body):
    obligation = db.scalar(select(Obligation).where(Obligation.owner==owner, Obligation.id==id).with_for_update())
    if obligation is None: raise HTTPException(404, "Not found")
    if obligation.operation_id:
        existing = db.get(Operation, obligation.operation_id)
        if existing.account_id != body.account_id: raise HTTPException(409, "Already paid from another account")
        return existing
    account = owned(db, Account, body.account_id, owner)
    if account.currency != obligation.currency: raise HTTPException(422, "Currency mismatch")
    service = owned(db, Record, obligation.service_id, owner)
    op = post(db, owner, OperationIn(key="obligation:"+id, kind="expense", account_id=account.id,
        amount_minor=obligation.amount_minor, occurred_at=body.occurred_at,
        title=service.title, record_id=service.id))
    obligation.operation_id = op.id
    audit(db, owner, id, "obligation.paid", {"operation_id": op.id})
    return op

def timeline(db, owner, start, end):
    rows=[]
    for r in db.scalars(select(Record).where(Record.owner==owner)):
        d=json.loads(r.data)
        if r.kind == "task" and d["due"] and start.isoformat() <= d["due"] <= end.isoformat():
            rows.append({"id":r.id,"kind":"task","title":r.title,"date":d["due"],"status":d["status"]})
        if r.kind in ("event", "study"):
            lo=datetime.combine(start,datetime.min.time(),timezone.utc)
            hi=datetime.combine(end+timedelta(days=1),datetime.min.time(),timezone.utc)
            if datetime.fromisoformat(d["start"]) < hi and datetime.fromisoformat(d["end"]) > lo:
                rows.append({"id":r.id,"kind":r.kind,"title":r.title,"start":d["start"],"end":d["end"]})
    for o in db.scalars(select(Obligation).where(Obligation.owner==owner, Obligation.due>=start.isoformat(),Obligation.due<=end.isoformat())):
        rows.append({"id":o.id,"kind":"payment","date":o.due,"service_id":o.service_id,
            "amount_minor":o.amount_minor,"currency":o.currency,"paid":bool(o.operation_id)})
    lower = datetime.combine(start, datetime.min.time(), timezone.utc)
    upper = datetime.combine(end+timedelta(days=1), datetime.min.time(), timezone.utc)
    for op in db.scalars(select(Operation).where(Operation.owner==owner)):
        at = datetime.fromisoformat(op.occurred_at)
        if lower <= at < upper:
            rows.append({"id":op.id,"kind":"operation","title":op.title,"start":op.occurred_at,
                         "operation_kind":op.kind,"amount_minor":op.amount_minor,"account_id":op.account_id})
    return sorted(rows,key=lambda r:r.get("date",r.get("start","")))
