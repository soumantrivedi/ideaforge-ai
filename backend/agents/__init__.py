# Legacy agents (for backward compatibility)
from .base_agent import BaseAgent
from .prd_authoring_agent import PRDAuthoringAgent
from .ideation_agent import IdeationAgent
from .jira_agent import JiraAgent
from .research_agent import ResearchAgent
from .analysis_agent import AnalysisAgent
from .validation_agent import ValidationAgent
from .strategy_agent import StrategyAgent
from .coordinator_agent import CoordinatorAgent
from .orchestrator import AgenticOrchestrator

# Agno framework agents
try:
    from .agno_base_agent import AgnoBaseAgent
    from .agno_prd_authoring_agent import AgnoPRDAuthoringAgent
    from .agno_ideation_agent import AgnoIdeationAgent
    from .agno_research_agent import AgnoResearchAgent
    from .agno_analysis_agent import AgnoAnalysisAgent
    from .rag_agent import RAGAgent
    from .agno_coordinator_agent import AgnoCoordinatorAgent
    from .agno_orchestrator import AgnoAgenticOrchestrator
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    # Define placeholders if Agno is not available
    AgnoBaseAgent = None
    AgnoPRDAuthoringAgent = None
    AgnoIdeationAgent = None
    AgnoResearchAgent = None
    AgnoAnalysisAgent = None
    RAGAgent = None
    AgnoCoordinatorAgent = None
    AgnoAgenticOrchestrator = None

__all__ = [
    # Legacy
    "BaseAgent",
    "PRDAuthoringAgent",
    "IdeationAgent",
    "JiraAgent",
    "ResearchAgent",
    "AnalysisAgent",
    "ValidationAgent",
    "StrategyAgent",
    "CoordinatorAgent",
    "AgenticOrchestrator",
    # Agno
    "AgnoBaseAgent",
    "AgnoPRDAuthoringAgent",
    "AgnoIdeationAgent",
    "AgnoResearchAgent",
    "AgnoAnalysisAgent",
    "RAGAgent",
    "AgnoCoordinatorAgent",
    "AgnoAgenticOrchestrator",
    "AGNO_AVAILABLE",
]
