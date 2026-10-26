from fastapi import HTTPException
from sqlalchemy import select
from .models import Account, Operation
from .records import owned, audit
from .schemas import OperationIn

POSITIVE = {"income", "loan_received"}

def operation_dict(row):
    return {k: getattr(row, k) for k in ("id", "key", "kind", "account_id", "target_id", "amount_minor", "occurred_at", "title", "record_id")}

def post(db, owner, body: OperationIn):
    values = body.model_dump(mode="json")
    existing = db.scalar(select(Operation).where(Operation.owner==owner, Operation.key==body.key))
    if existing:
        if any(getattr(existing, k) != v for k,v in values.items()):
            raise HTTPException(409, "Idempotency key reused with different content")
        return existing
    account = owned(db, Account, body.account_id, owner)
    if body.target_id:
        target = owned(db, Account, body.target_id, owner)
        if target.currency != account.currency: raise HTTPException(422, "Cross-currency transfer requires explicit exchange support")
    if body.record_id:
        from .models import Record
        owned(db, Record, body.record_id, owner)
    row = Operation(owner=owner, **values)
    db.add(row); db.flush()
    audit(db, owner, row.id, "finance.posted", operation_dict(row))
    return row

def balances(db, owner):
    accounts = list(db.scalars(select(Account).where(Account.owner==owner)))
    values = {a.id: a.opening_minor for a in accounts}
    for op in db.scalars(select(Operation).where(Operation.owner==owner)):
        values[op.account_id] += op.amount_minor if op.kind in POSITIVE else -op.amount_minor
        if op.target_id: values[op.target_id] += op.amount_minor
    return [{"id": a.id, "name": a.name, "currency": a.currency, "balance_minor": values[a.id]} for a in accounts]
