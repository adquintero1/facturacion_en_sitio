# Work Orders Facturación API

API de FastAPI para obtener datos de work orders con diferentes filtros y opciones de descarga.

## Estructura del Proyecto

```
facturacion_en_sitio/
├── main.py                           # Archivo principal de FastAPI
├── config.py                         # Configuración común y funciones compartidas
├── database.py                       # Funciones de base de datos
├── work_oder_json_convert.py         # API 1: Work orders por ID
├── all_get_work_order_json_convert.py # API 2: Work orders filtrados
├── company_country_api.py            # API 3: Work orders por company/country
└── README.md                         # Documentación
```

## APIs Disponibles

### API 1: Work Orders por ID
**Endpoint:** `/api/work-orders/get_work_order`

Obtiene work orders específicos por sus IDs.

**Parámetros:**
- `work_order_ids`: Lista de IDs de work orders (múltiples valores)

**Ejemplo de uso:**
```
GET /api/work-orders/get_work_order?work_order_ids=123&work_order_ids=456
```

### API 2: Work Orders Filtrados
**Endpoint:** `/api/filtered-orders/get_all_work_orders`

Obtiene todos los work orders filtrados por country_id y company_id.

**Parámetros:**
- `country_id`: ID del país (int)
- `company_id`: UUID de la empresa (str)

**Ejemplo de uso:**
```
GET /api/filtered-orders/get_all_work_orders?country_id=27&company_id=200
```

**Endpoint de descarga:** `/api/filtered-orders/download_all_work_orders`
Descarga los datos como archivo JSON.

### API 3: Work Orders por Company/Country
**Endpoint:** `/api/company-country/get_work_orders_by_company_country`

Obtiene work orders filtrados por company_id y country_id (tercera API).

**Parámetros:**
- `company_id`: ID de la empresa (str)
- `country_id`: ID del país (int)

**Ejemplo de uso:**
```
GET /api/company-country/get_work_orders_by_company_country?company_id=200&country_id=27
```

**Endpoint de descarga:** `/api/company-country/download_work_orders_by_company_country`
Descarga los datos como archivo JSON con nombre personalizado.

## Configuración de Base de Datos

La configuración de la base de datos se encuentra en `config.py`:

```python
DB_CONFIG = {
    "host": "xxx.xxx.x.xx",
    "database": "dbxxxxxxxx",
    "user": "xxxxxx",
    "password": "xxxxxx",
    "port": 5x3x
}
```

## Respuesta de la API

Todas las APIs devuelven un JSON con la siguiente estructura:

```json
[
  {
    "model": {
      "contentType": "application/vnd.gorules.decision",
      "nodes": [...],
      "edges": [...]
    },
    "context": {
      "tsl_wo_work_order_attribute": {
        // Datos del work order
      }
    },
    "linkedRules": [
      // Reglas vinculadas
    ]
  }
]
```

## Ejecutar la API

```bash
python main.py
```

La API estará disponible en: `http://127.0.0.1:8000`

## Documentación Interactiva

Una vez ejecutada la API, puedes acceder a:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

## Características

- ✅ Tres APIs diferentes para diferentes casos de uso
- ✅ Filtrado por ID, country_id y company_id
- ✅ Descarga de datos como archivos JSON
- ✅ Documentación automática con Swagger
- ✅ Código refactorizado y reutilizable
- ✅ Manejo de errores HTTP
- ✅ Respuestas consistentes con modelo y reglas vinculadas

