"""
API endpoints para el flujo de facturación
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import logging

from services.billing_service import BillingService
from utils.logging_config import log_billing_flow_start, log_billing_flow_end

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/process")
async def process_billing_flow(
    country_id: int = Query(..., description="ID del país"),
    company_id: str = Query(..., description="UUID de la empresa")
) -> Dict[str, Any]:
    """
    Procesa el flujo completo de facturación para un país y empresa específicos
    
    Args:
        country_id: ID del país
        company_id: UUID de la empresa
        
    Returns:
        Resultado del procesamiento de facturación
    """
    try:
        # Log inicio del flujo
        log_billing_flow_start(country_id, company_id)
        
        # Crear instancia del servicio
        billing_service = BillingService()
        
        # Procesar flujo de facturación
        result = await billing_service.process_billing_flow(country_id, company_id)
        
        # Log fin del flujo
        log_billing_flow_end(
            country_id, 
            company_id, 
            result.get("success", False),
            result.get("processed_items", 0),
            result.get("successful_items", 0),
            result.get("failed_items", 0),
            result.get("processing_time_seconds", 0.0)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error en endpoint de facturación: {str(e)}")
        log_billing_flow_end(country_id, company_id, False, 0, 0, 0, 0.0)
        raise HTTPException(status_code=500, detail=f"Error procesando facturación: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Endpoint de salud para verificar que el servicio está funcionando
    
    Returns:
        Estado del servicio
    """
    return {
        "status": "healthy",
        "service": "billing_flow_api",
        "message": "Servicio de facturación funcionando correctamente"
    }

@router.get("/stats")
async def get_processing_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas del procesamiento de facturación
    
    Returns:
        Estadísticas del servicio
    """
    return {
        "service": "billing_flow_api",
        "endpoints": [
            "POST /process - Procesar flujo de facturación",
            "GET /health - Verificar salud del servicio",
            "GET /stats - Obtener estadísticas"
        ],
        "description": "API para el procesamiento de flujos de facturación"
    }
