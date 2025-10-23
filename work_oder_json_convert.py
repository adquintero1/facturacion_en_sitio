from fastapi import APIRouter, Query
from typing import List
from database import fetch_multiple_work_orders
from config import build_custom_response

router = APIRouter()

@router.get("/get_work_order")
def get_work_order(work_order_ids: List[int] = Query(...)):
    """
    Obtener múltiples work_order_id como:
    /work_orders/?work_order_ids=123&work_order_ids=456
    """
    data = fetch_multiple_work_orders(work_order_ids)

    if len(work_order_ids) == 1:
        work_order_id = work_order_ids[0]
        work_order_data = data[work_order_id]
        return build_custom_response(work_order_data)

    context_list = [v for v in data.values()]
    return build_custom_response(context_list)