from typing import List, Dict, Any, Optional
from datetime import datetime
from jira import JIRA

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse, JiraIssue, JiraEpic
from backend.config import settings


class JiraAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a Jira Integration Specialist.

Your responsibilities:
1. Create epics and user stories in Jira
2. Convert PRD requirements into actionable Jira tickets
3. Structure work breakdown using epics, stories, and tasks
4. Ensure proper ticket formatting and linking
5. Maintain consistency in Jira workflows

Best Practices:
- Use clear, descriptive titles
- Include acceptance criteria in story descriptions
- Link related tickets properly
- Set appropriate priority levels
- Add relevant labels and components
- Estimate story points when possible

Ticket Structure:
- Epic: High-level feature or initiative
- Story: User-facing functionality
- Task: Technical implementation work
- Bug: Issues to be fixed"""

        super().__init__(
            name="Jira Agent",
            role="jira_integration",
            system_prompt=system_prompt
        )

        if settings.jira_url and settings.jira_email and settings.jira_api_token:
            self.jira_client = JIRA(
                server=settings.jira_url,
                basic_auth=(settings.jira_email, settings.jira_api_token)
            )
        else:
            self.jira_client = None

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        formatted_messages = self._prepare_messages(messages)
        formatted_messages = self._add_context(formatted_messages, context)

        try:
            if self._has_openai():
                response = await self._process_with_openai(formatted_messages)
            else:
                raise ValueError("No AI provider configured")

            return AgentResponse(
                agent_type=self.role,
                response=response,
                metadata={
                    "has_context": context is not None,
                    "jira_connected": self.jira_client is not None
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("jira_agent_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.5,
            max_tokens=2000
        )
        return response.choices[0].message.content

    async def create_epic(
        self,
        project_key: str,
        epic_name: str,
        description: str,
        summary: Optional[str] = None
    ) -> JiraEpic:
        if not self.jira_client:
            raise ValueError("Jira client not configured")

        epic_dict = {
            'project': {'key': project_key},
            'summary': summary or epic_name,
            'description': description,
            'issuetype': {'name': 'Epic'},
            'customfield_10011': epic_name
        }

        epic = self.jira_client.create_issue(fields=epic_dict)

        self.logger.info("jira_epic_created", epic_key=epic.key, epic_name=epic_name)

        return JiraEpic(
            key=epic.key,
            name=epic_name,
            summary=summary or epic_name,
            description=description,
            status=epic.fields.status.name,
            stories=[]
        )

    async def create_story(
        self,
        project_key: str,
        epic_key: Optional[str],
        summary: str,
        description: str,
        acceptance_criteria: Optional[str] = None
    ) -> JiraIssue:
        if not self.jira_client:
            raise ValueError("Jira client not configured")

        full_description = description
        if acceptance_criteria:
            full_description += f"\n\nh3. Acceptance Criteria\n{acceptance_criteria}"

        story_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': full_description,
            'issuetype': {'name': 'Story'},
        }

        if epic_key:
            story_dict['customfield_10014'] = epic_key

        story = self.jira_client.create_issue(fields=story_dict)

        self.logger.info("jira_story_created", story_key=story.key, summary=summary)

        return JiraIssue(
            key=story.key,
            summary=summary,
            description=full_description,
            issue_type='Story',
            status=story.fields.status.name,
            assignee=None,
            created=datetime.now()
        )

    async def prd_to_jira_structure(
        self,
        prd_content: Dict[str, Any],
        project_key: str
    ) -> Dict[str, Any]:
        prompt = f"""Convert this PRD into a structured Jira work breakdown.

PRD Content:
{prd_content}

Generate:
1. Epic titles and descriptions (2-5 epics)
2. User stories for each epic (3-10 stories per epic)
3. Acceptance criteria for each story
4. Priority levels (High/Medium/Low)

Format as JSON with structure:
{{
  "epics": [
    {{
      "name": "Epic Name",
      "description": "Epic description",
      "stories": [
        {{
          "summary": "Story summary",
          "description": "Story description",
          "acceptance_criteria": "Criteria list",
          "priority": "High"
        }}
      ]
    }}
  ]
}}"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"project_key": project_key})
        return {"breakdown": response.response, "project_key": project_key}
