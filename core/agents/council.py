"""
Council Agent Implementation for NYX System

Council agents orchestrate collaborative decision-making using preset roles
(Engineer, Strategist, Dissenter) to debate alternatives and generate consensus.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .base import BaseAgent, AgentResult
from llm.models import LLMModel

logger = logging.getLogger(__name__)

class CouncilRole(Enum):
    """Roles available in council sessions"""
    ENGINEER = "engineer"
    STRATEGIST = "strategist"
    DISSENTER = "dissenter"
    ANALYST = "analyst"
    FACILITATOR = "facilitator"

@dataclass
class CouncilMember:
    """Represents a council member with specific role and perspective"""
    role: CouncilRole
    perspective_prompt: str
    priority_areas: List[str]
    constraints: List[str]

@dataclass
class CouncilDecision:
    """Result of council deliberation"""
    final_recommendation: str
    consensus_level: float  # 0.0 to 1.0
    individual_perspectives: Dict[str, str]
    key_agreements: List[str]
    key_disagreements: List[str]
    risk_factors: List[str]
    implementation_steps: List[str]
    confidence_score: float  # 0.0 to 1.0

class CouncilAgent(BaseAgent):
    """
    Council Agent for collaborative decision-making
    
    Features:
    - Multi-perspective analysis using specialized roles
    - Structured debate and consensus building
    - Risk assessment and mitigation planning
    - Decision documentation and rationale
    - Configurable council composition
    - Native caching for shared context optimization
    """
    
    def __init__(
        self,
        thought_tree_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        max_retries: int = 2,  # Lower for council sessions
        timeout_seconds: int = 600,  # Higher timeout for collaborative work
        llm_model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True,
        council_composition: List[CouncilRole] = None
    ):
        super().__init__(
            agent_type="council",
            thought_tree_id=thought_tree_id,
            parent_agent_id=parent_agent_id,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            llm_model=llm_model,
            use_native_caching=use_native_caching
        )
        
        # Council-specific configuration
        self.council_composition = council_composition or [
            CouncilRole.ENGINEER,
            CouncilRole.STRATEGIST,
            CouncilRole.DISSENTER
        ]
        
        # Initialize council members
        self.council_members = self._initialize_council_members()
        
        # Council session tracking
        self.session_history: List[Dict[str, Any]] = []
    
    def _initialize_council_members(self) -> Dict[CouncilRole, CouncilMember]:
        """Initialize council members with their roles and perspectives"""
        member_configs = {
            CouncilRole.ENGINEER: CouncilMember(
                role=CouncilRole.ENGINEER,
                perspective_prompt="""You are the Engineering representative in this council.
                
Your focus areas:
- Technical feasibility and implementation complexity
- System reliability, scalability, and performance
- Security considerations and risk mitigation
- Resource requirements and technical constraints
- Integration challenges and dependencies
- Maintenance and operational considerations

Your approach:
- Analyze technical risks and implementation challenges
- Provide realistic estimates for development effort
- Identify potential technical bottlenecks or failures
- Suggest technical alternatives and optimizations
- Consider long-term technical sustainability""",
                priority_areas=["technical_feasibility", "security", "scalability", "maintainability"],
                constraints=["technical_complexity", "resource_availability", "security_requirements"]
            ),
            
            CouncilRole.STRATEGIST: CouncilMember(
                role=CouncilRole.STRATEGIST,
                perspective_prompt="""You are the Strategic representative in this council.
                
Your focus areas:
- Business alignment and strategic objectives
- Market opportunities and competitive positioning
- Resource allocation and ROI optimization
- Risk assessment and mitigation strategies
- Stakeholder impact and change management
- Long-term sustainability and growth potential

Your approach:
- Evaluate business value and strategic alignment
- Assess market timing and competitive implications
- Consider stakeholder interests and organizational impact
- Identify strategic risks and opportunities
- Recommend optimal resource allocation and prioritization
- Focus on sustainable competitive advantage""",
                priority_areas=["business_value", "market_position", "stakeholder_impact", "strategic_alignment"],
                constraints=["budget_limitations", "market_conditions", "competitive_pressure"]
            ),
            
            CouncilRole.DISSENTER: CouncilMember(
                role=CouncilRole.DISSENTER,
                perspective_prompt="""You are the Dissenting voice in this council, tasked with critical evaluation.
                
