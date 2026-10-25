import os
import json
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from life.db import Base, make_engine, session
from life.models import User, Audit
from life.security import hash_password
from life.api import app
from life.calendar import occurrence

@pytest.fixture
def client(tmp_path):
    engine=make_engine(os.getenv("TEST_DATABASE_URL", "sqlite:///"+str(tmp_path/"test.db")))
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    factory=sessionmaker(engine,expire_on_commit=False)
    with factory() as db:
        db.add_all([User(username="vovan",password=hash_password("test-password-123")),User(username="other",password=hash_password("test-password-456"))]); db.commit()
    def override():
        with factory() as db: yield db
    app.dependency_overrides[session]=override
    with TestClient(app) as c:
        token=c.post("/api/v1/auth/login",json={"username":"vovan","password":"test-password-123"}).json()["access_token"]
        c.headers["Authorization"]="Bearer "+token
        yield c
    app.dependency_overrides.clear(); engine.dispose()

def account(c,name="Cash",currency="RUB"):
    r=c.post("/api/v1/accounts",json={"name":name,"currency":currency,"opening_minor":100000})
    assert r.status_code==201,r.text
    return r.json()["id"]

def record(c,kind,title,data):
    r=c.post("/api/v1/records",json={"kind":kind,"title":title,"data":data})
    assert r.status_code==201,r.text
    return r.json()

def operation(c,account_id,**kw):
    body={"key":"expense-1","kind":"expense","account_id":account_id,"amount_minor":10000,"occurred_at":"2026-10-25T12:00:00Z","title":"Server"}
    body.update(kw)
    return c.post("/api/v1/operations",json=body)

def test_login_logout_and_isolation(client):
    assert client.get("/health").status_code==200
    r=record(client,"note","Private",{"text":"secret"})
    other=client.post("/api/v1/auth/login",json={"username":"other","password":"test-password-456"}).json()["access_token"]
    headers={"Authorization":"Bearer "+other}
    assert client.get("/api/v1/records/"+r["id"],headers=headers).status_code==404
    assert client.get("/api/v1/records",headers=headers).json()==[]
    assert client.post("/api/v1/auth/logout").status_code==204
    assert client.get("/api/v1/records").status_code==401

def test_accounting_idempotency_and_currency(client):
    a=account(client); b=account(client,"Provider balance")
    assert operation(client,a).status_code==201
    assert operation(client,a).status_code==201
    assert operation(client,a,amount_minor=10001).status_code==409
    assert operation(client,a,key="transfer",kind="transfer",target_id=b,amount_minor=20000).status_code==201
    assert operation(client,a,key="loan",kind="loan_received",amount_minor=50000).status_code==201
    balances={r["id"]:r["balance_minor"] for r in client.get("/api/v1/accounts").json()}
    assert balances=={a:120000,b:120000}
    usd=account(client,"USD","USD")
    assert operation(client,a,key="fx",kind="transfer",target_id=usd).status_code==422
    assert operation(client,a,key="invalid",amount_minor=-1).status_code==422
    assert operation(client,a,key="time",occurred_at="2026-10-25T12:00:00").status_code==422

def test_recurring_payment_snapshots_and_pay_once(client):
    a=account(client)
    s=record(client,"service","OneDash",{"category":"server","provider":"OneDash","amount_minor":110000,
        "first_due":"2026-01-31","repeat":"monthly","provider_balance_minor":-110000})
    query="?start=2026-01-01&end=2026-03-31"
    for _ in range(2): assert client.post("/api/v1/obligations/generate"+query).status_code==200
    rows=client.get("/api/v1/obligations"+query).json()
    assert [r["due"] for r in rows]==["2026-01-31","2026-02-28","2026-03-31"]
    assert client.get("/api/v1/accounts").json()[0]["balance_minor"]==100000
    body={"account_id":a,"occurred_at":"2026-02-01T09:00:00+03:00"}
    p="/api/v1/obligations/"+rows[0]["id"]+"/pay"
    first=client.post(p,json=body); second=client.post(p,json=body)
    assert first.status_code==200,first.text
    assert first.json()["id"]==second.json()["id"]
    assert client.get("/api/v1/accounts").json()[0]["balance_minor"]==-10000
    assert len(client.get("/api/v1/calendar"+query).json()["items"])==4
    changed=s["data"]|{"amount_minor":220000}
    assert client.put("/api/v1/records/"+s["id"],json={"version":1,"title":s["title"],"data":changed}).status_code==409

