export interface AgentMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AgentContext {
  projectId: string;
  projectTitle: string;
  projectDescription: string;
  previousOutputs?: Record<string, unknown>;
}

export interface AgentResult {
  success: boolean;
  output: Record<string, unknown>;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface ResearchOutput {
  competitors: Array<{
    name: string;
    description: string;
    strengths: string[];
    weaknesses: string[];
  }>;
  marketTrends: string[];
  userNeeds: string[];
  technologicalConsiderations: string[];
}

export interface AnalysisOutput {
  targetAudience: string;
  valueProposition: string;
  coreFeatures: Array<{
    name: string;
    description: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  technicalFeasibility: string;
  marketOpportunity: string;
  risks: string[];
}

export interface PRDContent {
  overview: {
    title: string;
    version: string;
    author: string;
    date: string;
    summary: string;
  };
  problemStatement: string;
  goals: string[];
  targetUsers: {
    persona: string;
    needs: string[];
    painPoints: string[];
  }[];
  features: Array<{
    id: string;
    name: string;
    description: string;
    priority: 'P0' | 'P1' | 'P2';
    userStories: string[];
    acceptanceCriteria: string[];
  }>;
  technicalRequirements: {
    architecture: string;
    integrations: string[];
    security: string[];
    performance: string[];
  };
  successMetrics: Array<{
    metric: string;
    target: string;
  }>;
  timeline: {
    phase: string;
    duration: string;
    deliverables: string[];
  }[];
}

export interface ValidationOutput {
  isValid: boolean;
  completeness: number;
  issues: Array<{
    severity: 'critical' | 'warning' | 'info';
    section: string;
    message: string;
    suggestion: string;
  }>;
  recommendations: string[];
}
