"""Deliberately non-compliant. Every function violates exactly one rule, so a
test can assert WHICH rule fired rather than only that something did.

Never imported, never run. It exists so the rule set can be proven to MATCH, not
merely to load — a rule that registers and never fires is the same fail-open as
a rule that never registers, relocated one step later.
"""
import pickle
from typing import Annotated

import httpx
import requests
import yaml
from fastapi import APIRouter, Header, Request
from sqlalchemy import select

router = APIRouter()


# reference-missing-route-authorization
@router.get("/reports")
def list_reports():
    return {"reports": []}


# reference-missing-route-authorization
@router.post("/reports")
def create_report(body: dict):
    return {"ok": True}


# reference-actor-field-from-request-body
def save_report(report, body):
    report.created_by = body.created_by
    return report


# reference-tenant-scope-from-request
def tenant_from_request(request: Request):
    return request.headers.get("X-Tenant-Id", "default")


# reference-unscoped-tenant-query
def all_documents(session, Document):
    return session.query(Document).all()


# reference-disabled-tls-verification
def fetch_upstream(url):
    return requests.get(url, verify=False)


# reference-disabled-tls-verification
def fetch_upstream_httpx(url):
    return httpx.get(url, verify=False)


# reference-unsafe-deserialization
def load_config(raw):
    return yaml.load(raw)


# reference-unsafe-deserialization
def load_cache(blob):
    return pickle.loads(blob)


# reference-missing-route-authorization
@router.put("/reports/{report_id}")
def replace_report(report_id: int, body: dict):
    return {"ok": True}


# reference-missing-route-authorization
@router.patch("/reports/{report_id}")
async def edit_report(report_id: int, body: dict):
    return {"ok": True}


# reference-tenant-scope-from-request
def tenant_from_lowercase_header(request: Request):
    return request.headers.get("x-tenant-id")


# reference-tenant-scope-from-request
def tenant_from_header_parameter(x_tenant_id: str = Header(...)):
    return x_tenant_id


# reference-tenant-scope-from-request
def tenant_from_annotated_header(tenant_id: Annotated[str, Header()]):
    return tenant_id


# reference-unscoped-tenant-query
def document_by_id(session, Document, doc_id):
    return session.get(Document, doc_id)


# reference-unscoped-tenant-query
def all_documents_v2(session, Document):
    return session.scalars(select(Document)).all()