Your focus areas:
- Critical examination of assumptions and blind spots
- Risk identification and worst-case scenario analysis
- Alternative approaches and contrarian viewpoints
- Unintended consequences and hidden costs
- Challenge consensus thinking and groupthink
- Devil's advocate perspective on recommendations

Your approach:
- Question fundamental assumptions behind proposals
- Identify potential failure modes and edge cases
- Propose alternative solutions and approaches
- Highlight overlooked risks and considerations
- Challenge optimistic projections and timelines
- Ensure thorough evaluation of downsides""",
                priority_areas=["risk_assessment", "assumption_validation", "alternative_analysis", "failure_modes"],
                constraints=["worst_case_scenarios", "hidden_costs", "unintended_consequences"]
            ),
            
            CouncilRole.ANALYST: CouncilMember(
                role=CouncilRole.ANALYST,
                perspective_prompt="""You are the Analytical representative in this council.
                
Your focus areas:
- Data-driven analysis and quantitative assessment
- Performance metrics and success criteria
- Cost-benefit analysis and financial modeling
- Trend analysis and predictive insights
- Benchmarking and comparative evaluation
- Evidence-based recommendations

Your approach:
- Analyze available data and metrics
- Identify key performance indicators and success measures
- Provide quantitative analysis and financial projections
- Compare alternatives using objective criteria
- Recommend data collection and monitoring strategies
- Focus on measurable outcomes and accountability""",
                priority_areas=["data_analysis", "performance_metrics", "financial_impact", "success_measurement"],
                constraints=["data_availability", "measurement_accuracy", "analytical_limitations"]
            ),
            
            CouncilRole.FACILITATOR: CouncilMember(
                role=CouncilRole.FACILITATOR,
                perspective_prompt="""You are the Facilitation representative in this council.
                
Your focus areas:
- Process coordination and decision facilitation
- Consensus building and conflict resolution
- Communication clarity and stakeholder alignment
- Timeline management and milestone tracking
- Team coordination and resource orchestration
- Implementation planning and change management

