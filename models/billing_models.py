"""
Modelos de datos para el sistema de facturación
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class BillingItemRequest(BaseModel):
    """Modelo para un item de facturación individual"""
    model: Dict[str, Any] = Field(..., description="Modelo de reglas de negocio")
    context: Dict[str, Any] = Field(..., description="Contexto del work order")
    linkedRules: Optional[List[Dict[str, Any]]] = Field(None, description="Reglas vinculadas")

class BillingItemResponse(BaseModel):
    """Modelo para la respuesta de un item procesado"""
    success: bool = Field(..., description="Indica si el procesamiento fue exitoso")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos de respuesta de la API externa")
    error: Optional[str] = Field(None, description="Tipo de error si falló")
    details: Optional[str] = Field(None, description="Detalles del error")
    original_item: Optional[BillingItemRequest] = Field(None, description="Item original procesado")

class BillingFlowRequest(BaseModel):
    """Modelo para la solicitud del flujo de facturación"""
    country_id: int = Field(..., description="ID del país", gt=0)
    company_id: str = Field(..., description="UUID de la empresa", min_length=1)

class BillingFlowResponse(BaseModel):
    """Modelo para la respuesta del flujo de facturación"""
    success: bool = Field(..., description="Indica si el flujo fue exitoso")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    country_id: int = Field(..., description="ID del país procesado")
    company_id: str = Field(..., description="UUID de la empresa procesada")
    processing_time_seconds: float = Field(..., description="Tiempo de procesamiento en segundos")
    processed_items: int = Field(..., description="Total de items procesados")
    successful_items: int = Field(..., description="Items procesados exitosamente")
    failed_items: int = Field(..., description="Items que fallaron en el procesamiento")
    success_rate: str = Field(..., description="Porcentaje de éxito")
    results: List[BillingItemResponse] = Field(..., description="Resultados detallados")
    summary: Dict[str, Any] = Field(..., description="Resumen del procesamiento")
    error: Optional[str] = Field(None, description="Error si el flujo falló")
    details: Optional[str] = Field(None, description="Detalles del error")

class ProcessingStatistics(BaseModel):
    """Modelo para estadísticas de procesamiento"""
    total_items: int = Field(..., description="Total de items procesados")
    successful_items: int = Field(..., description="Items exitosos")
    failed_items: int = Field(..., description="Items fallidos")
    success_rate: str = Field(..., description="Porcentaje de éxito")
    error_breakdown: Dict[str, int] = Field(..., description="Desglose de errores por tipo")

class ExternalAPIError(BaseModel):
    """Modelo para errores de la API externa"""
    error_type: str = Field(..., description="Tipo de error")
    status_code: Optional[int] = Field(None, description="Código de estado HTTP")
    message: str = Field(..., description="Mensaje de error")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp del error")

class BillingFlowSummary(BaseModel):
    """Modelo para resumen del flujo de facturación"""
    start_time: datetime = Field(..., description="Hora de inicio")
    end_time: datetime = Field(..., description="Hora de finalización")
    duration_seconds: float = Field(..., description="Duración en segundos")
    total_items: int = Field(..., description="Total de items")
    successful_items: int = Field(..., description="Items exitosos")
    failed_items: int = Field(..., description="Items fallidos")
    average_processing_time: float = Field(..., description="Tiempo promedio por item")
    throughput_items_per_second: float = Field(..., description="Throughput en items por segundo")

