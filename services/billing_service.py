"""
Servicio principal para el procesamiento de facturación
"""
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from clients.external_api_client import ExternalAPIClient
from database import fetch_filtered_work_orders
from config import build_simple_response
from .billing_processor import BillingProcessor

logger = logging.getLogger(__name__)

class BillingService:
    """Servicio principal para el procesamiento de facturación"""
    
    def __init__(self):
        self.external_client = ExternalAPIClient()
        self.billing_processor = BillingProcessor()
    
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
    
    async def continue_billing_processing(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Continúa el procesamiento de facturación después de la API externa
        
        Args:
            api_result: Resultado de la API externa con tsl_wo_work_order_attribute
            
        Returns:
            Resultado del procesamiento continuado
        """
        logger.info("🔄 Continuando procesamiento de facturación en sitio...")
        
        try:
            # Procesar el resultado de la API externa
            processing_result = await self.billing_processor.process_billing_result(api_result)
            
            if not processing_result.get("success", False):
                return processing_result
            
            # Agregar información adicional del procesamiento
            result = {
                "success": True,
                "message": "Procesamiento de facturación en sitio completado",
                "billing_processing": processing_result,
                "api_result": api_result
            }
            
            logger.info("✅ Procesamiento de facturación en sitio completado exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"💥 Error en procesamiento continuado: {str(e)}")
            return {
                "success": False,
                "error": "Billing Processing Error",
                "details": str(e)
            }
    
    async def process_massive_billing_flow(self, country_id: int, company_id: str) -> Dict[str, Any]:
        """
        Procesa el flujo masivo de facturación para múltiples órdenes
        
        Args:
            country_id: ID del país
            company_id: UUID de la empresa
            
        Returns:
            Resultado del procesamiento masivo
        """
        start_time = datetime.now()
        logger.info(f"🚀 Iniciando proceso masivo de facturación para country_id={country_id}, company_id={company_id}")
        
        try:
            # Paso 1: Obtener todas las órdenes de la base de datos
            logger.info("📊 Obteniendo órdenes de la base de datos...")
            raw_data = fetch_filtered_work_orders(country_id, company_id)
            
            if not raw_data:
                logger.warning("⚠️ No se encontraron órdenes para los parámetros especificados")
                return {
                    "success": False,
                    "message": "No se encontraron órdenes para los parámetros especificados",
                    "country_id": country_id,
                    "company_id": company_id,
                    "processed_orders": 0,
                    "successful_orders": 0,
                    "failed_orders": 0
                }
            
            logger.info(f"📦 Se encontraron {len(raw_data)} órdenes para procesar")
            
            # Paso 2: Procesar cada orden con API externa
            logger.info("🌐 Procesando órdenes con API externa...")
            context_list = [v for v in raw_data.values()]
            billing_items = build_simple_response(context_list)
            
            # Procesar con API externa
            processing_results = await self.external_client.process_billing_items_batch(billing_items)
            
            # Paso 3: Procesar cada resultado con reglas
            logger.info("🔧 Procesando resultados con reglas de facturación...")
            massive_results = []
            
            for i, api_result in enumerate(processing_results):
                if api_result.get("success", False):
                    logger.info(f"📋 Procesando orden {i+1}/{len(processing_results)} con reglas...")
                    
                    # Procesar con reglas
                    rule_processing = await self.billing_processor.process_billing_result(api_result)

                    final_execution_payload = rule_processing.get("final_execution_payload")
                    final_context_used = rule_processing.get("final_context_used")
                    rule_name = rule_processing.get("final_rule_name", "N/A")
                    second_phase_success = rule_processing.get("success", False)

                    if second_phase_success:
                        second_phase_result = final_execution_payload or {}
                        if final_context_used and isinstance(second_phase_result, dict):
                            second_phase_result.setdefault("context", final_context_used)
                    else:
                        failure_payload = final_execution_payload or {}
                        second_phase_result = {
                            "success": False,
                            "error": failure_payload.get("error"),
                            "details": failure_payload.get("details"),
                            "context": failure_payload.get("context") or failure_payload.get("context_used") or final_context_used
                        }
                    
                    concept_processing = None
                    third_phase_result = None
                    third_phase_success: Optional[bool] = None
                    third_phase_rule = None
                    
                    if second_phase_success:
                        concept_processing = await self.billing_processor.process_concept_chain(rule_processing)
                        third_phase_success = concept_processing.get("success", False)
                        third_phase_rule = concept_processing.get("final_rule_name", "N/A")
                        
                        if third_phase_success:
                            third_phase_result = concept_processing.get("final_execution_payload") or {}
                            final_context_phase3 = concept_processing.get("final_context_used")
                            if final_context_phase3 and isinstance(third_phase_result, dict):
                                third_phase_result.setdefault("context", final_context_phase3)
                        else:
                            failure_payload_phase3 = concept_processing.get("final_execution_payload") or {}
                            third_phase_result = {
                                "success": False,
                                "error": failure_payload_phase3.get("error") or concept_processing.get("error"),
                                "details": failure_payload_phase3.get("details"),
                                "context": failure_payload_phase3.get("context") or concept_processing.get("final_context_used")
                            }
                    else:
                        third_phase_success = None
                    
                    order_success = second_phase_success and (third_phase_success if third_phase_success is not None else True)
                    final_api_execution_success = third_phase_success if third_phase_success is not None else second_phase_success
                    
                    massive_results.append({
                        "order_index": i,
                        "first_api_result": api_result,  # Primera ejecución (inicial)
                        "second_api_result": second_phase_result,  # Resultado fase 2
                        "third_api_result": third_phase_result,    # Resultado fase 3
                        "success": order_success,
                        "rule_name": rule_name,
                        "second_phase_success": second_phase_success,
                        "third_phase_success": third_phase_success,
                        "third_phase_rule_name": third_phase_rule,
                        "api_execution_success": final_api_execution_success,
                        "chain_completed": concept_processing.get("chain_completed", False) if concept_processing else rule_processing.get("chain_completed", False)
                    })
                else:
                    logger.warning(f"⚠️ Orden {i+1} falló en API externa: {api_result.get('error', 'Unknown error')}")
                    massive_results.append({
                        "order_index": i,
                        "first_api_result": api_result,  # Primera ejecución (falló)
                        "second_api_result": None,  # No se ejecutó la segunda fase
                        "third_api_result": None,   # No se ejecutó la tercera fase
                        "success": False,
                        "error": api_result.get("error", "API execution failed"),
                        "api_execution_success": False,
                        "second_phase_success": None,
                        "third_phase_success": None
                    })
            
            # Paso 4: Consolidar resultados
            successful_orders = [r for r in massive_results if r.get("success", False)]
            failed_orders = [r for r in massive_results if not r.get("success", False)]
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result = {
                "success": True,
                "message": "Proceso masivo de facturación completado",
                "country_id": country_id,
                "company_id": company_id,
                "processing_time_seconds": processing_time,
                "total_orders": len(massive_results),
                "successful_orders": len(successful_orders),
                "failed_orders": len(failed_orders),
                "success_rate": f"{(len(successful_orders) / len(massive_results) * 100):.2f}%" if massive_results else "0%",
                "results": massive_results,
                "summary": {
                    "total_orders": len(massive_results),
                    "successful": len(successful_orders),
                    "failed": len(failed_orders),
                    "processing_time": f"{processing_time:.2f}s"
                }
            }
            
            logger.info(f"✅ Proceso masivo completado: {len(successful_orders)}/{len(massive_results)} órdenes exitosas en {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"💥 Error en proceso masivo: {str(e)}")
            return {
                "success": False,
                "error": "Massive Billing Process Error",
                "details": str(e),
                "country_id": country_id,
                "company_id": company_id,
                "processed_orders": 0,
                "successful_orders": 0,
                "failed_orders": 0
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
