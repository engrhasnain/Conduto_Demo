"""Supplier invoices: the queue, one invoice with its working, and the sum.

Nothing here decides anything. The queue reports what the checks already
made of each document, and the only write is a person approving one that
was held — which is the one decision this product does not take by itself.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..domain import factura as fa
from ..domain.taxid import format_cuit
from ..models import Document, Project, SupplierInvoice
from ..services import invoices as svc

router = APIRouter(prefix="/api")

#: What each exception means in one line, for somebody who has to clear it.
WHY: dict[str, dict[str, str]] = {
    "cae_invalido": {
        "es": "El CAE no es válido o estaba vencido cuando llegó la factura.",
        "en": "The authorisation code is invalid, or had expired when the invoice arrived.",
        "pt": "O código de autorização é inválido ou estava vencido quando a fatura chegou.",
    },
    "otro_cuit": {
        "es": "Está emitida a la otra sociedad del grupo, no a esta.",
        "en": "It is made out to the other company in the group, not to this one.",
        "pt": "Está emitida para a outra empresa do grupo, não para esta.",
    },
    "no_suma": {
        "es": "El neto, el IVA y las percepciones no suman el total impreso.",
        "en": "Net, tax and perceptions do not add up to the printed total.",
        "pt": "Líquido, imposto e percepções não somam o total impresso.",
    },
    "proveedor_desconocido": {
        "es": "El proveedor no está en el maestro; hay que darlo de alta.",
        "en": "The supplier is not in the master file and has to be opened.",
        "pt": "O fornecedor não está no cadastro e precisa ser aberto.",
    },
    "duplicada": {
        "es": "Este mismo comprobante ya está registrado.",
        "en": "This same document is already posted.",
        "pt": "Este mesmo documento já está lançado.",
    },
    "cuit_invalido": {
        "es": "El CUIT del emisor no pasa el dígito verificador.",
        "en": "The issuer's tax number fails its check digit.",
        "pt": "O CNPJ do emissor não passa no dígito verificador.",
    },
    "tipo_desconocido": {
        "es": "No se reconoce el tipo de comprobante.",
        "en": "The document type is not recognised.",
        "pt": "O tipo de documento não é reconhecido.",
    },
    "iva_no_cuadra": {
        "es": "El IVA declarado no corresponde a ninguna alícuota publicada.",
        "en": "The stated tax matches no published rate.",
        "pt": "O imposto declarado não corresponde a nenhuma alíquota publicada.",
    },
}


def _row(i: SupplierInvoice) -> dict:
    return {
        "id": i.id,
        "filename": i.filename,
        "received_on": i.received_on,
        "channel": i.channel,
        "vendor_name": i.vendor_name,
        "vendor_tax_id": format_cuit(i.vendor_tax_id),
        "document_type": i.document_type,
        "document_type_name": fa.document_type_name(i.document_type),
        "letter": fa.letter_of(i.document_type),
        "number": f"{i.point_of_sale:04d}-{i.number:08d}",
        "invoice_date": i.invoice_date,
        "authorisation_code": i.authorisation_code,
        "authorisation_expires": i.authorisation_expires,
        "currency": i.currency,
        "net": i.net,
        "vat": i.vat,
        "perception": i.perception,
        "total": i.total,
        "status": i.status,
        "exception_kind": i.exception_kind,
        "exception_detail": i.exception_detail,
        "why": WHY.get(i.exception_kind, {}),
        "confidence": i.confidence,
        "manual_minutes": i.manual_minutes,
        "approved_by": i.approved_by,
        "posted_reference": i.posted_reference,
        "posted_route": i.posted_route,
        "posted_at": i.posted_at.isoformat() + "Z" if i.posted_at else None,
        "document_id": i.document_id,
    }


@router.get("/invoices")
def list_invoices(
    status: str = Query("all"),
    channel: str = Query("all"),
    search: str = Query(""),
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = select(SupplierInvoice).order_by(SupplierInvoice.received_on.desc(), SupplierInvoice.id.desc())
    if status != "all":
        query = query.where(SupplierInvoice.status == status)
    if channel != "all":
        query = query.where(SupplierInvoice.channel == channel)
    rows = list(db.scalars(query.limit(limit)))
    if search:
        needle = search.lower().strip()
        rows = [
            r for r in rows
            if needle in r.vendor_name.lower()
            or needle in r.filename.lower()
            or needle in f"{r.point_of_sale:04d}-{r.number:08d}"
        ]

    everything = list(db.scalars(select(SupplierInvoice)))
    counts: dict[str, int] = {}
    for r in everything:
        counts[r.status] = counts.get(r.status, 0) + 1
    exceptions: dict[str, int] = {}
    for r in everything:
        if r.exception_kind:
            exceptions[r.exception_kind] = exceptions.get(r.exception_kind, 0) + 1

    return {
        "invoices": [_row(r) for r in rows],
        "counts": counts,
        "exceptions": exceptions,
        "channels": sorted({r.channel for r in everything}),
        "total": len(everything),
    }


@router.get("/invoices/savings")
def get_savings(db: Session = Depends(get_db)):
    """What this batch actually removed, from the rows rather than a slide."""
    return svc.savings(db)


class Projection(BaseModel):
    invoices_per_month: float = Field(default=420, ge=0, le=100_000)
    minutes_each: float = Field(default=4.5, ge=0.1, le=120)
    straight_through_pct: float = Field(default=87.4, ge=0, le=100)
    hourly_cost: float = Field(default=0, ge=0, le=10_000)


@router.post("/invoices/projection")
def post_projection(body: Projection):
    """The same sum at the volume the business types in.

    Kept apart from ``/savings`` on purpose: that one reports what happened
    here, this one answers "what would it be at our volume", and confusing
    the two in a meeting is how a number nobody can defend ends up on a
    slide.
    """
    return svc.project_savings(
        invoices_per_month=body.invoices_per_month,
        minutes_each=body.minutes_each,
        straight_through_pct=body.straight_through_pct,
        hourly_cost=body.hourly_cost,
    )


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.get(SupplierInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    out = _row(invoice)
    out["checks"] = (invoice.checks or {}).get("checks", [])
    out["notes"] = (invoice.checks or {}).get("notes", [])
    document = db.get(Document, invoice.document_id) if invoice.document_id else None
    out["document"] = (
        {"id": document.id, "filename": document.filename, "rel_path": document.rel_path}
        if document else None
    )
    project = db.get(Project, invoice.project_id) if invoice.project_id else None
    out["project"] = {"code": project.code, "name": project.name} if project else None
    return out


class Approval(BaseModel):
    by: str = Field(default="Nicolás Varela", max_length=80)
    note: str = Field(default="", max_length=500)


@router.post("/invoices/{invoice_id}/approve")
def post_approve(invoice_id: int, body: Approval, db: Session = Depends(get_db)):
    """A person takes responsibility for one the checks stopped.

    The exception is kept, not erased. What changes is that somebody's
    name is now against it, which is the whole difference between a
    cleared exception and a hidden one.
    """
    invoice = db.get(SupplierInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if invoice.status == "posted":
        raise HTTPException(409, "This invoice is already posted")

    invoice.status = "approved"
    invoice.approved_by = body.by
    invoice.approved_at = dt.datetime.utcnow()
    if body.note:
        invoice.exception_detail = f"{invoice.exception_detail} — {body.note}".strip(" —")
    db.commit()
    return _row(invoice)
