"""
Procesador de facturación en sitio
Maneja el flujo completo de procesamiento de billing_items según calculation_order
"""
import json
import os
from typing import Dict, Any, List, Optional
import logging
from clients.external_api_client import ExternalAPIClient

logger = logging.getLogger(__name__)

class BillingProcessor:
    """Procesador principal para el flujo de facturación en sitio"""
    
    def __init__(self):
        self.metodos_base_path = os.path.join(os.path.dirname(__file__), "..", "rules", "metodos")
        self.precios_base_path = os.path.join(os.path.dirname(__file__), "..", "rules", "precios")
        self.external_client = ExternalAPIClient()
    
    async def process_billing_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa el resultado de la API externa y ejecuta el flujo de facturación
        
        Args:
            api_result: Resultado de la API externa con tsl_wo_work_order_attribute
            
        Returns:
            Resultado del procesamiento de facturación
        """
        try:
            logger.info("🔄 Iniciando procesamiento de facturación en sitio...")
            
            # Extraer tsl_wo_work_order_attribute del resultado
            tsl_attr = self._extract_tsl_attribute(api_result)
            if not tsl_attr:
                return {"success": False, "error": "No se encontró tsl_wo_work_order_attribute"}
            
            # Obtener active_energy_billing_items
            billing_items = tsl_attr.get("billing_items", {})
            active_energy_items = billing_items.get("active_energy_billing_items", [])
            
            if not active_energy_items:
                return {"success": False, "error": "No se encontraron active_energy_billing_items"}
            
            logger.info(f"📊 Encontrados {len(active_energy_items)} items de energía activa")
            
            # Ordenar por calculation_order y tomar el primero
            sorted_items = sorted(active_energy_items, key=lambda x: x.get("calculation_order", 999))
            first_item = sorted_items[0]
            
            logger.info(f"🎯 Procesando primer item: calculation_order={first_item.get('calculation_order')}, method={first_item.get('method')}")
            
            # Cargar y ejecutar la regla correspondiente
            rule_result = await self._execute_billing_rule(first_item, tsl_attr)
            
            return {
                "success": True,
                "processed_item": first_item,
                "rule_result": rule_result,
                "tsl_attributes": tsl_attr
            }
            
        except Exception as e:
            logger.error(f"💥 Error en procesamiento de facturación: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_tsl_attribute(self, api_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrae tsl_wo_work_order_attribute del resultado de la API"""
        try:
            if "data" in api_result and "tsl_wo_work_order_attribute" in api_result["data"]:
                return api_result["data"]["tsl_wo_work_order_attribute"]
            return None
        except Exception as e:
            logger.error(f"Error extrayendo tsl_attribute: {str(e)}")
            return None
    
    async def _execute_billing_rule(self, billing_item: Dict[str, Any], tsl_attr: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la regla de facturación correspondiente al método
        
        Args:
            billing_item: Item de facturación con method
            tsl_attr: Atributos del work order
            
        Returns:
            Resultado de la ejecución de la regla
        """
        try:
            method = billing_item.get("method")
            if not method:
                return {"success": False, "error": "No se especificó método de cálculo"}
            
            logger.info(f"📋 Cargando regla para método: {method}")
            
            # Construir ruta al archivo de regla
            rule_path = self._get_rule_path(method)
            if not rule_path or not os.path.exists(rule_path):
                return {"success": False, "error": f"No se encontró regla para método: {method}"}
            
            # Cargar la regla
            rule = self._load_rule(rule_path)
            if not rule:
                return {"success": False, "error": f"Error cargando regla: {rule_path}"}
            
            logger.info(f"✅ Regla cargada exitosamente: {rule_path}")
            
            # Ejecutar la regla (aquí implementarías la lógica específica de cada regla)
            execution_result = self._run_rule_logic(rule, tsl_attr, billing_item)
            
            # Ejecutar con API externa
            api_execution_result = await self._execute_rule_with_external_api(rule, tsl_attr, billing_item)
            
            return {
                "success": True,
                "rule_path": rule_path,
                "rule_name": method,
                "execution_result": execution_result,
                "api_execution_result": api_execution_result
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando regla: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_rule_path(self, method: str) -> Optional[str]:
        """Construye la ruta al archivo de regla basado en el método"""
        try:
            # El método debe coincidir con el nombre de la carpeta
            method_folder = os.path.join(self.metodos_base_path, method)
            if not os.path.exists(method_folder):
                logger.warning(f"Carpeta de método no encontrada: {method_folder}")
                return None
            
            # Buscar el archivo .json con el mismo nombre que el método
            rule_file = os.path.join(method_folder, f"{method}.json")
            if os.path.exists(rule_file):
                return rule_file
            
            # Si no existe, buscar cualquier archivo .json en la carpeta
            for file in os.listdir(method_folder):
                if file.endswith('.json'):
                    return os.path.join(method_folder, file)
            
            return None
            
        except Exception as e:
            logger.error(f"Error construyendo ruta de regla: {str(e)}")
            return None
    
    def _load_rule(self, rule_path: str) -> Optional[Dict[str, Any]]:
        """Carga la regla desde el archivo JSON"""
        try:
            with open(rule_path, 'r', encoding='utf-8') as f:
                rule = json.load(f)
            logger.info(f"📄 Regla cargada: {len(rule)} elementos")
            return rule
        except Exception as e:
            logger.error(f"Error cargando regla {rule_path}: {str(e)}")
            return None
    
    def _run_rule_logic(self, rule: Dict[str, Any], tsl_attr: Dict[str, Any], billing_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la lógica específica de la regla
        
        Args:
            rule: Regla cargada desde JSON
            tsl_attr: Atributos del work order
            billing_item: Item de facturación
            
        Returns:
            Resultado de la ejecución
        """
        try:
            logger.info("⚙️ Ejecutando lógica de regla...")
            
            # Aquí implementarías la lógica específica según el tipo de regla
            # Por ahora, retornamos información básica
            
            return {
                "rule_type": rule.get("contentType", "unknown"),
                "nodes_count": len(rule.get("nodes", [])),
                "edges_count": len(rule.get("edges", [])),
                "billing_item_code": billing_item.get("billing_item_code"),
                "calculation_order": billing_item.get("calculation_order"),
                "method": billing_item.get("method"),
                "supply_number": tsl_attr.get("supply_number"),
                "stratum": tsl_attr.get("stratum"),
                "active_energy_consumption": tsl_attr.get("active_energy_consumption")
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando lógica de regla: {str(e)}")
            return {"error": str(e)}
    
    async def _execute_rule_with_external_api(self, rule: Dict[str, Any], tsl_attr: Dict[str, Any], billing_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la regla con la API externa usando el nuevo modelo y contexto
        
        Args:
            rule: Regla cargada desde JSON
            tsl_attr: Atributos del work order
            billing_item: Item de facturación
            
        Returns:
            Resultado de la ejecución con API externa
        """
        try:
            logger.info("🌐 Ejecutando regla con API externa...")
            
            # Cargar parámetros
            parametros = self._load_parametros(billing_item.get("method"))
            if not parametros:
                return {"success": False, "error": "No se pudieron cargar los parámetros"}
            
            # Construir nuevo contexto
            new_context = self._build_new_context(tsl_attr, parametros)
            
            # Crear nuevo modelo con la regla
            new_model = {
                "model": rule,
                "context": new_context
            }
            
            logger.info(f"📦 Nuevo modelo creado con {len(rule.get('nodes', []))} nodos")
            logger.info(f"📋 Contexto construido con {len(new_context)} elementos")
            
            # Ejecutar con API externa
            api_result = await self.external_client.process_billing_item(new_model)
            
            if api_result.get("success", False):
                logger.info("✅ Regla ejecutada exitosamente con API externa")
                return {
                    "success": True,
                    "api_result": api_result,
                    "rule_executed": billing_item.get("method"),
                    "context_used": new_context
                }
            else:
                logger.error(f"❌ Error en API externa: {api_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": api_result.get("error", "API execution failed"),
                    "details": api_result.get("details", "No details available")
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando regla con API externa: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _load_parametros(self, method: str) -> Optional[Dict[str, Any]]:
        """Carga el archivo parametros.json del método especificado"""
        try:
            parametros_path = os.path.join(self.metodos_base_path, method, "parametros.json")
            
            if not os.path.exists(parametros_path):
                logger.warning(f"Archivo parametros.json no encontrado: {parametros_path}")
                return None
            
            with open(parametros_path, 'r', encoding='utf-8') as f:
                parametros = json.load(f)
            
            logger.info(f"📄 Parámetros cargados: {parametros_path}")
            return parametros
            
        except Exception as e:
            logger.error(f"Error cargando parámetros: {str(e)}")
            return None
    
    def _build_new_context(self, tsl_attr: Dict[str, Any], parametros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construye el nuevo contexto con la estructura correcta:
        {
            "tsl_wo_work_order_attribute": {...},
            "parametros_de_la_regla": {...}
        }
        
        Args:
            tsl_attr: Atributos del work order
            parametros: Parámetros de la regla
            
        Returns:
            Nuevo contexto con estructura correcta
        """
        try:
            logger.info("🔧 Construyendo nuevo contexto con estructura correcta...")
            
            # Crear contexto con estructura correcta y aplanar parámetros
            # Extraer el contenido de parametros_de_la_regla si está anidado
            if "parametros_de_la_regla" in parametros:
                parametros_aplanados = parametros["parametros_de_la_regla"]
            else:
                parametros_aplanados = parametros
            
            # Cargar precios basado en rate_code
            rate_code = tsl_attr.get("rate_code", "residencial")  # Default a residencial
            precios_data = self._load_precios_data(rate_code)
            
            new_context = {
                "tsl_wo_work_order_attribute": tsl_attr,
                "parametros_de_la_regla": parametros_aplanados,
                rate_code: precios_data  # Agregar precios con el rate_code como clave
            }
            
            logger.info(f"✅ Contexto construido con estructura correcta")
            logger.info(f"📋 tsl_wo_work_order_attribute: {len(tsl_attr)} elementos")
            logger.info(f"📋 parametros_de_la_regla: {list(parametros.keys())}")
            
            return new_context
            
        except Exception as e:
            logger.error(f"Error construyendo contexto: {str(e)}")
            return {}
    
    def _load_precios_data(self, rate_code: str) -> Dict[str, Any]:
        """
        Carga los datos de precios basado en el rate_code
        
        Args:
            rate_code: Código de tarifa (ej: 'residencial', 'comercial', etc.)
            
        Returns:
            Datos de precios cargados desde el archivo JSON
        """
        try:
            precios_path = os.path.join(self.precios_base_path, rate_code, f"{rate_code}.json")
            
            if not os.path.exists(precios_path):
                logger.warning(f"Archivo de precios no encontrado: {precios_path}")
                return {"prices_and_method": []}
            
            with open(precios_path, 'r', encoding='utf-8') as f:
                precios_data = json.load(f)
            
            # Si el archivo tiene la estructura {rate_code: {prices_and_method: [...]}}
            # extraer solo el contenido interno
            if rate_code in precios_data:
                precios_content = precios_data[rate_code]
            else:
                precios_content = precios_data
            
            logger.info(f"📄 Precios cargados para rate_code '{rate_code}': {precios_path}")
            return precios_content
            
        except Exception as e:
            logger.error(f"Error cargando precios para rate_code '{rate_code}': {str(e)}")
            return {"prices_and_method": []}
