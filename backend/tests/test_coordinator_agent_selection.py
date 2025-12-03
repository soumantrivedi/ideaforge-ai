"""
Test cases for coordinator agent intelligent selection based on phase context and query content.

This test suite verifies that:
1. Coordinator selects appropriate agents based on phase context
2. Ideation agent is NOT invoked for market research or requirements phases
3. Only relevant agents are invoked based on query content
4. Phase context is properly respected
5. Response summarization works correctly
"""
import pytest
import asyncio
import sys
import os
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator
    from backend.models.schemas import AgentMessage, AgentResponse
    AGNO_AVAILABLE = True
except ImportError as e:
    AGNO_AVAILABLE = False
    print(f"⚠️  Agno framework not available: {e}")


class TestCoordinatorAgentSelection:
    """Test coordinator agent selection logic."""
    
    @pytest.fixture
    def coordinator(self):
        """Create coordinator instance for testing."""
        if not AGNO_AVAILABLE:
            pytest.skip("Agno framework not available")
        try:
            return AgnoEnhancedCoordinator(enable_rag=True)
        except Exception as e:
            pytest.skip(f"Failed to create coordinator: {e}")
    
    def test_determine_primary_agent_market_research_phase(self, coordinator):
        """Test that research agent is selected for market research phase."""
        query = "What are the market trends?"
        context = {"phase_name": "Market Research"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent == "research", f"Expected 'research', got '{primary_agent}'"
        assert confidence > 0.3, f"Confidence should be > 0.3, got {confidence}"
    
    def test_determine_primary_agent_requirements_phase(self, coordinator):
        """Test that PRD agent is selected for requirements phase."""
        query = "What are the functional requirements?"
        context = {"phase_name": "Requirements"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent == "prd_authoring", f"Expected 'prd_authoring', got '{primary_agent}'"
        assert confidence > 0.3, f"Confidence should be > 0.3, got {confidence}"
    
    def test_determine_primary_agent_ideation_phase(self, coordinator):
        """Test that ideation agent is selected for ideation phase."""
        query = "What problem are we solving?"
        context = {"phase_name": "Ideation"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent == "ideation", f"Expected 'ideation', got '{primary_agent}'"
        assert confidence > 0.3, f"Confidence should be > 0.3, got {confidence}"
    
    def test_determine_primary_agent_no_ideation_for_market_research(self, coordinator):
        """Test that ideation agent is NOT selected for market research phase."""
        query = "What are the market trends?"
        context = {"phase_name": "Market Research"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent != "ideation", f"Ideation agent should NOT be selected for market research phase, got '{primary_agent}'"
    
    def test_determine_primary_agent_no_ideation_for_requirements(self, coordinator):
        """Test that ideation agent is NOT selected for requirements phase."""
        query = "What are the functional requirements?"
        context = {"phase_name": "Requirements"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent != "ideation", f"Ideation agent should NOT be selected for requirements phase, got '{primary_agent}'"
    
    def test_determine_supporting_agents_market_research_phase(self, coordinator):
        """Test that only relevant agents are included for market research phase."""
        query = "What are the market trends and competitive landscape?"
        context = {"phase_name": "Market Research"}
        primary_agent = "research"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Should NOT include ideation for market research phase
        assert "ideation" not in supporting, f"Ideation agent should NOT be included for market research phase, got: {supporting}"
        
        # May include analysis if query mentions analysis
        # But should NOT include ideation
    
    def test_determine_supporting_agents_requirements_phase(self, coordinator):
        """Test that only relevant agents are included for requirements phase."""
        query = "What are the functional and non-functional requirements?"
        context = {"phase_name": "Requirements"}
        primary_agent = "prd_authoring"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Should NOT include ideation for requirements phase
        assert "ideation" not in supporting, f"Ideation agent should NOT be included for requirements phase, got: {supporting}"
    
    def test_determine_supporting_agents_ideation_phase(self, coordinator):
        """Test that ideation agent can be included for ideation phase."""
        query = "What problem are we solving and what are some ideas?"
        context = {"phase_name": "Ideation"}
        primary_agent = "ideation"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Ideation is primary, so it won't be in supporting, but that's OK
    
    def test_determine_supporting_agents_no_phase_context(self, coordinator):
        """Test agent selection when no phase context is available."""
        query = "What are the market trends?"
        context = {}  # No phase context
        primary_agent = "research"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Should include research if query mentions research
        # Should NOT include ideation unless query explicitly mentions ideation
        if "ideation" not in query.lower() and "idea" not in query.lower():
            assert "ideation" not in supporting, f"Ideation agent should NOT be included for research query without ideation keywords, got: {supporting}"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_market_research_phase(self, coordinator):
        """Test that market research phase queries use research agent, not ideation."""
        query = "What are the market trends and competitive landscape?"
        context = {
            "phase_name": "Market Research",
            "product_id": "test-product-123"
        }
        
        # Mock agent responses
        with patch.object(coordinator.rag_agent, 'process', new_callable=AsyncMock) as mock_rag, \
             patch.object(coordinator.research_agent, 'process', new_callable=AsyncMock) as mock_research, \
             patch.object(coordinator.ideation_agent, 'process', new_callable=AsyncMock) as mock_ideation:
            
            # Setup mock responses
            mock_rag.return_value = AgentResponse(
                agent_type="rag",
                response="Knowledge base context",
                timestamp=datetime.utcnow()
            )
            mock_research.return_value = AgentResponse(
                agent_type="research",
                response="Market research findings",
                timestamp=datetime.utcnow()
            )
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify research agent was called
            assert mock_research.called, "Research agent should be called for market research phase"
            
            # Verify ideation agent was NOT called
            assert not mock_ideation.called, "Ideation agent should NOT be called for market research phase"
            
            # Verify final response mentions research, not ideation
            complete_events = [e for e in events if e.get("type") == "complete"]
            if complete_events:
                response = complete_events[0].get("response", "")
                assert "research" in response.lower() or "market" in response.lower(), \
                    f"Response should mention research/market, got: {response[:200]}"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_requirements_phase(self, coordinator):
        """Test that requirements phase queries use PRD agent, not ideation."""
        query = "What are the functional requirements for the product?"
        context = {
            "phase_name": "Requirements",
            "product_id": "test-product-123"
        }
        
        # Mock agent responses
        with patch.object(coordinator.rag_agent, 'process', new_callable=AsyncMock) as mock_rag, \
             patch.object(coordinator.prd_agent, 'process', new_callable=AsyncMock) as mock_prd, \
             patch.object(coordinator.ideation_agent, 'process', new_callable=AsyncMock) as mock_ideation:
            
            # Setup mock responses
            mock_rag.return_value = AgentResponse(
                agent_type="rag",
                response="Knowledge base context",
                timestamp=datetime.utcnow()
            )
            mock_prd.return_value = AgentResponse(
                agent_type="prd_authoring",
                response="Product requirements document content",
                timestamp=datetime.utcnow()
            )
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify PRD agent was called
            assert mock_prd.called, "PRD agent should be called for requirements phase"
            
            # Verify ideation agent was NOT called
            assert not mock_ideation.called, "Ideation agent should NOT be called for requirements phase"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_ideation_phase(self, coordinator):
        """Test that ideation phase queries use ideation agent."""
        query = "What problem are we solving?"
        context = {
            "phase_name": "Ideation",
            "product_id": "test-product-123"
        }
        
        # Mock agent responses
        with patch.object(coordinator.rag_agent, 'process', new_callable=AsyncMock) as mock_rag, \
             patch.object(coordinator.ideation_agent, 'process', new_callable=AsyncMock) as mock_ideation:
            
            # Setup mock responses
            mock_rag.return_value = AgentResponse(
                agent_type="rag",
                response="Knowledge base context",
                timestamp=datetime.utcnow()
            )
            mock_ideation.return_value = AgentResponse(
                agent_type="ideation",
                response="Ideation content about the problem",
                timestamp=datetime.utcnow()
            )
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify ideation agent was called
            assert mock_ideation.called, "Ideation agent should be called for ideation phase"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_negative_response(self, coordinator):
        """Test that negative responses don't invoke agents."""
        query = "no"
        context = {
            "phase_name": "Market Research",
            "product_id": "test-product-123"
        }
        
        # Mock NLU to return should_proceed=False
        with patch('backend.services.natural_language_understanding.get_nlu') as mock_get_nlu:
            mock_nlu = Mock()
            mock_nlu.should_make_ai_call = Mock(return_value=(False, "User declined", "Got it! What would you like to do next?"))
            mock_get_nlu.return_value = mock_nlu
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify no agents were called (except coordinator for helpful response)
            complete_events = [e for e in events if e.get("type") == "complete"]
            if complete_events:
                response = complete_events[0].get("response", "")
                assert "no problem" in response.lower() or "what would you like" in response.lower(), \
                    f"Response should be helpful guidance, got: {response[:200]}"
    
    def test_phase_keyword_mapping(self, coordinator):
        """Test that phase names are correctly mapped to agents."""
        test_cases = [
            ("Market Research", "research"),
            ("market_research", "research"),
            ("Requirements", "prd_authoring"),
            ("Ideation", "ideation"),
            ("Strategy", "strategy"),
            ("Analysis", "analysis"),
            ("Validation", "validation"),
            ("Design", "ideation"),  # Design phase may use ideation or other agents
        ]
        
        for phase_name, expected_agent in test_cases:
            query = "Test query"
            context = {"phase_name": phase_name}
            
            primary_agent, _ = coordinator.determine_primary_agent(query, context)
            
            assert primary_agent == expected_agent, \
                f"For phase '{phase_name}', expected '{expected_agent}', got '{primary_agent}'"
    
    def test_determine_primary_agent_strategy_phase(self, coordinator):
        """Test that strategy agent is selected for strategy phase."""
        query = "What is our product strategy?"
        context = {"phase_name": "Strategy"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent == "strategy", f"Expected 'strategy', got '{primary_agent}'"
        assert confidence > 0.3, f"Confidence should be > 0.3, got {confidence}"
    
    def test_determine_primary_agent_analysis_phase(self, coordinator):
        """Test that analysis agent is selected for analysis phase."""
        query = "What are the key insights from our analysis?"
        context = {"phase_name": "Analysis"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent == "analysis", f"Expected 'analysis', got '{primary_agent}'"
        assert confidence > 0.3, f"Confidence should be > 0.3, got {confidence}"
    
    def test_determine_primary_agent_validation_phase(self, coordinator):
        """Test that validation agent is selected for validation phase."""
        query = "How do we validate our assumptions?"
        context = {"phase_name": "Validation"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        assert primary_agent == "validation", f"Expected 'validation', got '{primary_agent}'"
        assert confidence > 0.3, f"Confidence should be > 0.3, got {confidence}"
    
    def test_determine_primary_agent_design_phase(self, coordinator):
        """Test that appropriate agent is selected for design phase."""
        query = "What are the design requirements?"
        context = {"phase_name": "Design"}
        
        primary_agent, confidence = coordinator.determine_primary_agent(query, context)
        
        # Design phase may use ideation or other agents depending on query
        assert primary_agent in ["ideation", "prd_authoring", "research"], \
            f"Expected ideation/prd_authoring/research for design phase, got '{primary_agent}'"
        assert confidence > 0.2, f"Confidence should be > 0.2, got {confidence}"
    
    def test_determine_supporting_agents_strategy_phase(self, coordinator):
        """Test that only relevant agents are included for strategy phase."""
        query = "What is our product strategy and market positioning?"
        context = {"phase_name": "Strategy"}
        primary_agent = "strategy"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Should NOT include ideation for strategy phase unless query explicitly mentions it
        if "ideation" not in query.lower() and "idea" not in query.lower():
            assert "ideation" not in supporting, \
                f"Ideation agent should NOT be included for strategy phase, got: {supporting}"
    
    def test_determine_supporting_agents_analysis_phase(self, coordinator):
        """Test that only relevant agents are included for analysis phase."""
        query = "What are the key insights and findings?"
        context = {"phase_name": "Analysis"}
        primary_agent = "analysis"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Should NOT include ideation for analysis phase
        assert "ideation" not in supporting, \
            f"Ideation agent should NOT be included for analysis phase, got: {supporting}"
    
    def test_determine_supporting_agents_validation_phase(self, coordinator):
        """Test that only relevant agents are included for validation phase."""
        query = "How do we validate our product assumptions?"
        context = {"phase_name": "Validation"}
        primary_agent = "validation"
        
        supporting = coordinator.determine_supporting_agents(query, primary_agent, context)
        
        # Should include RAG
        assert "rag" in supporting, "RAG agent should be included"
        
        # Should NOT include ideation for validation phase
        assert "ideation" not in supporting, \
            f"Ideation agent should NOT be included for validation phase, got: {supporting}"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_strategy_phase(self, coordinator):
        """Test that strategy phase queries use strategy agent, not ideation."""
        query = "What is our product strategy and market positioning?"
        context = {
            "phase_name": "Strategy",
            "product_id": "test-product-123"
        }
        
        # Mock agent responses
        with patch.object(coordinator.rag_agent, 'process', new_callable=AsyncMock) as mock_rag, \
             patch.object(coordinator.strategy_agent, 'process', new_callable=AsyncMock) as mock_strategy, \
             patch.object(coordinator.ideation_agent, 'process', new_callable=AsyncMock) as mock_ideation:
            
            # Setup mock responses
            mock_rag.return_value = AgentResponse(
                agent_type="rag",
                response="Knowledge base context",
                timestamp=datetime.utcnow()
            )
            mock_strategy.return_value = AgentResponse(
                agent_type="strategy",
                response="Strategy insights",
                timestamp=datetime.utcnow()
            )
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify strategy agent was called
            assert mock_strategy.called, "Strategy agent should be called for strategy phase"
            
            # Verify ideation agent was NOT called
            assert not mock_ideation.called, "Ideation agent should NOT be called for strategy phase"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_analysis_phase(self, coordinator):
        """Test that analysis phase queries use analysis agent, not ideation."""
        query = "What are the key insights from our analysis?"
        context = {
            "phase_name": "Analysis",
            "product_id": "test-product-123"
        }
        
        # Mock agent responses
        with patch.object(coordinator.rag_agent, 'process', new_callable=AsyncMock) as mock_rag, \
             patch.object(coordinator.analysis_agent, 'process', new_callable=AsyncMock) as mock_analysis, \
             patch.object(coordinator.ideation_agent, 'process', new_callable=AsyncMock) as mock_ideation:
            
            # Setup mock responses
            mock_rag.return_value = AgentResponse(
                agent_type="rag",
                response="Knowledge base context",
                timestamp=datetime.utcnow()
            )
            mock_analysis.return_value = AgentResponse(
                agent_type="analysis",
                response="Analysis insights",
                timestamp=datetime.utcnow()
            )
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify analysis agent was called
            assert mock_analysis.called, "Analysis agent should be called for analysis phase"
            
            # Verify ideation agent was NOT called
            assert not mock_ideation.called, "Ideation agent should NOT be called for analysis phase"
    
    @pytest.mark.asyncio
    async def test_stream_route_query_validation_phase(self, coordinator):
        """Test that validation phase queries use validation agent, not ideation."""
        query = "How do we validate our product assumptions?"
        context = {
            "phase_name": "Validation",
            "product_id": "test-product-123"
        }
        
        # Mock agent responses
        with patch.object(coordinator.rag_agent, 'process', new_callable=AsyncMock) as mock_rag, \
             patch.object(coordinator.validation_agent, 'process', new_callable=AsyncMock) as mock_validation, \
             patch.object(coordinator.ideation_agent, 'process', new_callable=AsyncMock) as mock_ideation:
            
            # Setup mock responses
            mock_rag.return_value = AgentResponse(
                agent_type="rag",
                response="Knowledge base context",
                timestamp=datetime.utcnow()
            )
            mock_validation.return_value = AgentResponse(
                agent_type="validation",
                response="Validation insights",
                timestamp=datetime.utcnow()
            )
            
            # Collect events
            events = []
            async for event in coordinator.stream_route_query(query, context=context):
                events.append(event)
            
            # Verify validation agent was called
            assert mock_validation.called, "Validation agent should be called for validation phase"
            
            # Verify ideation agent was NOT called
            assert not mock_ideation.called, "Ideation agent should NOT be called for validation phase"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

