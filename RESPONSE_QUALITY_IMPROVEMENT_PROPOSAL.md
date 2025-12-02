# Response Quality Improvement Proposal
## Improving Agno Agents to Match ChatGPT/Gemini Quality Without Increasing Latency

**Date:** December 2025  
**Status:** Proposal - Awaiting Selection

---

## Executive Summary

The current Agno agent implementation prioritizes latency optimization through aggressive context truncation, which results in:
- **Generic responses** that lack specificity
- **Lost critical data** from chatbot conversations and phase forms
- **Incomplete context** being passed to LLMs

This proposal outlines multiple strategies to improve response quality while maintaining or improving latency through smarter context management.

---

## Current Issues Identified

### 1. Context Truncation Problems

| Location | Current Limit | Impact |
|----------|--------------|--------|
| Message History | Last 3 messages only (`max_history_runs=3`) | Loses conversation context |
| Context Summary | 100 chars max | Critical details lost |
| Conversation History | Last 15 messages, 400 chars each | Recent context incomplete |
| Ideation from Chat | 1500 chars max | Product ideas truncated |
| Form Data Fields | 200 chars per field | Form details lost |
| Knowledge Base | 300 chars per item, top 5 only | RAG context incomplete |

### 2. Response Quality Issues

- **Generic responses**: System prompts don't emphasize using ALL available context
- **Missing details**: Critical user-provided information from forms/chat is not included
- **Summarization loss**: Older messages summarized to 100 chars lose critical details
- **Word limits**: Enforced limits (500/1000 words) may truncate comprehensive responses

### 3. Latency Optimizations (Already Good)

✅ Fast model tier selection (gpt-5.1-chat-latest, gemini-1.5-flash)  
✅ Parallel agent execution (60-80% latency reduction)  
✅ Response caching (Redis-based)  
✅ System/user prompt separation (40-60% token reduction)  
✅ Tool call history limiting  

---

## Proposed Solutions

### **Option A: Smart Context Prioritization (Recommended)**
**Latency Impact:** +5-10% | **Quality Impact:** +40-60%

#### Strategy
Instead of truncating, prioritize context by relevance and recency:
- **Recent messages** (last 5-7): Full content, no truncation
- **Older messages** (8-15): Intelligent summarization preserving key facts
- **Form data**: All fields included, no truncation
- **Chatbot context**: Full recent conversations, summarized older ones
- **Knowledge base**: Top 10 results with full content

#### Implementation
1. **Intelligent Message Summarization**
   - Use LLM to extract key facts from older messages (not just truncate)
   - Preserve: user requirements, decisions, preferences, constraints
   - Discard: redundant information, pleasantries

2. **Context Relevance Scoring**
   - Score each context piece by:
     - Recency (recent = higher score)
     - Relevance to current query (semantic similarity)
     - Information density (key facts vs. filler)
   - Include top-scoring context pieces fully, summarize lower-scoring ones

3. **Enhanced System Prompts**
   - Add explicit instructions: "You MUST use ALL provided context"
   - Emphasize: "Reference specific details from conversation history"
   - Include: "If user mentioned X in chat/form, you MUST incorporate it"

#### Code Changes
```python
# backend/agents/agno_base_agent.py
max_history_runs: int = 7  # Increased from 3
enable_intelligent_summarization: bool = True  # New
context_relevance_scoring: bool = True  # New

# backend/agents/agno_enhanced_coordinator.py
conversation_history_limit: int = 20  # Increased from 15
conversation_char_limit: int = 800  # Increased from 400
ideation_char_limit: int = 3000  # Increased from 1500
form_data_char_limit: int = 500  # Increased from 200
```

#### Benefits
- ✅ Preserves critical information
- ✅ Maintains low latency (only +5-10%)
- ✅ Improves response specificity
- ✅ Better context utilization

---

### **Option B: Two-Tier Context System**
**Latency Impact:** +0-5% | **Quality Impact:** +30-50%

#### Strategy
Use two context tiers:
- **Tier 1 (Fast)**: Essential context only (product_id, phase_name, current field)
- **Tier 2 (Comprehensive)**: Full context loaded asynchronously after initial response

#### Implementation
1. **Initial Response (Fast)**
   - Use minimal essential context
   - Generate quick response
   - Stream to user immediately

2. **Context Enhancement (Background)**
   - Load full context asynchronously
   - Re-generate response with full context
   - Update user if significantly different

3. **Smart Caching**
   - Cache responses by context hash
   - If full context available, use cached comprehensive response

