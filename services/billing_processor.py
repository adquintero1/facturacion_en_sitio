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
        self.conceptos_base_path = os.path.join(os.path.dirname(__file__), "..", "rules", "conceptos")
        self.external_client = ExternalAPIClient()
    
    async def process_billing_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa el resultado de la API externa y ejecuta el flujo de facturación
        Procesa TODOS los billing_items de cada tipo en el orden especificado:
        1. active_energy_billing_items (todos)
        2. public_lighting_billing_items (todos)
        3. cleaning_billing_items (todos)
        
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
            
            # Obtener todos los tipos de billing_items
            billing_items = tsl_attr.get("billing_items", {})
            current_tsl_attr = tsl_attr
            final_api_result = None
            final_rule_name = None
            final_api_success = False
            chain_broken = False
            final_execution_payload = None
            final_context_used = None
            
            # Definir el orden de procesamiento
            billing_types = [
                ("active_energy_billing_items", "Energía Activa"),
                ("public_lighting_billing_items", "Alumbrado Público"),
                ("cleaning_billing_items", "Aseo")
            ]
            
            all_results = []
            total_processed = 0
            
            # Procesar cada tipo de billing_items
            for billing_type, type_name in billing_types:
                # Temporal: limitar fase 3 a energía activa
                if billing_type != "active_energy_billing_items":
                    logger.info(f"⏭️ Fase 3: se omite {type_name} (limitación temporal)")
                    continue
                items = billing_items.get(billing_type, [])
                
                if not items:
                    logger.info(f"📋 No se encontraron items de {type_name}")
                    continue
                
                logger.info(f"📊 Procesando {len(items)} items de {type_name}")
                
                # Ordenar por calculation_order
                sorted_items = sorted(items, key=lambda x: x.get("calculation_order", 999))
                
                # Procesar TODOS los items de este tipo
                type_results = []
                for i, item in enumerate(sorted_items):
                    if chain_broken:
                        logger.warning("⛔ Cadena de ejecución detenida por error previo, se omite el resto de los items")
                        break
                    
                    logger.info(f"🎯 Procesando item {i+1}/{len(sorted_items)} de {type_name}: calculation_order={item.get('calculation_order')}, method={item.get('method')}")
                    
                    # Ejecutar la regla correspondiente
                    rule_result = await self._execute_billing_rule(item, current_tsl_attr)
                    api_execution_result = rule_result.get("api_execution_result", {}) or {}
                    api_success = api_execution_result.get("success", False)
                    
                    if api_success:
                        updated_tsl_attr = api_execution_result.get("updated_tsl_attr")
                        if updated_tsl_attr:
                            current_tsl_attr = updated_tsl_attr
                        final_api_result = api_execution_result.get("api_result")
                        final_execution_payload = api_execution_result.get("api_result")
                        final_context_used = api_execution_result.get("context_used")
                        final_rule_name = rule_result.get("rule_name")
                        final_api_success = True
                        logger.info("🔗 Cadena actualizada con el resultado de la ejecución actual")
                    else:
                        chain_broken = True
                        final_api_success = False
                        final_execution_payload = api_execution_result
                        final_context_used = api_execution_result.get("context_used")
                        logger.error("❌ La ejecución de la API externa falló, se interrumpe la cadena de facturación")
                    
                    type_results.append({
                        "item_index": i,
                        "calculation_order": item.get("calculation_order"),
                        "method": item.get("method"),
                        "billing_item_code": item.get("billing_item_code"),
                        "rule_result": rule_result,
                        "success": rule_result.get("success", False)
                    })
                    
                    total_processed += 1
                    
                    if chain_broken:
                        break
                
                all_results.append({
                    "billing_type": billing_type,
                    "type_name": type_name,
                    "total_items": len(items),
                    "processed_items": len(type_results),
                    "results": type_results
                })
                
                if chain_broken:
                    break
            
            if total_processed == 0:
                return {"success": False, "error": "No se encontraron billing_items para procesar"}
            
            logger.info(f"✅ Procesamiento completado: {total_processed} items procesados en {len(all_results)} tipos")
            
            return {
                "success": final_api_success and not chain_broken,
                "total_processed": total_processed,
                "billing_types_processed": len(all_results),
                "results_by_type": all_results,
                "tsl_attributes": tsl_attr,
                "final_tsl_attributes": current_tsl_attr,
                "final_api_result": final_api_result,
                "final_execution_payload": final_execution_payload,
                "final_context_used": final_context_used,
                "final_rule_name": final_rule_name,
                "chain_completed": not chain_broken,
                "final_api_success": final_api_success
            }
            
        except Exception as e:
            logger.error(f"💥 Error en procesamiento de facturación: {str(e)}")
            return {"success": False, "error": str(e)}

    async def process_concept_chain(self, phase_two_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la fase 3 (conceptos) encadenando la salida de la fase 2.
        Recorre los billing_items nuevamente en el mismo orden y ejecuta la regla
        correspondiente según el calculation_method encontrado en prices_and_method.
        """
        try:
            logger.info("🔄 Iniciando fase 3 de procesamiento de conceptos...")
            
            # Tomar como punto de partida el input final utilizado en la fase 2
            api_result = phase_two_result.get("api_result")
            base_tsl_attr = self._extract_tsl_attribute(api_result or {}) if isinstance(phase_two_result, dict) else None
            current_tsl_attr = base_tsl_attr or phase_two_result.get("final_tsl_attributes")
            
            if not current_tsl_attr:
                return {"success": False, "error": "No se encontró tsl_wo_work_order_attribute para iniciar la fase 3"}
            
            current_context: Dict[str, Any] = {"tsl_wo_work_order_attribute": current_tsl_attr}
            baseline_billing_items = self._clone_context(current_tsl_attr.get("billing_items", {}))
            
            billing_items = current_tsl_attr.get("billing_items", {})
            if not billing_items:
                return {"success": False, "error": "No se encontraron billing_items para la fase 3"}
            
            billing_types = [
                ("active_energy_billing_items", "Energía Activa"),
                ("public_lighting_billing_items", "Alumbrado Público"),
                ("cleaning_billing_items", "Aseo")
            ]
            
            total_processed = 0
            final_execution_payload = None
            final_context_used = None
            final_rule_name = None
            final_api_success = False
            chain_broken = False
            
            for billing_type, type_name in billing_types:
                items = billing_items.get(billing_type, [])
                if not items:
                    logger.info(f"📋 Fase 3: no hay items de {type_name}")
                    continue
                
                sorted_items = sorted(items, key=lambda x: x.get("calculation_order", 999))
                
                for item in sorted_items:
                    if chain_broken:
                        logger.warning("⛔ Fase 3: cadena detenida por error previo, se omiten items restantes")
                        break

                    self._enrich_billing_item_with_baseline(item, billing_type, baseline_billing_items)
                    if not self._get_calculation_method_code(item):
                        logger.info(f"⛔ Fase 3: billing_item '{item.get('billing_item_code')}' sin calculation_method, se omite")
                        continue
                    
                    concept_result = await self._execute_concept_rule(item, current_context)
                    total_processed += 1
                    
                    if concept_result.get("success", False):
                        updated_tsl_attr = concept_result.get("updated_tsl_attr")
                        if updated_tsl_attr:
                            current_tsl_attr = self._merge_tsl_attributes(current_tsl_attr, updated_tsl_attr)
                        final_execution_payload = concept_result.get("api_result")
                        final_context_used = concept_result.get("context_used")
                        # Preparar contexto mínimo para el siguiente item
                        current_context = {"tsl_wo_work_order_attribute": current_tsl_attr}
                        final_rule_name = concept_result.get("calculation_method")
                        final_api_success = True
                        logger.info(f"✅ Fase 3: regla {final_rule_name} ejecutada correctamente")
                    else:
                        chain_broken = True
                        final_api_success = False
                        final_execution_payload = {
                            "success": False,
                            "error": concept_result.get("error"),
                            "details": concept_result.get("details"),
                            "context": concept_result.get("context_used")
                        }
                        final_context_used = concept_result.get("context_used")
                        final_rule_name = concept_result.get("calculation_method")
                        logger.error(f"❌ Fase 3: error ejecutando regla {final_rule_name}")
                
                if chain_broken:
                    break
            
            if total_processed == 0:
                return {"success": False, "error": "No se procesaron billing_items en la fase 3"}
            
            return {
                "success": final_api_success and not chain_broken,
                "total_processed": total_processed,
                "final_execution_payload": final_execution_payload,
                "final_context_used": final_context_used,
                "final_tsl_attributes": current_tsl_attr,
                "final_rule_name": final_rule_name,
                "chain_completed": not chain_broken
            }
        
        except Exception as e:
            logger.error(f"💥 Error en fase 3 de conceptos: {str(e)}")
            return {"success": False, "error": str(e)}

    def _clone_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Hace una copia profunda segura del contexto para evitar mutaciones no deseadas."""
        if not context:
            return {}
        try:
            return json.loads(json.dumps(context))
        except Exception:
            return dict(context)

    def _ensure_legacy_identifiers(self, tsl_attr: Dict[str, Any]) -> None:
        """Asegura que cada billing_item tenga legacy_billing_item_id enumerable para las reglas."""
        billing_items = tsl_attr.get("billing_items", {})
        if not isinstance(billing_items, dict):
            return
        
        collections = [
            "active_energy_billing_items",
            "public_lighting_billing_items",
            "cleaning_billing_items"
        ]
        
        for key in collections:
            items = billing_items.get(key)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and not item.get("legacy_billing_item_id"):
                    item["legacy_billing_item_id"] = item.get("billing_item_code")

    def _merge_tsl_attributes(self, previous: Dict[str, Any], updated: Dict[str, Any]) -> Dict[str, Any]:
        """Combina atributos preservando información clave como prices_and_method."""
        if not previous:
            return updated or {}
        if not updated:
            return self._clone_context(previous)
        
        merged = self._clone_context(previous)
        
        for key, value in updated.items():
            if key != "billing_items":
                merged[key] = value
        
        prev_billing = previous.get("billing_items", {})
        updated_billing = updated.get("billing_items", {})
        if isinstance(prev_billing, dict) and isinstance(updated_billing, dict):
            merged_billing = self._clone_context(prev_billing)
            for category, items in updated_billing.items():
                if isinstance(items, list):
                    merged_list = []
                    prev_map = {}
                    prev_items = prev_billing.get(category, [])
                    if isinstance(prev_items, list):
                        for prev_item in prev_items:
                            if isinstance(prev_item, dict):
                                prev_map[prev_item.get("billing_item_code")] = prev_item
                    updated_codes = set()
                    for item in items:
                        if not isinstance(item, dict):
                            merged_list.append(item)
                            continue
                        code = item.get("billing_item_code")
                        if code:
                            updated_codes.add(code)
                        base = prev_map.get(code, {})
                        merged_item = self._clone_context(base)
                        merged_item.update(item)
                        # Asegurar fields críticos
                        if base and base.get("prices_and_method") and not merged_item.get("prices_and_method"):
                            merged_item["prices_and_method"] = base["prices_and_method"]
                        if base and base.get("calculation_method") and not merged_item.get("calculation_method"):
                            merged_item["calculation_method"] = base["calculation_method"]
                        if base and base.get("legacy_billing_item_id") and not merged_item.get("legacy_billing_item_id"):
                            merged_item["legacy_billing_item_id"] = base["legacy_billing_item_id"]
                        merged_list.append(merged_item)
                    for code, prev_item in prev_map.items():
                        if code not in updated_codes:
                            merged_list.append(self._clone_context(prev_item))
                    merged_billing[category] = merged_list
                else:
                    merged_billing[category] = items
            merged["billing_items"] = merged_billing
        else:
            merged["billing_items"] = updated_billing or prev_billing
        
        return merged
    
    def _enrich_billing_item_with_baseline(
        self,
        item: Dict[str, Any],
        billing_type: str,
        baseline_billing_items: Dict[str, Any]
    ) -> None:
        """Completa información faltante del billing_item desde los datos originales."""
        if not isinstance(item, dict) or not isinstance(baseline_billing_items, dict):
            return
        
        baseline_list = baseline_billing_items.get(billing_type)
        if not isinstance(baseline_list, list):
            return
        
        code = item.get("billing_item_code")
        baseline_item = next(
            (bi for bi in baseline_list if isinstance(bi, dict) and bi.get("billing_item_code") == code),
            None
        )
        if not baseline_item:
            return
        
        if not item.get("prices_and_method") and baseline_item.get("prices_and_method"):
            item["prices_and_method"] = self._clone_context(baseline_item["prices_and_method"])
        if not item.get("calculation_method") and baseline_item.get("calculation_method"):
            item["calculation_method"] = self._clone_context(baseline_item["calculation_method"])
        if not item.get("legacy_billing_item_id") and baseline_item.get("legacy_billing_item_id"):
            item["legacy_billing_item_id"] = baseline_item["legacy_billing_item_id"]
    
    def _extract_tsl_attribute(self, api_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrae tsl_wo_work_order_attribute del resultado de la API."""
        try:
            data_section = api_result.get("data") if isinstance(api_result, dict) else None
            if isinstance(data_section, dict) and "tsl_wo_work_order_attribute" in data_section:
                return self._clone_context(data_section["tsl_wo_work_order_attribute"])
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
                "success": api_execution_result.get("success", False),
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
                updated_tsl_attr = self._extract_tsl_attribute(api_result)
                if updated_tsl_attr is None:
                    logger.error("❌ La API externa no retornó tsl_wo_work_order_attribute en data")
                    return {
                        "success": False,
                        "error": "Missing tsl_wo_work_order_attribute",
                        "details": "La respuesta exitosa de la API no contiene data.tsl_wo_work_order_attribute",
                        "context_used": new_context
                    }
                logger.info("✅ Regla ejecutada exitosamente con API externa")
                return {
                    "success": True,
                    "api_result": api_result,
                    "rule_executed": billing_item.get("method"),
                    "context_used": new_context,
                    "updated_tsl_attr": updated_tsl_attr
                }
            else:
                logger.error(f"❌ Error en API externa: {api_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": api_result.get("error", "API execution failed"),
                    "details": api_result.get("details", "No details available"),
                    "context_used": new_context
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
            "parametros_de_la_regla": {...},
            "{rate_code}": {...}
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
            
            # Cargar precios basado en rate_code (lógica original)
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
            logger.info(f"📋 Rate code: {rate_code}")
            logger.info(f"📄 Precios cargados para '{rate_code}': {len(precios_data.get('prices_and_method', []))} items")
            
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

    async def _execute_concept_rule(self, billing_item: Dict[str, Any], base_context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la regla de concepto usando calculation_method."""
        try:
            tsl_attr = base_context.get("tsl_wo_work_order_attribute")
            calculation_method = self._get_calculation_method_code(billing_item)
            if not calculation_method:
                return {
                    "success": False,
                    "error": "El billing_item no contiene calculation_method en prices_and_method",
                    "context_used": base_context
                }
            
            rule_path = self._get_concept_rule_path(calculation_method)
            if not rule_path:
                return {
                    "success": False,
                    "error": f"No se encontró regla para calculation_method: {calculation_method}",
                    "context_used": base_context,
                    "calculation_method": calculation_method
                }
            
            rule = self._load_rule(rule_path)
            if not rule:
                return {
                    "success": False,
                    "error": f"Error cargando regla de concepto: {rule_path}",
                    "context_used": base_context,
                    "calculation_method": calculation_method
                }
            
            parametros = self._load_concept_parametros(calculation_method)
            if parametros is None:
                return {
                    "success": False,
                    "error": f"No se pudieron cargar los parámetros de concepto: {calculation_method}",
                    "context_used": base_context,
                    "calculation_method": calculation_method
                }
            
            context = self._build_concept_context(base_context, parametros, calculation_method, billing_item)
            new_model = {"model": rule, "context": context}
            
            api_result = await self.external_client.process_billing_item(new_model)
            if api_result.get("success", False):
                updated_tsl_attr = self._extract_tsl_attribute(api_result)
                return {
                    "success": True,
                    "api_result": api_result,
                    "updated_tsl_attr": updated_tsl_attr,
                    "context_used": context,
                    "calculation_method": calculation_method
                }
            
            return {
                "success": False,
                "error": api_result.get("error", "API execution failed"),
                "details": api_result.get("details", "No details available"),
                "context_used": context,
                    "calculation_method": calculation_method
                }
        
        except Exception as e:
            logger.error(f"Error ejecutando regla de concepto: {str(e)}")
            return {"success": False, "error": str(e), "context_used": base_context}

    def _get_calculation_method_code(self, billing_item: Dict[str, Any]) -> Optional[str]:
        """Obtiene el calculation_method asociado al billing_item."""
        try:
            prices_info = billing_item.get("prices_and_method")
            if isinstance(prices_info, dict):
                method = prices_info.get("calculation_method")
                if method:
                    return method
            
            method_info = billing_item.get("calculation_method")
            if isinstance(method_info, dict):
                code = method_info.get("calculation_method_code") or method_info.get("code")
                if code:
                    return code
            elif isinstance(method_info, str):
                return method_info
        except Exception as e:
            logger.error(f"Error obteniendo calculation_method: {str(e)}")
        return None

    def _get_concept_rule_path(self, calculation_method: str) -> Optional[str]:
        """Construye la ruta a la regla de concepto."""
        try:
            concept_folder = os.path.join(self.conceptos_base_path, calculation_method)
            if not os.path.exists(concept_folder):
                logger.warning(f"Carpeta de concepto no encontrada: {concept_folder}")
                return None
            
            rule_file = os.path.join(concept_folder, f"{calculation_method}.json")
            if os.path.exists(rule_file):
                return rule_file
            
            for file in os.listdir(concept_folder):
                if file.endswith(".json"):
                    return os.path.join(concept_folder, file)
        except Exception as e:
            logger.error(f"Error construyendo ruta de concepto: {str(e)}")
        return None

    def _load_concept_parametros(self, calculation_method: str) -> Optional[Dict[str, Any]]:
        """Carga los parámetros asociados a un calculation_method de concepto."""
        try:
            parametros_path = os.path.join(self.conceptos_base_path, calculation_method, "parametros.json")
            if not os.path.exists(parametros_path):
                logger.warning(f"Archivo de parámetros de concepto no encontrado: {parametros_path}")
                return None
            
            with open(parametros_path, "r", encoding="utf-8") as f:
                parametros = json.load(f)
            
            logger.info(f"📄 Parámetros de concepto cargados: {parametros_path}")
            return parametros
        except Exception as e:
            logger.error(f"Error cargando parámetros de concepto: {str(e)}")
            return None


    def _build_concept_context(
        self,
        base_context: Dict[str, Any],
        parametros: Dict[str, Any],
        calculation_method: str,
        billing_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construye el contexto para ejecutar una regla de concepto."""
        base_clone = self._clone_context(base_context)
        tsl_attr = base_clone.get("tsl_wo_work_order_attribute") if base_clone else None
        
        if not tsl_attr and base_context and "tsl_wo_work_order_attribute" in base_context:
            tsl_attr = base_context["tsl_wo_work_order_attribute"]
        
        if not tsl_attr:
            tsl_attr = {}
        
        tsl_attr_copy = self._clone_context({"tsl_wo_work_order_attribute": tsl_attr}).get("tsl_wo_work_order_attribute", {})
        self._ensure_legacy_identifiers(tsl_attr_copy)
        
        parametros_aplanados = parametros.get("parametros_de_la_regla", parametros)
        
        return {
            "tsl_wo_work_order_attribute": tsl_attr_copy,
            "parametros_de_la_regla": parametros_aplanados
        }
