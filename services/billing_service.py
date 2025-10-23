"""
Servicio principal para el procesamiento de facturación
"""
import asyncio
from typing import Dict, Any, List
import logging
from datetime import datetime

from clients.external_api_client import ExternalAPIClient
from database import fetch_filtered_work_orders
from config import build_simple_response

logger = logging.getLogger(__name__)

class BillingService:
    """Servicio principal para el procesamiento de facturación"""
    
    def __init__(self):
        self.external_client = ExternalAPIClient()
    
    async def process_billing_flow(self, country_id: int, company_id: str) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de facturación:
        1. Obtiene datos de la base de datos
        2. Procesa cada item con la API externa
        3. Retorna resultados consolidados
        
        Args:
            country_id: ID del país
            company_id: UUID de la empresa
            
        Returns:
            Resultado consolidado del procesamiento
        """
        start_time = datetime.now()
        logger.info(f"🚀 Iniciando flujo de facturación para country_id={country_id}, company_id={company_id}")
        
        try:
            # Paso 1: Obtener datos de la base de datos
            logger.info("📊 Obteniendo datos de la base de datos...")
            raw_data = fetch_filtered_work_orders(country_id, company_id)
            
            if not raw_data:
                logger.warning("⚠️ No se encontraron datos para los parámetros especificados")
                return {
                    "success": False,
                    "message": "No se encontraron datos para los parámetros especificados",
                    "country_id": country_id,
                    "company_id": company_id,
                    "processed_items": 0,
                    "successful_items": 0,
                    "failed_items": 0
                }
            
            # Paso 2: Construir items de facturación (SIN linkedRules para reducir bulk)
            logger.info("🔧 Construyendo items de facturación (modelo simple)...")
            context_list = [v for v in raw_data.values()]
            billing_items = build_simple_response(context_list)
            
            logger.info(f"📦 Se generaron {len(billing_items)} items de facturación")
            
            # Paso 3: Procesar con API externa
            logger.info("🌐 Procesando items con API externa...")
            processing_results = await self.external_client.process_billing_items_batch(billing_items)
            
            # Paso 4: Consolidar resultados
            successful_items = [r for r in processing_results if r.get("success", False)]
            failed_items = [r for r in processing_results if not r.get("success", False)]
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result = {
                "success": True,
                "message": "Flujo de facturación completado exitosamente",
                "country_id": country_id,
                "company_id": company_id,
                "processing_time_seconds": processing_time,
                "processed_items": len(processing_results),
                "successful_items": len(successful_items),
                "failed_items": len(failed_items),
                "success_rate": f"{(len(successful_items) / len(processing_results) * 100):.2f}%" if processing_results else "0%",
                "results": processing_results,
                "summary": {
                    "total_processed": len(processing_results),
                    "successful": len(successful_items),
                    "failed": len(failed_items),
                    "processing_time": f"{processing_time:.2f}s"
                }
            }
            
            logger.info(f"✅ Flujo completado: {len(successful_items)}/{len(processing_results)} exitosos en {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"💥 Error en flujo de facturación: {str(e)}")
            return {
                "success": False,
                "error": "Billing Flow Error",
                "details": str(e),
                "country_id": country_id,
                "company_id": company_id,
                "processed_items": 0,
                "successful_items": 0,
                "failed_items": 0
            }
    
    async def process_single_billing_item(self, billing_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un solo item de facturación
        
        Args:
            billing_item: Item individual con model y context
            
        Returns:
            Resultado del procesamiento
        """
        logger.info("🔄 Procesando item individual...")
        
        try:
            result = await self.external_client.process_billing_item(billing_item)
            
            if result.get("success", False):
                logger.info("✅ Item procesado exitosamente")
            else:
                logger.error(f"❌ Error procesando item: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Error procesando item individual: {str(e)}")
            return {
                "success": False,
                "error": "Single Item Processing Error",
                "details": str(e),
                "original_item": billing_item
            }
    
    def get_processing_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera estadísticas del procesamiento
        
        Args:
            results: Lista de resultados del procesamiento
            
        Returns:
            Estadísticas del procesamiento
        """
        total = len(results)
        successful = sum(1 for r in results if r.get("success", False))
        failed = total - successful
        
        error_types = {}
        for result in results:
            if not result.get("success", False):
                error = result.get("error", "Unknown")
                error_types[error] = error_types.get(error, 0) + 1
        
        return {
            "total_items": total,
            "successful_items": successful,
            "failed_items": failed,
            "success_rate": f"{(successful / total * 100):.2f}%" if total > 0 else "0%",
            "error_breakdown": error_types
        }