#### Code Changes
```python
# New async context loader
async def load_comprehensive_context_async(product_id, session_ids):
    # Load in background
    pass

# Two-phase response generation
async def generate_response_two_tier(query, essential_context):
    # Phase 1: Fast response
    fast_response = await agent.process(query, essential_context)
    yield fast_response
    
    # Phase 2: Enhanced response (if context loaded)
    if comprehensive_context_ready:
        enhanced_response = await agent.process(query, comprehensive_context)
        yield enhanced_response
```

#### Benefits
- ✅ Minimal latency impact
- ✅ Progressive enhancement
- ✅ Better user experience (immediate + enhanced)

---

### **Option C: Context Compression with Semantic Preservation**
**Latency Impact:** +3-8% | **Quality Impact:** +35-55%

#### Strategy
Instead of truncation, use semantic compression:
- Extract key entities, facts, and relationships
- Preserve semantic meaning while reducing tokens
- Use structured context format (JSON) for efficiency

#### Implementation
1. **Entity Extraction**
   - Extract: product names, features, requirements, decisions
   - Store as structured data (not free text)
   - Include in context as JSON

2. **Fact Preservation**
   - Extract key facts: "User wants X", "Product has Y feature"
   - Preserve relationships: "Feature A depends on Feature B"
   - Include in compact structured format

3. **Semantic Summarization**
   - Use LLM to summarize while preserving key facts
   - Focus on information density, not character count
   - Preserve user-specific details

#### Code Changes
```python
# New context compressor
def compress_context_semantically(context: Dict) -> Dict:
    # Extract entities and facts
    entities = extract_entities(context)
    facts = extract_facts(context)
    relationships = extract_relationships(context)
    
    return {
        "entities": entities,
        "facts": facts,
        "relationships": relationships,
        "recent_messages": context["recent_messages"]  # Full recent
    }
```

#### Benefits
- ✅ Preserves semantic meaning
- ✅ Reduces token count efficiently
- ✅ Maintains low latency
- ✅ Better than truncation

---

### **Option D: Enhanced System Prompts + Context Injection**
**Latency Impact:** +0-2% | **Quality Impact:** +20-40%

#### Strategy
Improve how context is used without changing context size:
- Enhance system prompts to emphasize context usage
- Add explicit context injection points
- Improve context formatting for LLM consumption

#### Implementation
1. **Enhanced System Prompts**
   ```python
   system_prompt = f"""
   {base_prompt}
   
   CRITICAL CONTEXT USAGE INSTRUCTIONS:
   - You MUST reference specific details from the conversation history
   - If the user mentioned X in chat, you MUST incorporate it
   - Use ALL form data fields provided - nothing should be omitted
   - Reference specific phase content when relevant
   - If context contains Y, you MUST use it in your response
   
   CONTEXT PROVIDED:
   - Conversation History: {len(conversation_history)} messages
   - Form Data: {len(form_data)} fields
   - Phase Context: {phase_name}
   - Knowledge Base: {len(kb_items)} items
   
   Your response MUST demonstrate that you've used this context.
   """
   ```

2. **Structured Context Format**
   - Format context as structured sections
   - Add clear labels: "USER MENTIONED:", "FORM DATA:", "PHASE CONTEXT:"
   - Make it easy for LLM to parse and use

3. **Context Validation**
   - After response generation, verify key context was used
   - If missing, regenerate with stronger emphasis

#### Code Changes
```python
# Enhanced system prompt builder
def build_enhanced_system_prompt(base_prompt, context):
    context_summary = f"""
    === AVAILABLE CONTEXT ===
    Conversation History: {len(context.get('conversation_history', []))} messages
    Form Data Fields: {list(context.get('form_data', {}).keys())}
    Phase: {context.get('phase_name', 'N/A')}
    Knowledge Base Items: {len(context.get('knowledge_base', []))}
    
    === CRITICAL REQUIREMENTS ===
    - You MUST use ALL provided context
    - Reference specific details from conversation history
    - Include ALL form data fields in your response
    - Demonstrate context awareness in your answer
    """
    
    return f"{base_prompt}\n\n{context_summary}"

# Context validation
def validate_context_usage(response, context):
    # Check if key context items were referenced
    missing_context = []
    for key in context.get('form_data', {}).keys():
        if key not in response.lower():
            missing_context.append(key)
    
    if missing_context:
        # Regenerate with stronger emphasis
        pass
```

#### Benefits
- ✅ Minimal latency impact
- ✅ Better context utilization
- ✅ Improved response quality
- ✅ Easy to implement

---

### **Option E: Hybrid Approach (Recommended for Production)**
**Latency Impact:** +5-10% | **Quality Impact:** +50-70%

