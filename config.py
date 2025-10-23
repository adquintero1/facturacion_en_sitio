# Configuración común para todas las APIs
import json
import os
from typing import Any, Dict, List

# Configuración de DB
DB_CONFIG = {
    "host": "192.168.1.26",
    "database": "dbWorkOrderServices",
    "user": "admin",
    "password": "!Qazxsw2",
    "port": 5433
}

TABLE_NAME = "tsl_wo_work_order_attribute"

def load_model_from_json(file_path: str) -> Dict[str, Any]:
    """Carga el modelo desde un archivo JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Archivo {file_path} no encontrado. Usando modelo por defecto.")
        return get_default_model()
    except json.JSONDecodeError as e:
        print(f"⚠️  Error al parsear JSON en {file_path}: {e}. Usando modelo por defecto.")
        return get_default_model()

def get_default_model() -> Dict[str, Any]:
    """Modelo por defecto en caso de que falle la carga del JSON"""
    return {
        "contentType": "application/vnd.gorules.decision",
        "nodes": [],
        "edges": []
    }

def reload_model(new_file_path: str = None) -> Dict[str, Any]:
    """Recarga el modelo desde un archivo JSON específico o el archivo por defecto"""
    global MODEL
    if new_file_path:
        MODEL = load_model_from_json(new_file_path)
        print(f"🔄 MODEL recargado desde: {new_file_path}")
    else:
        MODEL = load_model_from_json(MODEL_FILE_PATH)
        print(f"🔄 MODEL recargado desde archivo por defecto: {MODEL_FILE_PATH}")
    return MODEL

# Cargar modelo dinámicamente desde archivo JSON
MODEL_FILE_PATH = os.path.join(os.path.dirname(__file__), "rules", "tarifas", "residencial", "AFINIA-EN001-ENRE001-TARIFA-RESIDENCIAL.json")
MODEL = load_model_from_json(MODEL_FILE_PATH)

# Mensaje de confirmación
print(f"✅ MODEL cargado desde: {MODEL_FILE_PATH}")
print(f"📊 Nodos en el modelo: {len(MODEL.get('nodes', []))}")
print(f"🔗 Conexiones en el modelo: {len(MODEL.get('edges', []))}")

# Modelo cargado dinámicamente desde archivo JSON
# El MODEL se carga automáticamente desde: rules/tarifas/AFINIA-EN001-ENRE001-TARIFA-RESIDENCIAL.json

# Reglas vinculadas comunes
LINKEDRULES = [
    {
        "key": "billing on-site-data preparation",
        "content": {
            "contentType": "application/vnd.gorules.decision",
            "nodes": [
                {
                    "type": "inputNode",
                    "content": {
                        "schema": ""
                    },
                    "id": "79f5d05f-eceb-46f7-9349-c84480ed5d07",
                    "name": "request",
                    "position": {
                        "x": 160,
                        "y": 315
                    }
                },
                {
                    "type": "outputNode",
                    "content": {
                        "schema": ""
                    },
                    "id": "f18708af-d30e-4701-8c14-4de30ce1449e",
                    "name": "response",
                    "position": {
                        "x": 920,
                        "y": 315
                    }
                },
                {
                    "type": "functionNode",
                    "content": {
                        "source": "import zen from 'zen';\n\n/** @type {Handler} **/\nexport const handler = async (input) => {\n  const tsl_wo_work_order_attribute = input?.tsl_wo_work_order_attribute || {};\n\n  const newJson = {\n    on_site_billing_data : {\n      supply_number: tsl_wo_work_order_attribute.supply_number,\n      reading_date: tsl_wo_work_order_attribute.reading_date,\n      active_energy_consumption: tsl_wo_work_order_attribute.active_energy_consumption,\n      active_energy_reading_value: tsl_wo_work_order_attribute.active_energy_reading_value,\n      active_energy_last_reading_value: tsl_wo_work_order_attribute.active_energy_last_reading_value,\n      stratum: tsl_wo_work_order_attribute.stratum,\n      // consumption_history: tsl_wo_work_order_attribute.active_energy_consumptions_history?.map(item => ({\n      //   name: item.name,\n      //   value: item.value\n      // })) || [],\n      billing_items: tsl_wo_work_order_attribute.billing_items || {}, \n      rates_prices: tsl_wo_work_order_attribute.rates_prices || {}\n    }\n  };\n\n  return newJson;\n};\n"
                    },
                    "id": "9ab04f7f-5e44-4dee-9b13-4bb341741e42",
                    "name": "JSON transform",
                    "position": {
                        "x": 505,
                        "y": 315
                    }
                }
            ],
            "edges": [
                {
                    "id": "c0c58aa9-4464-4654-a6cb-32d5d548c754",
                    "sourceId": "79f5d05f-eceb-46f7-9349-c84480ed5d07",
                    "targetId": "9ab04f7f-5e44-4dee-9b13-4bb341741e42",
                    "type": "edge"
                },
                {
                    "id": "10fd69df-cd5d-4ce2-8c0c-0ee067732e4f",
                    "sourceId": "9ab04f7f-5e44-4dee-9b13-4bb341741e42",
                    "targetId": "f18708af-d30e-4701-8c14-4de30ce1449e",
                    "type": "edge"
                }
            ]
        }
    }
]

def process_attribute_value(value: str) -> Any:
    """Procesa el valor de un atributo para convertirlo al tipo correcto"""
    if value is None:
        return ""
    value = value.strip()
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    try:
        if value.startswith("{") or value.startswith("["):
            return json.loads(value)
    except json.JSONDecodeError:
        pass
    return value

def build_custom_response(payload: Any) -> List[Dict[str, Any]]:
    """Construye la respuesta personalizada con el modelo y reglas vinculadas"""
    if isinstance(payload, list):
        return [
            {
                "model": MODEL,
                "context": item,
                "linkedRules": LINKEDRULES
            }
            for item in payload
        ]
    elif isinstance(payload, dict):
        return [
            {
                "model": MODEL,
                "context": payload,
                "linkedRules": LINKEDRULES
            }
        ]
    else:
        raise ValueError("El payload debe ser una lista o un diccionario.")

def build_simple_response(payload: Any) -> List[Dict[str, Any]]:
    """Construye la respuesta simple solo con modelo y contexto (sin linkedRules)"""
    if isinstance(payload, list):
        return [
            {
                "model": MODEL,
                "context": item
            }
            for item in payload
        ]
    elif isinstance(payload, dict):
        return [
            {
                "model": MODEL,
                "context": payload
            }
        ]
    else:
        raise ValueError("El payload debe ser una lista o un diccionario.")
