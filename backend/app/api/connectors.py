from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import bids as bids_svc
from ..services import connectors as svc

router = APIRouter(prefix="/api")


@router.get("/connectors")
def get_connectors(db: Session = Depends(get_db)):
    return svc.list_connectors(db)


@router.get("/connectors/{key}")
def get_connector(key: str, db: Session = Depends(get_db)):
    d = svc.connector_detail(db, key)
    if not d:
        raise HTTPException(404, "Connector not found")
    return d


@router.post("/connectors/{key}/sync")
def post_sync(key: str, db: Session = Depends(get_db)):
    try:
        return svc.sync(db, key)
    except svc.ConnectorError as e:
        raise HTTPException(404 if str(e) == "unknown" else 409, "This connector is not connected yet") from e


@router.post("/connectors/{key}/test")
def post_test(key: str, db: Session = Depends(get_db)):
    try:
        return svc.test_connection(db, key)
    except svc.ConnectorError as e:
        raise HTTPException(409, "This connector is not connected yet") from e


@router.get("/bids")
def get_bids(db: Session = Depends(get_db)):
    return bids_svc.pipeline(db)


@router.get("/bids/{crm_id}")
def get_bid(crm_id: str, db: Session = Depends(get_db)):
    d = bids_svc.bid_detail(db, crm_id)
    if not d:
        raise HTTPException(404, "Bid not found")
    return d
