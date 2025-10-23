from fastapi import FastAPI
from work_oder_json_convert import router as work_orders_router
from all_get_work_order_json_convert import router as all_get_work_order_json_convert_router
from billing_flow_api import router as billing_flow_router

app = FastAPI(
    title="Work Orders Facturación API",
    description="API para obtener datos de work orders con diferentes filtros y procesamiento de facturación",
    version="1.0.0"
)

# API 1: Obtener work orders por ID específico
app.include_router(work_orders_router, prefix="/api/work-orders", tags=["Work Orders by ID"])

# API 2: Obtener todos los work orders filtrados por country_id y company_id
app.include_router(all_get_work_order_json_convert_router, prefix="/api/filtered-orders", tags=["Filtered Orders"])

# API 3: Flujo completo de facturación con API externa
app.include_router(billing_flow_router, prefix="/api/billing-flow", tags=["Billing Flow"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)