def test_optimistic_update_audit_and_links(client):
    p=record(client,"project","Life",{"status":"active"})
    t=record(client,"task","Build core",{"due":"2026-10-25"})
    r=client.post("/api/v1/links",json={"source":t["id"],"target":p["id"],"relation":"belongs_to"})
    assert r.status_code==201
    assert len(client.get("/api/v1/links",params={"record_id":p["id"]}).json())==1
    update={"version":1,"title":"Core ready","data":{"status":"done","due":"2026-10-25"}}
    r=client.put("/api/v1/records/"+t["id"],json=update)
    assert r.status_code==200,r.text
    assert r.json()["version"]==2
    assert client.put("/api/v1/records/"+t["id"],json=update).status_code==409
    assert any(a["action"]=="record.updated" for a in client.get("/api/v1/audit").json())

def test_course_requires_evidence_and_counts_unique_steps(client):
    c=record(client,"course","Python",{"steps":["variables","loops"]})
    data={"course_id":c["id"],"step":"variables","start":"2026-10-25T10:00:00Z","end":"2026-10-25T10:40:00Z","evidence":"Solved 3 exercises"}
    record(client,"study","Practice",data); record(client,"study","Repeat",data)
    progress=client.get("/api/v1/courses/"+c["id"]+"/progress").json()
    assert progress=={"total":2,"completed":1,"percent":50.0,"actual_minutes":80.0}
    bad=data|{"step":"unknown"}
    assert client.post("/api/v1/records",json={"kind":"study","title":"No","data":bad}).status_code==422

def test_custom_types_validate_and_isolate(client):
    definition=record(client,"custom_type","Equipment",{"fields":{"name":"text","price":"integer","bought":"date"}})
    data={"type_id":definition["id"],"values":{"name":"Laptop","price":10000,"bought":"2026-10-25"}}
    record(client,"custom","Laptop",data)
    data["values"]["price"]=True
    assert client.post("/api/v1/records",json={"kind":"custom","title":"Invalid","data":data}).status_code==422

def test_csv_formula_protection(client):
    a=account(client)
    operation(client,a,title="=HYPERLINK(\"bad\")")
    r=client.get("/api/v1/export/operations.csv")
    assert r.status_code==200
    assert "'=HYPERLINK" in r.text
    assert "no-store"==r.headers["cache-control"]

def test_calendar_overlap_and_time_validation(client):
    record(client,"event","Overnight",{"start":"2026-10-24T23:00:00Z","end":"2026-10-25T02:00:00Z"})
    r=client.get("/api/v1/calendar?start=2026-10-25&end=2026-10-25")
    assert len(r.json()["items"])==1
    assert client.get("/api/v1/calendar?start=2026-10-25&end=2026-10-24").status_code==422
    assert client.get("/api/v1/records?limit=50000").status_code==422

def test_recurrence_anchor():
    assert occurrence(date(2024,2,29),"yearly",1,1)==date(2025,2,28)
    assert occurrence(date(2024,2,29),"yearly",1,4)==date(2028,2,29)
    assert occurrence(date(2026,1,1),"days",30,2)==date(2026,3,2)

def test_summary_keeps_loans_transfers_and_currencies_separate(client):
    a=account(client); b=account(client,"Savings"); account(client,"Dollars","USD")
    operation(client,a,key="earned",kind="income",amount_minor=10000)
    operation(client,a,key="loan",kind="loan_received",amount_minor=5000)
    operation(client,a,key="move",kind="transfer",target_id=b,amount_minor=4000)
    result=client.get("/api/v1/finance/summary?start=2026-10-01&end=2026-10-31").json()
    currencies={x["currency"]:x for x in result["currencies"]}
    assert currencies["RUB"]["income_minor"]==10000
    assert currencies["RUB"]["loan_received_minor"]==5000
    assert currencies["RUB"]["balance_minor"]==215000
    assert currencies["USD"]["income_minor"]==0

def test_cannot_spend_or_link_another_users_account(client):
    a=account(client)
    token=client.post("/api/v1/auth/login",json={"username":"other","password":"test-password-456"}).json()["access_token"]
    client.headers["Authorization"]="Bearer "+token
    assert operation(client,a).status_code==404
    assert client.get("/api/v1/operations").json()==[]
    assert client.get("/api/v1/accounts").json()==[]

def test_fractional_minor_units_rejected(client):
    a=account(client)
    assert operation(client,a,amount_minor=1.5).status_code==422
    assert operation(client,a,amount_minor=True).status_code==422
