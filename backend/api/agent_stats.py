"""
API endpoints for agent usage statistics and tracking.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from typing import Dict, List, Any
from datetime import datetime
import structlog
from backend.api.auth import get_current_user
from backend.database import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/usage-stats")
async def get_agent_usage_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get agent usage statistics for the current user from first login.
    Returns percentage usage, total counts, and usage by phase.
    """
    try:
        user_id = str(current_user["id"])
        tenant_id = str(current_user.get("tenant_id", ""))
        
        # Query conversation history to get agent usage (using tenant_id for filtering)
        # First get all records with phase_id (from column or interaction_metadata)
        query = text("""
            SELECT 
                agent_role,
                agent_name,
                phase_id,
                interaction_metadata,
                created_at,
                session_id
            FROM conversation_history
            WHERE tenant_id = :tenant_id 
                AND agent_role IS NOT NULL 
                AND agent_role != ''
        """)
        
        result = await db.execute(query, {"tenant_id": tenant_id})
        rows = result.fetchall()
        
        # Process rows in Python to extract phase_id and performance metrics from interaction_metadata
        # Also extract individual agent interactions from agent_interactions array
        agent_usage_data = []
        for row in rows:
            agent_role = row[0] or None
            agent_name = row[1] or None
            phase_id = row[2]  # Direct phase_id column
            interaction_metadata = row[3]  # JSONB field
            created_at = row[4]
            session_id = row[5]
            
            # Parse interaction_metadata
            metadata_dict = {}
            if interaction_metadata:
                try:
                    import json
                    if isinstance(interaction_metadata, dict):
                        metadata_dict = interaction_metadata
                    else:
                        metadata_dict = json.loads(interaction_metadata) if isinstance(interaction_metadata, str) else interaction_metadata
                except Exception:
                    metadata_dict = {}
            
            # Extract phase_id from interaction_metadata if phase_id is NULL
            if not phase_id and metadata_dict:
                phase_id_str = metadata_dict.get('phase_id')
                if phase_id_str:
                    try:
                        from uuid import UUID
                        phase_id = UUID(str(phase_id_str))
                    except (ValueError, TypeError):
                        phase_id = None
            
            # Extract performance metrics from metadata
            # Check if this is a direct agent interaction or part of agent_interactions array
            processing_time = 0.0
            tokens = 0
            cache_hits = 0
            cache_misses = 0
            
            # Normalize agent identifiers for matching
            def normalize_for_match(s: str) -> str:
                if not s:
                    return ''
                return s.lower().strip().replace('_', '').replace('-', '').replace(' ', '')
            
            agent_role_normalized = normalize_for_match(agent_role)
            agent_name_normalized = normalize_for_match(agent_name)
            
            # Check direct metadata first (for single agent responses)
            if 'processing_time' in metadata_dict:
                processing_time = float(metadata_dict.get('processing_time', 0.0))
                tokens_data = metadata_dict.get('tokens', {})
                if isinstance(tokens_data, dict):
                    tokens = tokens_data.get('total', 0)
                cache_hit = metadata_dict.get('cache_hit', False)
                if cache_hit:
                    cache_hits = 1
                else:
                    cache_misses = 1
            # Check agent_interactions array (for multi-agent responses) - aggregate all matching interactions
            elif 'agent_interactions' in metadata_dict:
                agent_interactions = metadata_dict.get('agent_interactions', [])
                for interaction in agent_interactions:
                    if isinstance(interaction, dict):
                        interaction_meta = interaction.get('metadata', {})
                        to_agent = interaction.get('to_agent', '')
                        to_agent_normalized = normalize_for_match(to_agent)
                        
                        # Match agent by role or name (more flexible matching)
                        if (to_agent_normalized == agent_role_normalized or 
                            to_agent_normalized == agent_name_normalized or
                            agent_role_normalized in to_agent_normalized or 
                            to_agent_normalized in agent_role_normalized):
                            processing_time += float(interaction_meta.get('processing_time', 0.0))
                            tokens_data = interaction_meta.get('tokens', {})
                            if isinstance(tokens_data, dict):
                                tokens += tokens_data.get('total', 0)
                            if interaction_meta.get('cache_hit', False):
                                cache_hits += 1
                            else:
                                cache_misses += 1
            # Check performance_metrics.agent_metrics (aggregated metrics)
            elif 'performance_metrics' in metadata_dict:
                perf_metrics = metadata_dict.get('performance_metrics', {})
                agent_metrics = perf_metrics.get('agent_metrics', {})
                # Try to find metrics for this agent
                for agent_key, metrics in agent_metrics.items():
                    agent_key_normalized = normalize_for_match(agent_key)
                    if (agent_key_normalized == agent_role_normalized or 
                        agent_key_normalized == agent_name_normalized or
                        agent_role_normalized in agent_key_normalized or 
                        agent_key_normalized in agent_role_normalized):
                        processing_time = float(metrics.get('processing_time', 0.0))
                        tokens = int(metrics.get('tokens', 0))
                        cache_hits = int(metrics.get('cache_hits', 0))
                        cache_misses = int(metrics.get('cache_misses', 0))
                        break
            
            # Determine cache_hit status for this record
            cache_hit = cache_hits > 0
            
            # Only add if agent_role exists (for direct agent responses)
            if agent_role:
                agent_usage_data.append({
                    'agent_role': agent_role,
                    'agent_name': agent_name or agent_role.replace('_', ' ').title(),
                    'phase_id': phase_id,
                    'created_at': created_at,
                    'session_id': session_id,
                    'processing_time': processing_time,
                    'tokens': tokens,
                    'cache_hit': cache_hit,
                    'cache_hits': cache_hits,
                    'cache_misses': cache_misses
                })
            
            # Also extract individual agent interactions from agent_interactions array
            # This ensures supporting agents are tracked even if they don't have direct rows
            if 'agent_interactions' in metadata_dict:
                agent_interactions = metadata_dict.get('agent_interactions', [])
                for interaction in agent_interactions:
                    if isinstance(interaction, dict):
                        to_agent = interaction.get('to_agent', '')
                        if to_agent:
                            interaction_meta = interaction.get('metadata', {})
                            interaction_processing_time = float(interaction_meta.get('processing_time', 0.0))
                            interaction_tokens_data = interaction_meta.get('tokens', {})
                            interaction_tokens = interaction_tokens_data.get('total', 0) if isinstance(interaction_tokens_data, dict) else 0
                            interaction_cache_hit = interaction_meta.get('cache_hit', False)
                            interaction_cache_hits = 1 if interaction_cache_hit else 0
                            interaction_cache_misses = 0 if interaction_cache_hit else 1
                            
                            agent_usage_data.append({
                                'agent_role': to_agent,
                                'agent_name': to_agent.replace('_', ' ').title(),
                                'phase_id': phase_id,
                                'created_at': created_at,
                                'session_id': session_id,
                                'processing_time': interaction_processing_time,
                                'tokens': interaction_tokens,
                                'cache_hits': interaction_cache_hits,
                                'cache_misses': interaction_cache_misses
                            })
        
        # Helper function to normalize role names consistently
        def normalize_role(role_or_name: str) -> str:
            """Normalize agent role/name to consistent format."""
            if not role_or_name:
                return 'unknown'
            # Convert to lowercase, replace spaces/hyphens with underscores
            normalized = role_or_name.lower().strip().replace(' ', '_').replace('-', '_')
            # Remove common prefixes/suffixes
            normalized = normalized.replace('agno_', '').replace('_agent', '')
            return normalized
        
        # Aggregate by agent_role, agent_name, and phase_id
        agent_usage_map: Dict[str, Dict[str, Any]] = {}
        usage_by_phase: Dict[str, int] = {}
        session_counts: Dict[str, set] = {}
        
        for data in agent_usage_data:
            agent_role = data['agent_role']
            agent_name = data['agent_name']
            phase_id = data['phase_id']
            created_at = data['created_at']
            session_id = data['session_id']
            processing_time = data.get('processing_time', 0.0)
            tokens = data.get('tokens', 0)
            cache_hits = data.get('cache_hits', 0)
            cache_misses = data.get('cache_misses', 0)
            
            # Track usage by phase
            if phase_id:
                phase_key = str(phase_id)
                usage_by_phase[phase_key] = usage_by_phase.get(phase_key, 0) + 1
            
            # Aggregate by agent role
            if agent_role not in agent_usage_map:
                agent_usage_map[agent_role] = {
                    'agent_name': agent_name,
                    'agent_role': agent_role,
                    'usage_count': 0,
                    'total_interactions': 0,
                    'last_used': None,
                    'total_processing_time': 0.0,
                    'total_tokens': 0,
                    'cache_hits': 0,
                    'cache_misses': 0,
                }
                session_counts[agent_role] = set()
            
            agent_usage_map[agent_role]['usage_count'] += 1
            agent_usage_map[agent_role]['total_interactions'] += 1
            agent_usage_map[agent_role]['total_processing_time'] += processing_time
            agent_usage_map[agent_role]['total_tokens'] += tokens
            agent_usage_map[agent_role]['cache_hits'] += cache_hits
            agent_usage_map[agent_role]['cache_misses'] += cache_misses
            if session_id:
                session_counts[agent_role].add(session_id)
            if created_at and (not agent_usage_map[agent_role]['last_used'] or created_at > agent_usage_map[agent_role]['last_used']):
                agent_usage_map[agent_role]['last_used'] = created_at
        
        # Calculate total usage
        total_usage = sum(data['usage_count'] for data in agent_usage_map.values())
        
        # Convert to list and calculate percentages with performance metrics
        agents = []
        for role, data in agent_usage_map.items():
            usage_percentage = (data['usage_count'] / total_usage * 100) if total_usage > 0 else 0
            
            # Calculate average processing time
            avg_processing_time = (data['total_processing_time'] / data['usage_count']) if data['usage_count'] > 0 else 0.0
            
            # Calculate cache hit rate
            total_cache_requests = data['cache_hits'] + data['cache_misses']
            cache_hit_rate = (data['cache_hits'] / total_cache_requests * 100) if total_cache_requests > 0 else 0.0
            
            agents.append({
                'agent_name': data['agent_name'],
                'agent_role': role,
                'usage_count': data['usage_count'],
                'usage_percentage': round(usage_percentage, 2),
                'total_interactions': data['total_interactions'],
                'last_used': data['last_used'].isoformat() if data['last_used'] else None,
                # Performance metrics from database
                'avg_processing_time': round(avg_processing_time, 2),
                'total_processing_time': round(data['total_processing_time'], 2),
                'cache_hit_rate': round(cache_hit_rate, 2),
                'total_tokens': data['total_tokens'],
            })
        
        # Get all available agents from orchestrator with profiling metrics
        # Import orchestrator directly from main module
        import backend.main as main_module
        orchestrator = main_module.orchestrator if hasattr(main_module, 'orchestrator') else None
        
        # Get all available agents
        all_agents = []
        agent_metrics_map = {}
        
        # Helper function to normalize role names consistently
        def normalize_role(role_or_name: str) -> str:
            """Normalize agent role/name to consistent format."""
            if not role_or_name:
                return 'unknown'
            # Convert to lowercase, replace spaces/hyphens with underscores
            normalized = role_or_name.lower().strip().replace(' ', '_').replace('-', '_')
            # Remove common prefixes/suffixes
            normalized = normalized.replace('agno_', '').replace('_agent', '')
            return normalized
        
        if orchestrator:
            # Get agents from orchestrator
            if hasattr(orchestrator, 'get_available_agents'):
                all_agents = orchestrator.get_available_agents()
            elif hasattr(orchestrator, 'agents'):
                # Build agent list from orchestrator.agents dict
                for agent_name, agent_instance in orchestrator.agents.items():
                    # Use agent's role if available, otherwise derive from name
                    agent_role = getattr(agent_instance, 'role', None) or agent_name
                    normalized_role = normalize_role(agent_role)
                    all_agents.append({
                        'name': agent_name,
                        'role': normalized_role,
                        'description': agent_role
                    })
            
            # Get agent metrics from orchestrator if available
            if hasattr(orchestrator, 'agents'):
                for agent_name, agent_instance in orchestrator.agents.items():
                    if hasattr(agent_instance, 'metrics'):
                        # Use agent's role if available, otherwise derive from name
                        agent_role = getattr(agent_instance, 'role', None) or agent_name
                        normalized_role = normalize_role(agent_role)
                        metrics = getattr(agent_instance, 'metrics', {})
                        # Aggregate metrics if role already exists (avoid duplicates)
                        if normalized_role in agent_metrics_map:
                            existing = agent_metrics_map[normalized_role]
                            agent_metrics_map[normalized_role] = {
                                'avg_time': max(existing.get('avg_time', 0.0), metrics.get('avg_time', 0.0)),
                                'total_time': existing.get('total_time', 0.0) + metrics.get('total_time', 0.0),
                                'total_calls': existing.get('total_calls', 0) + metrics.get('total_calls', 0),
                                'cache_hits': existing.get('cache_hits', 0) + metrics.get('cache_hits', 0),
                                'cache_misses': existing.get('cache_misses', 0) + metrics.get('cache_misses', 0),
                                'token_usage': {
                                    'input': existing.get('token_usage', {}).get('input', 0) + metrics.get('token_usage', {}).get('input', 0),
                                    'output': existing.get('token_usage', {}).get('output', 0) + metrics.get('token_usage', {}).get('output', 0),
                                },
                            }
                            # Recalculate avg_time
                            total_calls = agent_metrics_map[normalized_role]['total_calls']
                            if total_calls > 0:
                                agent_metrics_map[normalized_role]['avg_time'] = agent_metrics_map[normalized_role]['total_time'] / total_calls
                        else:
                            agent_metrics_map[normalized_role] = {
                                'avg_time': metrics.get('avg_time', 0.0),
                                'total_time': metrics.get('total_time', 0.0),
                                'total_calls': metrics.get('total_calls', 0),
                                'cache_hits': metrics.get('cache_hits', 0),
                                'cache_misses': metrics.get('cache_misses', 0),
                                'token_usage': metrics.get('token_usage', {'input': 0, 'output': 0}),
                            }
            
            # Also get metrics from coordinator agents (rag_agent, prd_agent, etc.)
            if hasattr(orchestrator, 'coordinator'):
                coordinator = orchestrator.coordinator
                # Check for common coordinator agent attributes
                coordinator_agents = {}
                if hasattr(coordinator, 'rag_agent') and coordinator.rag_agent:
                    coordinator_agents['rag'] = coordinator.rag_agent
                if hasattr(coordinator, 'prd_agent') and coordinator.prd_agent:
                    coordinator_agents['prd_authoring'] = coordinator.prd_agent
                if hasattr(coordinator, 'research_agent') and coordinator.research_agent:
                    coordinator_agents['research'] = coordinator.research_agent
                if hasattr(coordinator, 'analysis_agent') and coordinator.analysis_agent:
                    coordinator_agents['analysis'] = coordinator.analysis_agent
                if hasattr(coordinator, 'ideation_agent') and coordinator.ideation_agent:
                    coordinator_agents['ideation'] = coordinator.ideation_agent
                if hasattr(coordinator, 'summary_agent') and coordinator.summary_agent:
                    coordinator_agents['summary'] = coordinator.summary_agent
                if hasattr(coordinator, 'scoring_agent') and coordinator.scoring_agent:
                    coordinator_agents['scoring'] = coordinator.scoring_agent
                if hasattr(coordinator, 'validation_agent') and coordinator.validation_agent:
                    coordinator_agents['validation'] = coordinator.validation_agent
                if hasattr(coordinator, 'export_agent') and coordinator.export_agent:
                    coordinator_agents['export'] = coordinator.export_agent
                
                # Get metrics from coordinator agents
                for role, agent_instance in coordinator_agents.items():
                    if hasattr(agent_instance, 'metrics'):
                        normalized_role = normalize_role(role)
                        metrics = getattr(agent_instance, 'metrics', {})
                        # Aggregate with existing metrics if any
                        if normalized_role in agent_metrics_map:
                            existing = agent_metrics_map[normalized_role]
                            agent_metrics_map[normalized_role] = {
                                'avg_time': max(existing.get('avg_time', 0.0), metrics.get('avg_time', 0.0)),
                                'total_time': existing.get('total_time', 0.0) + metrics.get('total_time', 0.0),
                                'total_calls': existing.get('total_calls', 0) + metrics.get('total_calls', 0),
                                'cache_hits': existing.get('cache_hits', 0) + metrics.get('cache_hits', 0),
                                'cache_misses': existing.get('cache_misses', 0) + metrics.get('cache_misses', 0),
                                'token_usage': {
                                    'input': existing.get('token_usage', {}).get('input', 0) + metrics.get('token_usage', {}).get('input', 0),
                                    'output': existing.get('token_usage', {}).get('output', 0) + metrics.get('token_usage', {}).get('output', 0),
                                },
                            }
                            # Recalculate avg_time
                            total_calls = agent_metrics_map[normalized_role]['total_calls']
                            if total_calls > 0:
                                agent_metrics_map[normalized_role]['avg_time'] = agent_metrics_map[normalized_role]['total_time'] / total_calls
                        else:
                            agent_metrics_map[normalized_role] = {
                                'avg_time': metrics.get('avg_time', 0.0),
                                'total_time': metrics.get('total_time', 0.0),
                                'total_calls': metrics.get('total_calls', 0),
                                'cache_hits': metrics.get('cache_hits', 0),
                                'cache_misses': metrics.get('cache_misses', 0),
                                'token_usage': metrics.get('token_usage', {'input': 0, 'output': 0}),
                            }
        
        # Agent roles are already normalized in agent_usage_map, so no need to normalize again
        
        # Merge in-memory metrics as fallback (only if database metrics are missing)
        # Database metrics take precedence as they persist across restarts
        for agent in agents:
            role = normalize_role(agent['agent_role'])
            # Only use in-memory metrics if database metrics are all zero
            if agent.get('total_tokens', 0) == 0 and agent.get('total_processing_time', 0.0) == 0.0:
                if role in agent_metrics_map:
                    metrics = agent_metrics_map[role]
                    agent['avg_processing_time'] = round(metrics['avg_time'], 2)  # in seconds
                    agent['total_processing_time'] = round(metrics['total_time'], 2)
                    total_cache_requests = metrics['cache_hits'] + metrics['cache_misses']
                    agent['cache_hit_rate'] = round(
                        (metrics['cache_hits'] / total_cache_requests * 100) if total_cache_requests > 0 else 0,
                        2
                    )
                    agent['total_tokens'] = metrics['token_usage'].get('input', 0) + metrics['token_usage'].get('output', 0)
            # Ensure all metrics fields exist (database metrics already set above)
            if 'avg_processing_time' not in agent:
                agent['avg_processing_time'] = agent.get('avg_processing_time', 0.0)
            if 'total_processing_time' not in agent:
                agent['total_processing_time'] = agent.get('total_processing_time', 0.0)
            if 'cache_hit_rate' not in agent:
                agent['cache_hit_rate'] = agent.get('cache_hit_rate', 0.0)
            if 'total_tokens' not in agent:
                agent['total_tokens'] = agent.get('total_tokens', 0)
        
        # Deduplicate agents by role (keep the one with highest usage_count)
        agents_by_role = {}
        for agent in agents:
            role = normalize_role(agent['agent_role'])
            if role not in agents_by_role or agent['usage_count'] > agents_by_role[role]['usage_count']:
                agents_by_role[role] = agent
        
        # Convert back to list
        agents = list(agents_by_role.values())
        
        # Include agents that haven't been used yet (0 usage) - only if not already in list
        used_roles = {normalize_role(a['agent_role']) for a in agents}
        for agent_info in all_agents:
            # Handle different agent_info formats
            role = normalize_role(agent_info.get('role', '') or agent_info.get('type', '') or agent_info.get('name', ''))
            if not role or role == 'unknown':
                continue
            
            if role not in used_roles:
                metrics = agent_metrics_map.get(role, {})
                agent_name = agent_info.get('name', role.replace('_', ' ').title())
                # Calculate cache hit rate
                cache_hits = metrics.get('cache_hits', 0)
                cache_misses = metrics.get('cache_misses', 0)
                total_cache_requests = cache_hits + cache_misses
                cache_hit_rate = round(
                    (cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0,
                    2
                )
                
                agents.append({
                    'agent_name': agent_name,
                    'agent_role': role,
                    'usage_count': 0,
                    'usage_percentage': 0.0,
                    'total_interactions': 0,
                    'last_used': None,
                    # Use in-memory metrics as fallback for unused agents
                    'avg_processing_time': round(metrics.get('avg_time', 0.0), 2),
                    'total_processing_time': round(metrics.get('total_time', 0.0), 2),
                    'cache_hit_rate': cache_hit_rate,
                    'total_tokens': metrics.get('token_usage', {}).get('input', 0) + metrics.get('token_usage', {}).get('output', 0),
                })
                used_roles.add(role)  # Mark as added to prevent duplicates
        
        # Get phase names for usage_by_phase
        phase_query = text("""
            SELECT id, phase_name FROM product_lifecycle_phases
        """)
        phase_result = await db.execute(phase_query)
        phase_map = {}
        for row in phase_result.fetchall():
            # Handle both UUID and string IDs
            phase_id = row[0]
            phase_name = row[1]
            # Store both string and UUID representations
            phase_map[str(phase_id)] = phase_name
            if hasattr(phase_id, '__str__'):
                phase_map[phase_id.__str__()] = phase_name
        
        # Convert phase IDs to names
        usage_by_phase_named: Dict[str, int] = {}
        for phase_id, count in usage_by_phase.items():
            # Convert phase_id to string for lookup
            phase_id_str = str(phase_id) if phase_id else None
            phase_name = phase_map.get(phase_id_str, phase_id_str) if phase_id_str else 'Unknown Phase'
            # Aggregate counts if phase name already exists
            if phase_name in usage_by_phase_named:
                usage_by_phase_named[phase_name] += count
            else:
                usage_by_phase_named[phase_name] = count
        
        # Get usage trend (last 30 days)
        trend_query = text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM conversation_history
            WHERE tenant_id = :tenant_id 
                AND agent_role IS NOT NULL 
                AND agent_role != ''
                AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """)
        trend_result = await db.execute(trend_query, {"tenant_id": tenant_id})
        trend_rows = trend_result.fetchall()
        
        usage_trend = [
            {'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]), 'count': row[1]}
            for row in trend_rows
        ]
        
        return {
            'total_agents': len(all_agents),
            'total_usage': total_usage,
            'agents': sorted(agents, key=lambda x: x['usage_count'], reverse=True),
            'usage_by_phase': usage_by_phase_named,
            'usage_trend': usage_trend,
        }
        
    except Exception as e:
        logger.error("failed_to_get_agent_stats", error=str(e), user_id=str(current_user["id"]))
        raise HTTPException(status_code=500, detail=f"Failed to get agent statistics: {str(e)}")

