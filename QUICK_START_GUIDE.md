# IdeaForge AI - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Launch the Application

```bash
# Start the platform
docker-compose up -d

# Or run locally
npm install
npm run dev
```

Access at: **http://localhost:3000** (or your configured port)

### Step 2: Configure AI Providers

1. Click **Settings** in the top navigation
2. Add at least one API key:
   - **OpenAI** (recommended - required for RAG/embeddings)
   - **Claude** (optional - Anthropic models)
   - **Gemini** (optional - Google models)
3. Click **Save Configuration**

### Step 3: Start Chatting!

1. Click **Chat** in the navigation
2. Select a **Coordination Mode**:
   - 🤝 **Collaborative** (default) - Best for most questions
   - ⚡ **Parallel** - Get multiple perspectives at once
   - 📋 **Sequential** - Step-by-step processing
   - ⚖️ **Debate** - Multiple viewpoints with synthesis
3. Type your question and press Enter
4. Watch multiple AI agents collaborate on your answer!

## 💡 Example Questions to Try

### For Code Expert (💻)
```
"Write a Python function to sort a list efficiently"
"Debug this JavaScript code: [paste code]"
"How do I optimize SQL queries?"
```

### For Research Specialist (🔬)
```
"Research the latest trends in AI development"
"What are the pros and cons of microservices?"
"Analyze the current state of quantum computing"
```

### For Creative Writer (✨)
```
"Write a short story about time travel"
"Give me creative names for a tech startup"
"Create a poem about innovation"
```

### For Data Analyst (📊)
```
"Analyze this sales data and find patterns"
"What metrics should I track for my app?"
"Create a dashboard layout for KPIs"
```

### For Complex Questions (Multiple Agents)
```
"How do I build a scalable e-commerce platform?"
→ Code Expert + Research Specialist + Data Analyst work together

"Create a business plan for an AI startup"
→ Research + Creative + Analysis + General collaborate

"Should I use React or Vue for my project?"
→ Debate mode: Multiple agents discuss and synthesize
```

## 🎨 Understanding the UI

### Chat Interface

**Coordination Mode Buttons**:
- 📋 Sequential - One after another
- ⚡ Parallel - All at once
- 🤝 Collaborative - Primary + consultations
- ⚖️ Debate - Discussion + synthesis

**Message Colors**:
- **Blue gradient** = Your messages
- **Gray with color badge** = Agent responses
- **Agent icon** shows which agent responded

**Interaction Indicators**:
- ⚡ icon + number = How many agent consultations occurred

### Agent Status Panel

**Agent Cards Show**:
- **Color-coded badges** for each agent type
- **Confidence bars** showing expertise level
- **Active status** (green check = working on your query)
- **Interaction count** for collaboration tracking

**What the Colors Mean**:
- 🤖 Blue/Cyan = General Assistant
- 🔬 Green/Emerald = Research Specialist
- 💻 Orange/Amber = Code Expert
- ✨ Pink/Rose = Creative Writer
- 📊 Purple/Violet = Data Analyst
- 📚 Teal/Cyan = Knowledge Retrieval

## 🎯 Coordination Modes Explained

### 🤝 Collaborative Mode (Recommended)
**When to use**: Most questions, especially complex ones

**How it works**:
1. One primary agent takes your question
2. It identifies what expertise is needed
3. Consults other agents behind the scenes
4. Synthesizes one comprehensive answer

**Example**:
```
You: "How do I build a secure REST API?"

Behind the scenes:
- Code Expert (primary) leads
- Consults Research Specialist for best practices
- Consults Data Analyst for performance patterns
- Returns one detailed, expert answer
```

### ⚡ Parallel Mode
**When to use**: Brainstorming, diverse perspectives

**How it works**:
1. Multiple agents respond simultaneously
2. You see separate responses from each
3. Compare different viewpoints

**Example**:
```
You: "Give me app ideas for productivity"

You get:
- General: Market-based suggestions
- Research: Trend analysis ideas
- Creative: Innovative concepts
- Analysis: Data-driven opportunities
```

### 📋 Sequential Mode
**When to use**: Step-by-step processes

**How it works**:
1. First agent completes their part
2. Second agent builds on it
3. Continues in order
4. Progressive refinement

**Example**:
```
You: "Plan, design, and code a login system"

Sequence:
1. Research: Security best practices
2. General: System design
3. Code Expert: Implementation
```

### ⚖️ Debate Mode
**When to use**: Decision-making, controversial topics

**How it works**:
1. Three agents discuss (2 rounds)
2. They respond to each other
3. Synthesis agent combines viewpoints
4. You get debate + final recommendation

**Example**:
```
You: "GraphQL vs REST API?"

Process:
- Round 1: Each agent presents case
- Round 2: Agents counter-argue
- Synthesis: Balanced recommendation
```

## 📚 Knowledge Base

### Add Documents
1. Click **Knowledge Base** in navigation
2. Click **Add Document**
3. Enter title and content
4. Documents become searchable by agents

