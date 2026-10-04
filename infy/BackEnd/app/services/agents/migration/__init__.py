from app.services.agents.migration.migration_analysis_agent import MigrationAnalysisAgent
from app.services.agents.migration.java_to_julia_agent import JavaToJuliaAgent
from app.services.agents.migration.migration_risk_agent import MigrationRiskAgent
from app.services.agents.migration.migration_error_detection_agent import MigrationErrorDetectionAgent
from app.services.agents.migration.migration_error_correction_agent import MigrationErrorCorrectionAgent
from app.services.agents.migration.migration_validation_agent import MigrationValidationAgent

migration_analysis_agent = MigrationAnalysisAgent()
java_to_julia_agent = JavaToJuliaAgent()
migration_risk_agent = MigrationRiskAgent()
migration_error_detection_agent = MigrationErrorDetectionAgent()
migration_error_correction_agent = MigrationErrorCorrectionAgent()
migration_validation_agent = MigrationValidationAgent()

__all__ = [
    "MigrationAnalysisAgent",
    "migration_analysis_agent",
    "JavaToJuliaAgent",
    "java_to_julia_agent",
    "MigrationRiskAgent",
    "migration_risk_agent",
    "MigrationErrorDetectionAgent",
    "migration_error_detection_agent",
    "MigrationErrorCorrectionAgent",
    "migration_error_correction_agent",
    "MigrationValidationAgent",
    "migration_validation_agent",
]
