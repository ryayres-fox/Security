"""The compliant counterpart. Every function satisfies the rule its
non-compliant twin violates.

This half matters as much as the other. A rule set that flags everything passes
every "does it fire?" test and is still useless — it gets suppressed within a
week, and a suppressed rule reports success forever after.
"""
import pickle  # noqa: S403  -- imported only to show the safe alternative below

import requests
import yaml
from fastapi import APIRouter, Depends, Request

from .auth import current_user, require_scope

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
    del pickle
    raise NotImplementedError("use json.loads for untrusted input")
