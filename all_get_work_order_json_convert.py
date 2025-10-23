from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from database import fetch_filtered_work_orders
from config import build_custom_response, build_simple_response
import json
import io

router = APIRouter()

@router.get("/get_all_work_orders")
def get_all_work_orders(
    country_id: int = Query(..., description="ID del país"),
    company_id: str = Query(..., description="UUID de la empresa")
):
    """
    Obtener work orders filtrando por country_id y company_id.
    Ejemplo de uso:
    /work_orders/?country_id=27&company_id=200
    """
    data = fetch_filtered_work_orders(country_id, company_id)
    context_list = [v for v in data.values()]
    return build_custom_response(context_list)

@router.get("/get_all_work_orders_simple")
def get_all_work_orders_simple(
    country_id: int = Query(..., description="ID del país"),
    company_id: str = Query(..., description="UUID de la empresa")
):
    """
    Obtener work orders filtrando por country_id y company_id (SIN linkedRules).
    Solo incluye model y context.
    Ejemplo de uso:
    /work_orders/?country_id=27&company_id=200
    """
    data = fetch_filtered_work_orders(country_id, company_id)
    context_list = [v for v in data.values()]
    return build_simple_response(context_list)

@router.get("/download_all_work_orders")
def download_all_work_orders(country_id: int, company_id: str):
    """
    Descargar todos los work orders filtrados por country_id y company_id como archivo JSON.
    """
    data = fetch_filtered_work_orders(country_id, company_id)
    context_list = [v for v in data.values()]
    payload = build_custom_response(context_list)

    json_str = json.dumps(payload, indent=2, ensure_ascii=False)
    buffer = io.BytesIO(json_str.encode("utf-8"))

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=all_work_orders.json"
        }
    )

@router.get("/download_all_work_orders_simple")
def download_all_work_orders_simple(country_id: int, company_id: str):
    """
    Descargar todos los work orders filtrados por country_id y company_id como archivo JSON (SIN linkedRules).
    Solo incluye model y context.
    """
    data = fetch_filtered_work_orders(country_id, company_id)
    context_list = [v for v in data.values()]
    payload = build_simple_response(context_list)

    json_str = json.dumps(payload, indent=2, ensure_ascii=False)
    buffer = io.BytesIO(json_str.encode("utf-8"))

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=all_work_orders_simple.json"
        }
    )