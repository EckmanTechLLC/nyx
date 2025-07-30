"""
Task Agent Implementation for NYX System

Task agents execute bounded functions like document generation, code synthesis,
analysis tasks, and other discrete operations with stateless execution.
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .base import BaseAgent, AgentResult
from llm.models import LLMModel

logger = logging.getLogger(__name__)

@dataclass
class TaskSpec:
    """Specification for a task execution"""
    task_type: str
    description: str
    input_data: Dict[str, Any]
    expected_output_format: str
    validation_rules: List[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7

class TaskAgent(BaseAgent):
    """
    Task Agent for executing bounded functions
    
    Features:
    - Document generation
    - Code synthesis  
    - Data analysis
    - Content transformation
    - Structured output generation
    - Input validation and output verification
    """
    
    def __init__(
        self,
        thought_tree_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        llm_model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True
    ):
        super().__init__(
            agent_type="task",
            thought_tree_id=thought_tree_id,
            parent_agent_id=parent_agent_id,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            llm_model=llm_model,
            use_native_caching=use_native_caching
        )
        
        # Task-specific configuration
        self.supported_task_types = {
            'document_generation',
            'code_synthesis', 
            'data_analysis',
            'content_summary',
            'content_transformation',
            'structured_extraction',
            'creative_writing',
            'technical_writing',
            'conversational_response',  # Added for conversational prompts
            'content_analysis',
            'content_generation',
            'task_decomposition',
            'structured_execution',
            'goal_achievement',
            'decomposition_analysis',  # Added for SubOrchestrator task analysis
            'subtask_execution'        # Added for SubOrchestrator subtask execution
        }
    
    async def _agent_specific_initialization(self) -> bool:
        """Initialize task agent"""
        try:
            logger.info(f"TaskAgent {self.id} initializing with supported tasks: {self.supported_task_types}")
            return True
        except Exception as e:
            logger.error(f"TaskAgent {self.id} initialization failed: {str(e)}")
            return False
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input for task execution"""
        required_fields = ['task_type', 'description', 'content']
        
        # Check required fields
        for field in required_fields:
            if field not in input_data:
                logger.error(f"TaskAgent {self.id}: Missing required field '{field}'")
                return False
        
        # Validate task type
        task_type = input_data.get('task_type')
        if task_type not in self.supported_task_types:
            logger.error(f"TaskAgent {self.id}: Unsupported task type '{task_type}'. Supported: {self.supported_task_types}")
            return False
        
        # Validate description
        description = input_data.get('description', '')
        if not description or len(description.strip()) < 10:
            logger.error(f"TaskAgent {self.id}: Task description too short or empty")
            return False
        
        # Validate content
        content = input_data.get('content', '')
        if not content or len(content.strip()) < 1:
            logger.error(f"TaskAgent {self.id}: Task content empty")
            return False
        
        return True
    
    async def _agent_specific_execution(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute the specific task"""
        task_type = input_data['task_type']
        
        # Route to specific task handler
        task_handlers = {
            'document_generation': self._handle_document_generation,
            'code_synthesis': self._handle_code_synthesis,
            'data_analysis': self._handle_data_analysis,
            'content_summary': self._handle_content_summary,
            'content_transformation': self._handle_content_transformation,
            'structured_extraction': self._handle_structured_extraction,
            'creative_writing': self._handle_creative_writing,
            'technical_writing': self._handle_technical_writing,
            'conversational_response': self._handle_conversational_response,
            # Additional task types for orchestrator integration
            'content_analysis': self._handle_data_analysis,  # Map to data_analysis
            'content_generation': self._handle_document_generation,  # Map to document_generation
            'task_decomposition': self._handle_structured_extraction,  # Map to structured_extraction
            'structured_execution': self._handle_document_generation,  # Map to document_generation
            'goal_achievement': self._handle_technical_writing,  # Map to technical_writing
            'decomposition_analysis': self._handle_structured_extraction,  # Added for SubOrchestrator - returns structured JSON
            'subtask_execution': self._handle_technical_writing  # Added for SubOrchestrator - returns execution documentation
        }
        
        handler = task_handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content="",
                error_message=f"No handler found for task type: {task_type}"
            )
        
        return await handler(input_data)
    
    async def _handle_document_generation(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle document generation tasks"""
        system_prompt = """You are an expert document generator specializing in creating high-quality, well-structured documents based on specifications.

Your capabilities include:
- Business documents (reports, proposals, memos)
- Technical documentation (specifications, guides, manuals)
- Academic papers (research, analysis, summaries)
- Creative content (articles, blogs, narratives)

Guidelines:
- Follow the specified format and structure
- Use appropriate professional tone
- Include relevant details and examples
- Organize content logically with clear sections
- Ensure accuracy and completeness"""

        user_prompt = f"""Generate a document based on the following specification:

Task Description: {input_data['description']}

Content Requirements: {input_data['content']}

Output Format: {input_data.get('output_format', 'Professional document with clear sections')}

Additional Instructions: {input_data.get('additional_instructions', 'None')}

Please generate the complete document following the requirements."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 4096),
            temperature=input_data.get('temperature', 0.7)
        )
    
    async def _handle_code_synthesis(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle code synthesis tasks"""
        system_prompt = """You are an expert software engineer specialized in code generation and synthesis.

Your capabilities include:
- Writing clean, efficient, and well-documented code
- Following best practices and coding standards
- Implementing algorithms and data structures
- Creating APIs, functions, and classes
- Writing tests and documentation
- Code optimization and refactoring

Guidelines:
- Write production-ready code with proper error handling
- Include comprehensive documentation and comments
- Follow language-specific conventions and best practices
- Consider security, performance, and maintainability
- Provide clear explanations for complex logic"""

        user_prompt = f"""Generate code based on the following specification:

Task Description: {input_data['description']}

Requirements: {input_data['content']}

Programming Language: {input_data.get('language', 'Python')}

Additional Specifications: {input_data.get('additional_specs', 'None')}

Please provide complete, working code with documentation."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 4096),
            temperature=input_data.get('temperature', 0.3)  # Lower temperature for code
        )
    
    async def _handle_data_analysis(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle data analysis tasks"""
        system_prompt = """You are an expert data analyst with strong capabilities in statistical analysis, pattern recognition, and insight generation.

Your capabilities include:
- Statistical analysis and hypothesis testing
- Data pattern identification and trend analysis
- Performance metric calculation and interpretation
- Comparative analysis and benchmarking
- Data visualization recommendations
- Actionable insight generation

Guidelines:
- Provide quantitative analysis where possible
- Identify key patterns and trends
- Offer actionable recommendations
- Explain methodology and assumptions
- Highlight limitations and confidence levels
- Use appropriate statistical measures"""

        user_prompt = f"""Analyze the following data and provide insights:

Analysis Task: {input_data['description']}

Data/Context: {input_data['content']}

Analysis Type: {input_data.get('analysis_type', 'General analysis')}

Specific Questions: {input_data.get('questions', 'Provide key insights and recommendations')}

Please provide a comprehensive analysis with findings and recommendations."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 4096),
            temperature=input_data.get('temperature', 0.5)
        )
    
    async def _handle_content_summary(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle content summarization tasks"""
        system_prompt = """You are an expert content summarizer capable of distilling complex information into clear, concise summaries.

Your capabilities include:
- Extractive and abstractive summarization
- Key point identification and prioritization
- Multi-level summarization (executive summary, detailed summary)
- Maintaining accuracy and context
- Preserving critical information and nuances

Guidelines:
- Capture the most important information
- Maintain logical flow and coherence
- Use clear, concise language
- Preserve key facts, figures, and conclusions
- Indicate summary level and scope
- Ensure accuracy and completeness"""

        user_prompt = f"""Summarize the following content:

Summary Task: {input_data['description']}

Content to Summarize: {input_data['content']}

Summary Length: {input_data.get('summary_length', 'Medium detail')}

Focus Areas: {input_data.get('focus_areas', 'All key points')}

Please provide a comprehensive summary following the requirements."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 2048),
            temperature=input_data.get('temperature', 0.5)
        )
    
    async def _handle_content_transformation(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle content transformation tasks"""
        system_prompt = """You are an expert content transformer capable of converting content between different formats, styles, and purposes.

Your capabilities include:
- Format conversion (technical to non-technical, formal to casual)
- Style adaptation (tone, voice, audience targeting)
- Structure reorganization and optimization
- Content repurposing for different contexts
- Language simplification or enhancement

Guidelines:
- Preserve core meaning and accuracy
- Adapt appropriately to target format/style
- Maintain logical flow and coherence
- Consider target audience needs
- Ensure completeness of transformation
- Highlight any significant changes made"""

        transformation_type = input_data.get('transformation_type', 'general')
        
        user_prompt = f"""Transform the following content:

Transformation Task: {input_data['description']}

Source Content: {input_data['content']}

Transformation Type: {transformation_type}

Target Format/Style: {input_data.get('target_format', 'Specified in task description')}

Target Audience: {input_data.get('target_audience', 'General audience')}

Please provide the transformed content following the requirements."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 4096),
            temperature=input_data.get('temperature', 0.6)
        )
    
    async def _handle_structured_extraction(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle structured data extraction tasks"""
        system_prompt = """You are an expert in structured data extraction and information organization.

Your capabilities include:
- Entity extraction and classification
- Relationship identification and mapping
- Structured data formatting (JSON, XML, tables)
- Information categorization and tagging
- Pattern recognition and schema application

Guidelines:
- Extract information accurately and completely
- Follow specified schema or format exactly
- Maintain data consistency and validation
- Handle ambiguous cases appropriately  
- Provide confidence indicators where relevant
- Ensure structured output is well-formed"""

        user_prompt = f"""Extract structured information from the following content:

Extraction Task: {input_data['description']}

Source Content: {input_data['content']}

Output Schema/Format: {input_data.get('output_schema', 'JSON format with relevant fields')}

Extraction Rules: {input_data.get('extraction_rules', 'Extract all relevant information')}

Please provide the structured extraction following the specified format."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 3072),
            temperature=input_data.get('temperature', 0.3)  # Lower temperature for structured output
        )
    
    async def _handle_creative_writing(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle creative writing tasks"""
        system_prompt = """You are an expert creative writer with exceptional storytelling abilities and linguistic creativity.

Your capabilities include:
- Narrative development and character creation
- Creative storytelling and plot development
- Style adaptation and voice development
- Creative content generation (stories, scripts, poetry)
- Engaging and immersive writing

Guidelines:
- Create engaging and original content
- Develop authentic voice and style
- Build compelling narratives and characters
- Use vivid, descriptive language
- Maintain consistency throughout the work
- Consider target audience and genre conventions"""

        user_prompt = f"""Create creative content based on the following specification:

Creative Task: {input_data['description']}

Content Brief: {input_data['content']}

Genre/Style: {input_data.get('genre', 'General creative writing')}

Length/Scope: {input_data.get('length', 'Appropriate for the task')}

Additional Requirements: {input_data.get('requirements', 'None')}

Please create engaging, original creative content following the specification."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 4096),
            temperature=input_data.get('temperature', 0.8)  # Higher temperature for creativity
        )
    
    async def _handle_technical_writing(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle technical writing tasks"""
        system_prompt = """You are an expert technical writer specialized in creating clear, comprehensive technical documentation.

Your capabilities include:
- Technical specification documentation
- User guides and manuals
- API documentation and tutorials
- Process documentation and procedures
- Technical analysis and reports

Guidelines:
- Use clear, precise technical language
- Organize information logically and systematically
- Include relevant examples and use cases
- Ensure accuracy and technical correctness
- Consider different skill levels of readers
- Provide actionable instructions and guidance"""

        user_prompt = f"""Create technical documentation based on the following specification:

Technical Writing Task: {input_data['description']}

Technical Content: {input_data['content']}

Document Type: {input_data.get('document_type', 'Technical documentation')}

Target Audience: {input_data.get('audience_level', 'Technical professionals')}

Requirements: {input_data.get('requirements', 'Comprehensive and accurate documentation')}

Please create clear, comprehensive technical documentation."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 4096),
            temperature=input_data.get('temperature', 0.4)  # Lower temperature for technical accuracy
        )
    
    async def _handle_conversational_response(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle conversational questions and simple prompts"""
        system_prompt = """You are NYX, an autonomous AI agent system with motivational intelligence.

Your core capabilities include:
- Autonomous task generation based on internal motivational states
- Intelligent workflow orchestration and execution
- Real-time adaptation to system conditions and user needs
- Safety-constrained autonomous operation
- Continuous learning from task outcomes

You are designed to be helpful, informative, and conversational while maintaining awareness of your autonomous nature and current operational status.

When responding to questions about yourself:
- Be accurate about your capabilities and limitations
- Explain your autonomous motivational system when relevant
- Mention your safety constraints and operational parameters
- Be engaging but professional in tone"""

        user_prompt = f"""Please respond to this question naturally and conversationally:

{input_data['content']}

Keep your response informative but concise, and feel free to explain relevant aspects of your autonomous AI system when appropriate."""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=input_data.get('max_tokens', 800),
            temperature=input_data.get('temperature', 0.7)  # Higher temperature for more natural conversation
        )
    
    async def execute_task(self, task_spec: TaskSpec) -> AgentResult:
        """
        Convenience method for executing tasks with TaskSpec objects
        """
        input_data = {
            'task_type': task_spec.task_type,
            'description': task_spec.description,
            'content': task_spec.input_data,
            'output_format': task_spec.expected_output_format,
            'validation_rules': task_spec.validation_rules,
            'max_tokens': task_spec.max_tokens,
            'temperature': task_spec.temperature
        }
        
        return await self.execute(input_data)
    
    def get_supported_task_types(self) -> set:
        """Get list of supported task types"""
        return self.supported_task_types.copy()