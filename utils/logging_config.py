"""
Configuración de logging para el sistema de facturación
"""
import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Configura el sistema de logging
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Archivo de log opcional
        
    Returns:
        Logger configurado
    """
    # Crear logger principal
    logger = logging.getLogger("billing_system")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Evitar duplicación de handlers
    if logger.handlers:
        return logger
    
    # Formato de los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo si se especifica
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Archivo siempre en DEBUG
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_billing_logger() -> logging.Logger:
    """Obtiene el logger configurado para el sistema de facturación"""
    return logging.getLogger("billing_system")

def log_billing_flow_start(country_id: int, company_id: str) -> None:
    """Log del inicio del flujo de facturación"""
    logger = get_billing_logger()
    logger.info(f"🚀 INICIANDO FLUJO DE FACTURACIÓN")
    logger.info(f"   📍 Country ID: {country_id}")
    logger.info(f"   🏢 Company ID: {company_id}")
    logger.info(f"   ⏰ Timestamp: {datetime.now().isoformat()}")

def log_billing_flow_end(country_id: int, company_id: str, success: bool, 
                        processed: int, successful: int, failed: int, 
                        duration: float) -> None:
    """Log del final del flujo de facturación"""
    logger = get_billing_logger()
    status = "✅ COMPLETADO" if success else "❌ FALLIDO"
    logger.info(f"🏁 FLUJO DE FACTURACIÓN {status}")
    logger.info(f"   📍 Country ID: {country_id}")
    logger.info(f"   🏢 Company ID: {company_id}")
    logger.info(f"   📊 Procesados: {processed}")
    logger.info(f"   ✅ Exitosos: {successful}")
    logger.info(f"   ❌ Fallidos: {failed}")
    logger.info(f"   ⏱️ Duración: {duration:.2f}s")
    logger.info(f"   📈 Tasa de éxito: {(successful/processed*100):.2f}%" if processed > 0 else "   📈 Tasa de éxito: 0%")

def log_api_call(url: str, method: str, status_code: Optional[int] = None, 
                duration: Optional[float] = None) -> None:
    """Log de llamadas a API externa"""
    logger = get_billing_logger()
    status_emoji = "✅" if status_code and 200 <= status_code < 300 else "❌"
    logger.info(f"🌐 API CALL {status_emoji}")
    logger.info(f"   🔗 URL: {url}")
    logger.info(f"   📡 Method: {method}")
    if status_code:
        logger.info(f"   📊 Status: {status_code}")
    if duration:
        logger.info(f"   ⏱️ Duration: {duration:.3f}s")

