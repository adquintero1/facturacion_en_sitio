"""
API endpoints para el flujo de facturación
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any
import logging

from services.billing_service import BillingService
from utils.logging_config import log_billing_flow_start, log_billing_flow_end

logger = logging.getLogger(__name__)

router = APIRouter()


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
            "POST /process-complete - Flujo completo con reglas ejecutadas",
            "POST /process-massive - Proceso masivo para múltiples órdenes",
            "GET /health - Verificar salud del servicio",
            "GET /stats - Obtener estadísticas"
        ],
        "description": "API para el procesamiento de flujos de facturación"
    }


@router.post("/process-complete")
async def process_complete_billing_flow(
    country_id: int = Query(..., description="ID del país"),
    company_id: str = Query(..., description="UUID de la empresa")
) -> Dict[str, Any]:
    """
    Procesa el flujo completo de facturación incluyendo ejecución de reglas
    
    Args:
        country_id: ID del país
        company_id: UUID de la empresa
        
    Returns:
        Resultado completo del procesamiento de facturación con reglas ejecutadas
    """
    try:
        logger.info("🚀 Iniciando flujo completo de facturación con reglas...")
        
        # Crear instancia del servicio
        billing_service = BillingService()
        
        # Paso 1: Procesar flujo inicial
        initial_result = await billing_service.process_billing_flow(country_id, company_id)
        
        if not initial_result.get("success", False):
            return initial_result
        
        # Paso 2: Continuar con procesamiento de reglas
        if initial_result.get("results") and len(initial_result["results"]) > 0:
            external_api_result = initial_result["results"][0]
            
            # Continuar procesamiento con reglas
            continue_result = await billing_service.continue_billing_processing(external_api_result)
            
            if continue_result.get("success", False):
                # Combinar resultados
                complete_result = {
                    "success": True,
                    "message": "Flujo completo de facturación con reglas ejecutado exitosamente",
                    "country_id": country_id,
                    "company_id": company_id,
                    "initial_processing": initial_result,
                    "rule_processing": continue_result,
                    "summary": {
                        "total_processed": initial_result.get("processed_items", 0),
                        "successful_items": initial_result.get("successful_items", 0),
                        "failed_items": initial_result.get("failed_items", 0),
                        "rules_executed": continue_result.get("billing_processing", {}).get("rule_result", {}).get("rule_name", "N/A")
                    }
                }
                
                logger.info("✅ Flujo completo de facturación con reglas completado exitosamente")
                return complete_result
            else:
                return {
                    "success": False,
                    "error": "Error en procesamiento de reglas",
                    "details": continue_result.get("error", "Unknown error"),
                    "initial_processing": initial_result
                }
        else:
            return {
                "success": False,
                "error": "No se obtuvieron resultados de la API externa",
                "initial_processing": initial_result
            }
        
    except Exception as e:
        logger.error(f"Error en flujo completo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en flujo completo: {str(e)}")

@router.post("/process-massive")
async def process_massive_billing_flow(
    country_id: int = Query(..., description="ID del país"),
    company_id: str = Query(..., description="UUID de la empresa")
) -> Dict[str, Any]:
    """
    Procesa el flujo masivo de facturación para múltiples órdenes
    
    Este endpoint maneja el proceso completo masivo:
    1. Obtiene múltiples órdenes de la base de datos
    2. Para cada orden ejecuta la API externa
    3. Para cada resultado procesa billing_items por calculation_order
    4. Ejecuta reglas según el method de cada item
    
    Args:
        country_id: ID del país
        company_id: UUID de la empresa
        
    Returns:
        Resultado del procesamiento masivo con todas las órdenes procesadas
    """
    try:
        logger.info("🚀 Iniciando proceso masivo de facturación...")
        
        # Crear instancia del servicio
        billing_service = BillingService()
        
        # Ejecutar proceso masivo
        result = await billing_service.process_massive_billing_flow(country_id, company_id)
        
        logger.info(f"✅ Proceso masivo completado: {result.get('success', False)}")
        return result
        
    except Exception as e:
        logger.error(f"Error en proceso masivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en proceso masivo: {str(e)}")
