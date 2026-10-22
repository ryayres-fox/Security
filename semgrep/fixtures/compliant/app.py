"""The compliant counterpart. Every function satisfies the rule its
non-compliant twin violates.

This half matters as much as the other. A rule set that flags everything passes
every "does it fire?" test and is still useless — it gets suppressed within a
week, and a suppressed rule reports success forever after.
"""
import json
import os
from typing import Annotated

import requests
import yaml
from fastapi import APIRouter, Depends, Header, Request, Security
from sqlalchemy import select

from .auth import User, current_user, require_scope

router = APIRouter()


@router.get("/reports", dependencies=[Depends(require_scope("reports:read"))])
def list_reports():
    return {"reports": []}


@router.post("/reports")
def create_report(body: dict, user=Depends(current_user)):
    return {"ok": True}


def save_report(report, user):
    report.created_by = user.subject
    return report


def tenant_from_context(request: Request):
    return request.state.auth.tenant_id


def all_documents(session, Document, tenant_id):
    return session.query(Document).filter_by(tenant_id=tenant_id).all()


def fetch_upstream(url):
    return requests.get(url, timeout=10)


def load_config(raw):
    return yaml.safe_load(raw)


def load_cache(blob):
    return json.loads(blob)


@router.put("/reports/{report_id}")
def replace_report(report_id: int, body: dict,
                   user: Annotated[User, Depends(current_user)]):
    return {"ok": True}


@router.patch("/reports/{report_id}")
async def edit_report(report_id: int, body: dict,
                      user=Security(current_user, scopes=["reports:write"])):
    return {"ok": True}


@router.delete("/reports/{report_id}")
def delete_report(report_id: int, user: User = Depends(current_user)):
    return {"ok": True}


def request_id_from_header(x_request_id: str = Header(...)):
    return x_request_id


def user_agent(request: Request):
    return request.headers.get("User-Agent")


def document_by_id(session, Document, doc_id, tenant_id):
    row = session.get(Document, doc_id)
    if row is None or row.tenant_id != tenant_id:
        raise PermissionError(doc_id)
    return row


def all_documents_v2(session, Document, tenant_id):
    return session.scalars(
        select(Document).where(Document.tenant_id == tenant_id)).all()


def app_env():
    return os.environ.get("APP_ENV", "dev")


def serialise(row):
    return {"id": row.id, "tenant_id": row.tenant_id}


def serialise_typed(row: "Report"):
    return {"id": row.id, "tenant_id": row.tenant_id}


@router.get("/me/tenant")
def my_tenant(user: User = Depends(current_user)):
    return {"tenant": user.tenant_id}


@router.get("/me/tenant/annotated")
def my_tenant_annotated(user: Annotated[User, Depends(current_user)]):
    return {"tenant": user.tenant_id}
