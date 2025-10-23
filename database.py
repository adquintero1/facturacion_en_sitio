# Funciones de base de datos comunes
import psycopg2
import pandas as pd
from typing import Any, Dict, List
from fastapi import HTTPException
from config import DB_CONFIG, TABLE_NAME, process_attribute_value

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    return psycopg2.connect(**DB_CONFIG)

def fetch_multiple_work_orders(work_order_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Obtiene múltiples work orders por sus IDs"""
    conn = get_db_connection()
    query = f"""
        SELECT work_order_id, name, attribute_value
        FROM {TABLE_NAME}
        WHERE work_order_id = ANY(%s)
    """
    df = pd.read_sql(query, conn, params=(work_order_ids,))
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="No work orders found")

    grouped = df.groupby("work_order_id")
    result = {}

    for work_order_id, group in grouped:
        record = {}
        for _, row in group.iterrows():
            key = row['name']
            val = row['attribute_value']
            val = process_attribute_value(val)
            record[key] = val
        result[work_order_id] = {"tsl_wo_work_order_attribute": record}

    return result

def fetch_filtered_work_orders(country_id: int, company_id: str) -> Dict[int, Dict[str, Any]]:
    """Obtiene work orders filtrados por country_id y company_id"""
    conn = get_db_connection()
    query = f"""
        SELECT work_order_id, name, attribute_value
        FROM {TABLE_NAME}
        WHERE country_id = %s AND company_id = %s
    """
    df = pd.read_sql(query, conn, params=(country_id, company_id))
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="No work orders found for the specified country and company")

    grouped = df.groupby("work_order_id")
    result = {}

    for work_order_id, group in grouped:
        record = {}
        for _, row in group.iterrows():
            key = row['name']
            val = row['attribute_value']
            val = process_attribute_value(val)
            record[key] = val
        result[work_order_id] = {"tsl_wo_work_order_attribute": record}

    return result
