"""
Cliente para la API externa de reglas de cálculo
"""
import httpx
import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ExternalAPIClient:
    """Cliente para interactuar con la API externa de reglas de cálculo"""
    
    def __init__(self):
        self.base_url = "https://devapi.softwarelabs.com.ar"
        self.endpoint = "/api/consumption/items/rules"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIyQXBBcy1yODB2SS12dk14U0NQRzd6MllyNEdIbFlNSWtBaDM1MEx6d29JIn0.eyJleHAiOjE3NjE2MDYzNDQsImlhdCI6MTc2MTU2Njc0NSwiYXV0aF90aW1lIjoxNzYxNTY2NzQ0LCJqdGkiOiJjMzI3ZGU3My1lYjZkLTQ0NDUtOGMxOS00YjE2N2ExY2Q4OWUiLCJpc3MiOiJodHRwczovL2tleWNsb2FrLnNvZnR3YXJlbGFicy5jb20uYXIvcmVhbG1zL1NvZnR3YXJlTGFicyIsImF1ZCI6WyJyZWFsbS1tYW5hZ2VtZW50Iiwic2RjIiwiUWFRdWVzdCIsIkZpZWxkbWF0ZSIsImJyb2tlciIsImFjY291bnQiLCJVc2VyTWFuYWdtZW50QVBJIl0sInN1YiI6IjRjYTg5OTk4LWVkZDEtNDc1ZS1hMzk3LTc3ZjNlMmI0YWRjNSIsInR5cCI6IkJlYXJlciIsImF6cCI6IkRldlF1ZXN0Iiwic2lkIjoiZGZjMmIwMWYtMjRjMy00MWFlLTkyNGItNmJiZmI1YmUwNzc0IiwiYWNyIjoiMSIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwczovL2Zlcy5zb2Z0d2FyZWxhYnMuY29tLmFyIiwiaHR0cHM6Ly9sb2NhbGhvc3Q6NTE3NCIsImh0dHBzOi8vbG9jYWxob3N0OjUxNzMiLCIqIiwiaHR0cHM6Ly8xOTIuMTY4LjEuMjA6NTE3MyIsImh0dHBzOi8vZGV2cXVlc3Quc29mdHdhcmVsYWJzLmNvbS5jbyIsImh0dHA6Ly8xOTIuMTY4LjEuMjA6NTE3MyIsImh0dHA6Ly9sb2NhbGhvc3Q6NTE3MyIsImh0dHBzOi8vZGV2cXVlc3Quc29mdHdhcmVsYWJzLmNvbS5hciJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiZGVmYXVsdC1yb2xlcy1zb2Z0d2FyZWxhYnMiLCJhZG1pbiIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiRGV2UXVlc3QiOnsicm9sZXMiOlsiY2lzLW5vdGlmaWNhdGlvbnMiLCJTYW1wbGUgUGFnZSAyIiwiU2FtcGxlIFBhZ2UiLCJCcmlnYWRlIE1hbmFnZXIiLCJmbS1lbnRlcnByaXNlLXN0cnVjdHVyZSIsImZtLXByb2R1Y3QtbWFuYWdlbWVudCIsIndvcmstZm9yY2UtbWFuYWdlbWVudCIsImJpbGxpbmctYW5vbWFsaWVzLW1hbmFnZW1lbnQiLCJjaXMtY2FsZW5kYXItbWFuYWdlbWVudCIsIndvcmstb3JkZXItbWFuYWdlbWVudCIsImZtLWdlb2dyYXBoaWMtc3RydWN0dXJlIiwiVW5pdCBNYW5hZ2VyIiwiY2lzLXByb2R1Y3QtbWFuYWdlbWVudCIsImNpcy1nZW9ncmFwaGljLXN0cnVjdHVyZSIsIkhvbWUiLCJEYXRhRW5naW5lIiwiZm0tcmF0ZXMtbWFuYWdlbWVudCIsImZtLWFkbWluLWdlbmVyYWwtZ3JvdXAiLCJjaXMtcmF0ZXMtbWFuYWdlbWVudCIsImNpcy1hZG1pbi1wcm9kdWN0cy1ncm91cCIsIkFkbWluaXN0cmFkb3IiLCJzdWJzaWRpZXMtbWFuYWdlbWVudCIsInVtYV9wcm90ZWN0aW9uIiwiZm0tYWRtaW4td29yay1vcmRlcnMtZ3JvdXAiLCJ0YXhlcy1tYW5hZ2VtZW50IiwiYnJpZ2FkZS1tYW5hZ2VtZW50IiwicmVhZGluZy1hbm9tYWxpZXMtbWFuYWdlbWVudCIsIkJQTU4iLCJjaXMtYWRtaW4tZ3JvdXAtMyIsImNpcy1hZG1pbi1ncm91cC0yIiwic2tpbGwtc2V0IiwiRVRMIiwiZm0tYWRtaW4td29yay1mb3JjZS1ncm91cCIsImZtLWNhbGVuZGFyLW1hbmFnZW1lbnQiLCJmbS1hZG1pbi1wcm9kdWN0cy1ncm91cCIsImZtLW5vdGlmaWNhdGlvbnMiXX0sInJlYWxtLW1hbmFnZW1lbnQiOnsicm9sZXMiOlsidmlldy1pZGVudGl0eS1wcm92aWRlcnMiLCJ2aWV3LXJlYWxtIiwibWFuYWdlLWlkZW50aXR5LXByb3ZpZGVycyIsImltcGVyc29uYXRpb24iLCJyZWFsbS1hZG1pbiIsImNyZWF0ZS1jbGllbnQiLCJtYW5hZ2UtdXNlcnMiLCJxdWVyeS1yZWFsbXMiLCJ2aWV3LWF1dGhvcml6YXRpb24iLCJxdWVyeS1jbGllbnRzIiwicXVlcnktdXNlcnMiLCJtYW5hZ2UtZXZlbnRzIiwibWFuYWdlLXJlYWxtIiwidmlldy1ldmVudHMiLCJ2aWV3LXVzZXJzIiwidmlldy1jbGllbnRzIiwibWFuYWdlLWF1dGhvcml6YXRpb24iLCJtYW5hZ2UtY2xpZW50cyIsInF1ZXJ5LWdyb3VwcyJdfSwic2RjIjp7InJvbGVzIjpbInVtYV9wcm90ZWN0aW9uIl19LCJRYVF1ZXN0Ijp7InJvbGVzIjpbIkFkbWluaXN0cmFkb3IiLCJIb21lIl19LCJGaWVsZG1hdGUiOnsicm9sZXMiOlsiZmllbGRtYXRlX2V4cG9ydF9kYiIsIkZpZWxkbWF0ZSJdfSwiYnJva2VyIjp7InJvbGVzIjpbInJlYWQtdG9rZW4iXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJ2aWV3LWFwcGxpY2F0aW9ucyIsInZpZXctY29uc2VudCIsInZpZXctZ3JvdXBzIiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJkZWxldGUtYWNjb3VudCIsIm1hbmFnZS1jb25zZW50Iiwidmlldy1wcm9maWxlIl19LCJVc2VyTWFuYWdtZW50QVBJIjp7InJvbGVzIjpbInVtYV9wcm90ZWN0aW9uIl19fSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImNvbXBhbnlJZCI6IjlmOWYwZjhmLWFhNmItNGNlOS05ZGM4LTIwYTg2YTMyMTRhYSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6IkRlbW8gSG9uZHVyYXMiLCJncm91cHMiOlsiL0FkbWluaXN0cmFkb3IiXSwiaWQiOiI0Y2E4OTk5OC1lZGQxLTQ3NWUtYTM5Ny03N2YzZTJiNGFkYzUiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJkZW1vQGVlaC5jb20iLCJnaXZlbl9uYW1lIjoiRGVtbyIsImZhbWlseV9uYW1lIjoiSG9uZHVyYXMiLCJjb3VudHJ5SWQiOiI2MCIsImVtYWlsIjoiZGVtb0BlZWguY29tIn0.kGX9FT2sbOYb6-J5hFzml3e60pazXqcqXb3sy5_34uiqbgXxgg39nuj0QRTGyhMAheExk9IYH4t3RjAbM1laAQZ05UWm237UTo79VebKKq3N1nvj_fPNSyTA7-N57ZGqA2W9kBIrpYKBqjOl6t_ILbeHmApgFci7U3pgLiC2GbXJoTkgLgfKVM-nMO9nRoz6R5GV3B1e0U8HsSIWk0PrLZcu9nR7qhKLjRF6ReOYGnFIFrvxMdt7nDcQthDkL01PjVp4hS83XNR-jEQSPc_D-ugV0eY0fKwjZWiZLdZQ2LTSfshsZJBOtgMut_JpMCSVTu4Xl1o0PKRjpruciL5I2w"
        }
    
    async def process_billing_item(self, billing_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un item de facturación individual con la API externa
        
        Args:
            billing_item: Objeto con model y context del item
            
        Returns:
            Resultado del procesamiento de la API externa
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoint}",
                    json=billing_item,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                    except ValueError:
                        logger.error("❌ Error parseando respuesta JSON de API externa (cuerpo vacío o inválido)")
                        return {
                            "success": False,
                            "error": "Invalid JSON response",
                            "details": response.text,
                            "status_code": response.status_code,
                            "context": billing_item.get("context", {})
                        }
                    logger.info(f"✅ Item procesado exitosamente: {billing_item.get('context', {}).get('tsl_wo_work_order_attribute', {}).get('supply_number', 'N/A')}")
                    return {
                        "success": True,
                        "data": result,
                        "context": billing_item.get("context", {})  # Solo mantener el context inicial
                    }
                else:
                    logger.error(f"❌ Error en API externa: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API Error: {response.status_code}",
                        "details": response.text,
                        "context": billing_item.get("context", {})  # Solo mantener el context inicial
                    }
                    
        except httpx.TimeoutException:
            logger.error("⏰ Timeout en API externa")
            return {
                "success": False,
                "error": "Timeout",
                "details": "La API externa no respondió en el tiempo esperado",
                "context": billing_item.get("context", {})  # Solo mantener el context inicial
            }
        except Exception as e:
            logger.error(f"💥 Error inesperado: {str(e)}")
            return {
                "success": False,
                "error": "Unexpected Error",
                "details": str(e),
                "context": billing_item.get("context", {})  # Solo mantener el context inicial
            }
    
    async def process_billing_items_batch(self, billing_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Procesa múltiples items de facturación en paralelo
        
        Args:
            billing_items: Lista de objetos con model y context
            
        Returns:
            Lista de resultados del procesamiento
        """
        logger.info(f"🚀 Iniciando procesamiento de {len(billing_items)} items")
        
        # Procesar en paralelo con semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(5)  # Máximo 5 requests simultáneos
        
        async def process_with_semaphore(item):
            async with semaphore:
                return await self.process_billing_item(item)
        
        tasks = [process_with_semaphore(item) for item in billing_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados y manejar excepciones
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"💥 Excepción en item {i}: {str(result)}")
                processed_results.append({
                    "success": False,
                    "error": "Processing Exception",
                    "details": str(result),
                    "context": billing_items[i].get("context", {})  # Solo mantener el context inicial
                })
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.get("success", False))
        logger.info(f"✅ Procesamiento completado: {successful}/{len(billing_items)} exitosos")
        
        return processed_results