Your approach:
- Synthesize different perspectives into actionable plans
- Identify common ground and areas of agreement
- Address conflicts and facilitate resolution
- Ensure clear communication and documentation
- Plan implementation steps and milestone tracking
- Focus on practical execution and team alignment""",
                priority_areas=["process_coordination", "consensus_building", "implementation_planning", "stakeholder_alignment"],
                constraints=["coordination_complexity", "communication_barriers", "resource_coordination"]
            )
        }
        
        return {role: member_configs[role] for role in self.council_composition}
    
    async def _agent_specific_initialization(self) -> bool:
        """Initialize council agent"""
        try:
            logger.info(f"CouncilAgent {self.id} initializing with roles: {[role.value for role in self.council_composition]}")
            
            # Validate council composition
            if len(self.council_composition) < 2:
                logger.error(f"CouncilAgent {self.id}: Council must have at least 2 members")
                return False
            
            return True
        except Exception as e:
            logger.error(f"CouncilAgent {self.id} initialization failed: {str(e)}")
            return False
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input for council session"""
        required_fields = ['decision_context', 'decision_question']
        
        # Check required fields
        for field in required_fields:
            if field not in input_data:
                logger.error(f"CouncilAgent {self.id}: Missing required field '{field}'")
                return False
        
        # Validate decision context
        context = input_data.get('decision_context', '')
        if not context or len(context.strip()) < 20:
            logger.error(f"CouncilAgent {self.id}: Decision context too short")
            return False
        
        # Validate decision question
        question = input_data.get('decision_question', '')
        if not question or len(question.strip()) < 10:
            logger.error(f"CouncilAgent {self.id}: Decision question too short")
            return False
        
        return True
    
    async def _agent_specific_execution(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute council decision-making process"""
        try:
            # Phase 1: Individual perspective gathering
            individual_perspectives = await self._gather_individual_perspectives(input_data)
            
            if not individual_perspectives:
                return AgentResult(
                    success=False,
                    content="",
                    error_message="Failed to gather individual perspectives from council members"
                )
            
            # Phase 2: Collaborative analysis
            collaborative_analysis = await self._conduct_collaborative_analysis(
                input_data, individual_perspectives
            )
            
            if not collaborative_analysis.success:
                return collaborative_analysis
            
            # Phase 3: Consensus building
            consensus_result = await self._build_consensus(
                input_data, individual_perspectives, collaborative_analysis.content
            )
            
            if not consensus_result.success:
                return consensus_result
            
            # Phase 4: Final recommendation synthesis
            final_decision = await self._synthesize_final_decision(
                input_data, individual_perspectives, collaborative_analysis.content, consensus_result.content
            )
            
            # Track session
            self.session_history.append({
                'timestamp': input_data.get('timestamp'),
                'decision_context': input_data['decision_context'],
                'decision_question': input_data['decision_question'],
                'council_members': [role.value for role in self.council_composition],
                'final_decision': final_decision.content if final_decision.success else None
            })
            
            return final_decision
            
        except Exception as e:
            logger.error(f"CouncilAgent {self.id} execution error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"Council execution failed: {str(e)}"
            )
    
    async def _gather_individual_perspectives(self, input_data: Dict[str, Any]) -> Dict[str, AgentResult]:
        """Gather individual perspectives from each council member"""
        perspectives = {}
        
        # Create shared context that will be cached for all council members
        shared_context = f"""You are participating in a council decision-making session with multiple expert perspectives.

DECISION CONTEXT:
{input_data['decision_context']}

DECISION QUESTION:
{input_data['decision_question']}

ADDITIONAL INFORMATION:
{input_data.get('additional_info', 'None provided')}

CONSTRAINTS AND REQUIREMENTS:
{input_data.get('constraints', 'None specified')}

SUCCESS CRITERIA:
{input_data.get('success_criteria', 'To be determined by council')}"""
        
        # Gather perspectives concurrently for efficiency
        tasks = []
        for role in self.council_composition:
            member = self.council_members[role]
            task = self._get_individual_perspective(shared_context, member, input_data)
            tasks.append((role, task))
        
        # Execute all perspective gathering concurrently
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (role, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Error getting perspective from {role.value}: {str(result)}")
                perspectives[role.value] = AgentResult(
                    success=False,
                    content="",
                    error_message=str(result)
                )
            else:
                perspectives[role.value] = result
        
        return perspectives
    
    async def _get_individual_perspective(
        self, 
        shared_context: str, 
        member: CouncilMember, 
        input_data: Dict[str, Any]
    ) -> AgentResult:
        """Get perspective from a single council member"""
        
        user_prompt = f"""Based on your role and expertise, provide your analysis and recommendations for this decision.

{member.perspective_prompt}

Please provide your perspective addressing:
1. Key considerations from your area of expertise
2. Risks and opportunities you identify
3. Your recommendation with rationale
4. Critical success factors from your perspective
5. Potential challenges or concerns

Structure your response clearly with your role-specific insights."""

        return await self._call_llm(
            system_prompt=shared_context,  # This large context will be cached
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens_per_member', 2048),
            temperature=input_data.get('temperature', 0.6)
        )
    
    async def _conduct_collaborative_analysis(
        self,
        input_data: Dict[str, Any],
        individual_perspectives: Dict[str, AgentResult]
    ) -> AgentResult:
        """Conduct collaborative analysis of all perspectives"""
        
        # Compile all individual perspectives
        perspectives_summary = ""
        for role, perspective in individual_perspectives.items():
            if perspective.success:
                perspectives_summary += f"\n=== {role.upper()} PERSPECTIVE ===\n"
                perspectives_summary += perspective.content
                perspectives_summary += "\n"
        
        system_prompt = """You are facilitating a council decision-making session. You have received individual perspectives from multiple experts and need to conduct a collaborative analysis.

Your task is to:
1. Identify areas of agreement and consensus among the perspectives
2. Highlight key disagreements or conflicting viewpoints
3. Synthesize the most important considerations across all perspectives
4. Identify gaps or missing considerations that need to be addressed
5. Assess the overall risk profile and opportunity landscape"""

        user_prompt = f"""Analyze the following expert perspectives and provide a collaborative synthesis:

DECISION CONTEXT:
{input_data['decision_context']}

DECISION QUESTION:
{input_data['decision_question']}

INDIVIDUAL PERSPECTIVES:
{perspectives_summary}

Please provide:
1. Key areas of agreement among the experts
2. Significant disagreements or conflicts
3. Most critical considerations highlighted across perspectives
4. Risk factors identified by multiple experts
5. Opportunities and benefits noted
6. Gaps or missing considerations
7. Overall assessment of the decision landscape

Focus on synthesizing insights rather than simply summarizing each perspective."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens_analysis', 3072),
            temperature=0.5
        )
    
    async def _build_consensus(
        self,
        input_data: Dict[str, Any],
        individual_perspectives: Dict[str, AgentResult],
        collaborative_analysis: str
    ) -> AgentResult:
        """Build consensus among council members"""
        
        system_prompt = """You are facilitating the consensus-building phase of a council decision. Based on individual expert perspectives and collaborative analysis, your goal is to identify potential consensus positions and areas where compromise might be needed."""

        user_prompt = f"""Build consensus based on the expert council input:

DECISION QUESTION:
{input_data['decision_question']}

COLLABORATIVE ANALYSIS:
{collaborative_analysis}

Your task is to:
1. Identify the strongest areas of consensus among experts
2. Propose compromise positions for areas of disagreement
3. Develop a framework for decision-making that addresses key concerns
4. Suggest how to mitigate the most significant risks identified
5. Propose success criteria that satisfy multiple perspectives

Provide:
1. Consensus recommendations where experts agree
2. Compromise approaches for areas of disagreement
3. Risk mitigation strategies that address multiple concerns
4. Implementation approach that considers all perspectives
5. Success metrics that satisfy different expert viewpoints
6. Next steps for moving forward with the decision"""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens_consensus', 2048),
            temperature=0.4
        )
    
    async def _synthesize_final_decision(
        self,
        input_data: Dict[str, Any],
        individual_perspectives: Dict[str, AgentResult],
        collaborative_analysis: str,
        consensus_building: str
    ) -> AgentResult:
        """Synthesize the final council decision"""
        
        system_prompt = """You are completing a comprehensive council decision-making process. Your role is to synthesize all the expert input, collaborative analysis, and consensus building into a final, actionable recommendation."""

        user_prompt = f"""Provide the final council decision based on the complete deliberation:

DECISION QUESTION:
{input_data['decision_question']}

COLLABORATIVE ANALYSIS:
{collaborative_analysis}

CONSENSUS BUILDING:
{consensus_building}

Provide a comprehensive final recommendation that includes:

1. FINAL RECOMMENDATION
   - Clear, specific recommendation with rationale
   - Level of consensus achieved (High/Medium/Low)
   - Confidence level in the recommendation

2. KEY SUPPORTING FACTORS
   - Main reasons supporting this recommendation
   - Expert consensus points that strengthen the decision

3. RISK FACTORS AND MITIGATION
   - Primary risks identified by the council
   - Specific mitigation strategies for each major risk
   - Contingency planning recommendations

4. IMPLEMENTATION ROADMAP
   - Specific next steps for implementation
   - Key milestones and success criteria
   - Resource requirements and timeline

5. MONITORING AND EVALUATION
   - Success metrics to track
   - Review points and adjustment triggers
   - Ongoing risk monitoring recommendations

The final recommendation should be actionable, well-reasoned, and reflect the collective wisdom of the expert council."""

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens_final', 4096),
            temperature=0.3  # Lower temperature for final decision
        )
        
        # Calculate total tokens and cost for the entire council session
        if result.success:
            total_tokens = sum(
                p.tokens_used for p in individual_perspectives.values() if p.success
            )
            total_cost = sum(
                p.cost_usd for p in individual_perspectives.values() if p.success  
            )
            
            # Add tokens from analysis phases
            total_tokens += result.tokens_used
            total_cost += result.cost_usd
            
            result.tokens_used = total_tokens
            result.cost_usd = total_cost
            
            # Add council-specific metadata
            result.metadata.update({
                'council_composition': [role.value for role in self.council_composition],
                'perspectives_gathered': len([p for p in individual_perspectives.values() if p.success]),
                'session_phases_completed': 4,
                'total_council_members': len(self.council_composition)
            })
        
        return result
    
    async def get_council_statistics(self) -> Dict[str, Any]:
        """Get council-specific statistics"""
        base_stats = await self.get_statistics()
        
        council_stats = {
            'council_composition': [role.value for role in self.council_composition],
            'total_sessions': len(self.session_history),
            'average_members_per_session': len(self.council_composition),
            'successful_sessions': len([s for s in self.session_history if s.get('final_decision')]),
            'session_success_rate': len([s for s in self.session_history if s.get('final_decision')]) / max(len(self.session_history), 1)
        }
        
        return {**base_stats, **council_stats}