#### Strategy
Combine the best of all options:
- **Option A** (Smart Context Prioritization) for message history
- **Option D** (Enhanced System Prompts) for better context usage
- **Option C** (Semantic Compression) for older context
- Keep current optimizations (fast models, parallel execution, caching)

#### Implementation Phases

**Phase 1: Quick Wins (Week 1)**
- Implement Option D (Enhanced System Prompts)
- Increase `max_history_runs` from 3 to 5
- Increase conversation history limits (15→20, 400→600 chars)
- Add context validation

**Phase 2: Smart Context (Week 2)**
- Implement intelligent summarization for older messages
- Add context relevance scoring
- Increase form data limits (200→500 chars)

**Phase 3: Semantic Compression (Week 3)**
- Implement entity extraction
- Add structured context format
- Optimize token usage

#### Code Changes Summary
```python
# Phase 1 Changes
max_history_runs: int = 5  # From 3
conversation_history_limit: int = 20  # From 15
conversation_char_limit: int = 600  # From 400
ideation_char_limit: int = 2500  # From 1500
form_data_char_limit: int = 500  # From 200

# Enhanced system prompts
system_prompt = build_enhanced_system_prompt(base_prompt, context)

# Phase 2: Intelligent summarization
if len(messages) > max_history_runs:
    older_messages = messages[:-max_history_runs]
    summarized = await intelligent_summarize(older_messages)
    # Preserve key facts, not just truncate

# Phase 3: Semantic compression
compressed_context = compress_context_semantically(full_context)
```

#### Benefits
- ✅ Best quality improvement
- ✅ Reasonable latency impact
- ✅ Phased implementation
- ✅ Backward compatible

---

## Comparison Matrix

| Option | Latency Impact | Quality Impact | Implementation Effort | Risk Level |
|--------|---------------|----------------|---------------------|------------|
| **A: Smart Prioritization** | +5-10% | +40-60% | Medium | Low |
| **B: Two-Tier System** | +0-5% | +30-50% | High | Medium |
| **C: Semantic Compression** | +3-8% | +35-55% | High | Medium |
| **D: Enhanced Prompts** | +0-2% | +20-40% | Low | Very Low |
| **E: Hybrid (Recommended)** | +5-10% | +50-70% | Medium-High | Low |

---

## Recommended Implementation Plan

### **Immediate (Option D - Week 1)**
1. Enhance system prompts to emphasize context usage
2. Increase basic limits (history: 3→5, conversation: 15→20)
3. Add context validation
4. **Expected Result:** +20-40% quality, +0-2% latency

### **Short-term (Option A - Week 2-3)**
1. Implement intelligent message summarization
2. Add context relevance scoring
3. Increase form data limits
4. **Expected Result:** +40-60% quality, +5-10% latency

### **Long-term (Option C - Week 4+)**
1. Implement semantic compression
2. Add entity extraction
3. Optimize token usage
4. **Expected Result:** +50-70% quality, +5-10% latency

---

## Success Metrics

### Quality Metrics
- **Context Utilization Rate**: % of provided context referenced in response
- **Specificity Score**: Number of specific details (names, features, requirements) mentioned
- **User Satisfaction**: Feedback on response relevance and completeness
- **Information Retention**: % of user-provided details preserved in response

### Latency Metrics
- **Average Response Time**: Should stay within +10% of current
- **P95 Response Time**: Should not exceed current +15%
- **Token Usage**: Monitor for efficiency

### Testing Plan
1. **A/B Testing**: Compare current vs. improved responses
2. **User Feedback**: Collect feedback on response quality
3. **Context Audit**: Verify all critical context is used
4. **Latency Monitoring**: Ensure latency stays acceptable

---

## Risk Mitigation

### Latency Risks
- **Mitigation**: Implement in phases, monitor closely
- **Rollback Plan**: Feature flags to disable if latency exceeds threshold
- **Optimization**: Continue using fast models, parallel execution, caching

### Quality Risks
- **Mitigation**: Context validation to ensure usage
- **Testing**: Comprehensive testing with real user scenarios
- **Monitoring**: Track context utilization metrics

---

## Next Steps

1. **Review and Select**: Choose option(s) to implement
2. **Create Implementation Plan**: Detailed tasks and timeline
3. **Set Up Monitoring**: Metrics and dashboards
4. **Implement Phase 1**: Quick wins (Option D)
5. **Measure and Iterate**: Based on results

---

## Questions for Discussion

1. Which option(s) align with your priorities?
2. What is the acceptable latency increase threshold?
3. Should we implement all phases or focus on specific ones?
4. Are there specific use cases we should prioritize?

---

**Document Status:** Proposal - Awaiting Selection  
**Next Review:** After option selection