### Using Knowledge
- Ask questions about your documents
- RAG agent automatically searches and retrieves
- Context is added to agent responses
- Works with all coordination modes

## ⚙️ Settings & Configuration

### API Keys
**OpenAI** (Required):
- Powers embeddings for knowledge search
- GPT-3.5/GPT-4 models
- Get key at: platform.openai.com

**Claude** (Optional):
- Anthropic's Claude models
- Excellent for analysis and writing
- Get key at: console.anthropic.com

**Gemini** (Optional):
- Google's Gemini models
- Fast and capable
- Get key at: makersuite.google.com

### Provider Selection
- System auto-assigns providers to agents
- First provider goes to most agents
- Additional providers distributed for variety
- You can use 1, 2, or all 3 providers

## 🔍 Tips & Tricks

### Get Better Responses
✅ **Be specific**: "Write Python code for X" > "Help with code"
✅ **Provide context**: Include relevant details
✅ **Ask follow-ups**: Build on previous responses
✅ **Try different modes**: Experiment with coordination

### Optimize Performance
✅ **Parallel for speed**: Get multiple quick responses
✅ **Collaborative for quality**: Best comprehensive answers
✅ **Sequential for learning**: See step-by-step process
✅ **Debate for decisions**: Thorough analysis

### Watch Agent Activity
✅ **Check confidence bars**: See agent expertise levels
✅ **Look for ⚡ icons**: Agent collaboration happening
✅ **Monitor active status**: Know who's working
✅ **Read agent names**: Understand specializations

## 🐛 Troubleshooting

### No Agents Responding?
1. ✅ Check API keys configured
2. ✅ Verify internet connection
3. ✅ Look for errors in browser console
4. ✅ Try refreshing the page

### Slow Responses?
1. ✅ Use Parallel mode for faster results
2. ✅ Check API rate limits
3. ✅ Verify network speed
4. ✅ Try with fewer agents

### Can't See Agent Status?
1. ✅ Expand agent panel (desktop)
2. ✅ Scroll to see all agents
3. ✅ Check responsive layout (mobile)

### Knowledge Base Not Working?
1. ✅ OpenAI API key required (for embeddings)
2. ✅ Check documents uploaded successfully
3. ✅ Try RAG agent specifically
4. ✅ Verify Supabase connection

## 📱 Mobile Usage

### Responsive Design
- ✅ Full functionality on mobile
- ✅ Stacked layout for small screens
- ✅ Touch-optimized buttons
- ✅ Swipe gestures supported

### Best Practices
- Use portrait orientation
- Tap mode buttons to switch
- Swipe to see agent panel
- Use keyboard shortcuts

## 🎓 Advanced Features

### Agent Consultation
- Agents automatically consult each other
- Tracked in interaction counts
- Visible in message metadata
- Improves answer quality

### Context Awareness
- Agents remember conversation history
- Build on previous responses
- Maintain conversation flow
- Reference earlier messages

### Confidence Scoring
- Each agent rates its capability
- Higher confidence = better match
- Helps with auto-routing
- Visible in agent panel

## 🚀 Next Steps

### Explore More
1. **Try all coordination modes** - Find your favorites
2. **Build knowledge base** - Add your documents
3. **Ask complex questions** - See agents collaborate
4. **Watch interactions** - Learn how agents work together

### Get Advanced
1. Check MULTI_AGENT_SYSTEM.md for architecture
2. Review agent capabilities in detail
3. Understand coordination strategies
4. Customize for your needs

## 💬 Example Conversations

### Beginner: Simple Question
```
You: "What is machine learning?"
Mode: Collaborative

Response: General Agent provides clear explanation
Time: ~5 seconds
Agents: 1 (General)
```

### Intermediate: Technical Question
```
You: "How do I optimize my database queries?"
Mode: Collaborative

Response: Code Expert consults Data Analyst, provides detailed answer
Time: ~10 seconds
Agents: 2 (Code + Analysis)
Interactions: 1 consultation
```

### Advanced: Complex Project
```
You: "Design a scalable microservices architecture for e-commerce"
Mode: Collaborative

Response:
- Code Expert (primary)
- Consults Research (best practices)
- Consults Analysis (performance patterns)
- Consults General (integration strategy)

Time: ~20 seconds
Agents: 4 active
Interactions: 3 consultations
Result: Comprehensive architecture plan
```

### Expert: Strategic Decision
```
You: "Should we migrate from monolith to microservices?"
Mode: Debate

Response:
- Round 1: 3 agents present viewpoints
- Round 2: Counter-arguments
- Synthesis: Balanced recommendation

Time: ~30 seconds
Agents: 4 (3 debating + 1 synthesis)
Interactions: 6 (debate rounds)
Result: Thorough analysis with recommendation
```

## 🎉 You're Ready!

Start asking questions and watch the magic of multi-agent collaboration!

---

**Need Help?**: Check MULTI_AGENT_SYSTEM.md for detailed documentation
**Found a Bug?**: Check browser console and troubleshooting section
**Want More?**: Explore advanced coordination modes and features

**Happy Collaborating! 🚀**
