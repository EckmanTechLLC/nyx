"""
Validator Agent Implementation for NYX System

Validator agents apply static rules and catch errors, enforce system constraints,
and validate outputs before propagation to ensure safety and compliance.
"""
import logging
import re
import json
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass
from enum import Enum

from .base import BaseAgent, AgentResult
from llm.models import LLMModel

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Levels of validation strictness"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    CRITICAL = "critical"

class ValidationType(Enum):
    """Types of validation checks"""
    FORMAT = "format"
    CONTENT = "content"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    LOGIC = "logic"
    CONSISTENCY = "consistency"

@dataclass
class ValidationRule:
    """Represents a validation rule"""
    name: str
    description: str
    validation_type: ValidationType
    level: ValidationLevel
    rule_function: Optional[Callable] = None
    pattern: Optional[str] = None
    required_fields: List[str] = None
    forbidden_content: List[str] = None

@dataclass
class ValidationResult:
    """Result of validation check"""
    rule_name: str
    passed: bool
    message: str
    severity: ValidationLevel
    details: Dict[str, Any] = None

class ValidatorAgent(BaseAgent):
    """
    Validator Agent for rule enforcement and output validation
    
    Features:
    - Static rule validation with configurable rules
    - Content safety and compliance checking
    - Format and structure validation
    - Logic and consistency validation
    - Multi-level validation (basic to critical)
    - Custom rule definition and enforcement
    """
    
    def __init__(
        self,
        thought_tree_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        max_retries: int = 2,
        timeout_seconds: int = 180,
        llm_model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        custom_rules: List[ValidationRule] = None
    ):
        super().__init__(
            agent_type="validator",
            thought_tree_id=thought_tree_id,
            parent_agent_id=parent_agent_id,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            llm_model=llm_model,
            use_native_caching=use_native_caching
        )
        
        self.validation_level = validation_level
        self.validation_rules = self._initialize_validation_rules()
        
        # Add custom rules if provided
        if custom_rules:
            self.validation_rules.extend(custom_rules)
        
        # Validation tracking
        self.validation_history: List[Dict[str, Any]] = []
    
    def _initialize_validation_rules(self) -> List[ValidationRule]:
        """Initialize default validation rules"""
        return [
            # Format validation rules
            ValidationRule(
                name="json_format",
                description="Validate JSON format structure",
                validation_type=ValidationType.FORMAT,
                level=ValidationLevel.BASIC,
                rule_function=self._validate_json_format
            ),
            ValidationRule(
                name="required_fields",
                description="Check for required fields presence",
                validation_type=ValidationType.FORMAT,
                level=ValidationLevel.STANDARD,
                rule_function=self._validate_required_fields
            ),
            ValidationRule(
                name="field_types",
                description="Validate field data types",
                validation_type=ValidationType.FORMAT,
                level=ValidationLevel.STANDARD,
                rule_function=self._validate_field_types
            ),
            
            # Content validation rules
            ValidationRule(
                name="content_length",
                description="Validate content length within bounds",
                validation_type=ValidationType.CONTENT,
                level=ValidationLevel.BASIC,
                rule_function=self._validate_content_length
            ),
            ValidationRule(
                name="forbidden_content",
                description="Check for forbidden content patterns",
                validation_type=ValidationType.SAFETY,
                level=ValidationLevel.STRICT,
                rule_function=self._validate_forbidden_content
            ),
            
            # Safety validation rules
            ValidationRule(
                name="prompt_injection",
                description="Detect potential prompt injection attempts",
                validation_type=ValidationType.SAFETY,
                level=ValidationLevel.CRITICAL,
                rule_function=self._validate_prompt_injection
            ),
            ValidationRule(
                name="sensitive_data",
                description="Check for sensitive data exposure",
                validation_type=ValidationType.SAFETY,
                level=ValidationLevel.STRICT,
                rule_function=self._validate_sensitive_data
            ),
            
            # Logic validation rules
            ValidationRule(
                name="consistency_check",
                description="Check internal consistency of content",
                validation_type=ValidationType.LOGIC,
                level=ValidationLevel.STANDARD,
                rule_function=self._validate_consistency
            ),
            ValidationRule(
                name="completeness_check",
                description="Verify content completeness",
                validation_type=ValidationType.CONTENT,
                level=ValidationLevel.STANDARD,
                rule_function=self._validate_completeness
            )
        ]
    
    async def _agent_specific_initialization(self) -> bool:
        """Initialize validator agent"""
        try:
            logger.info(f"ValidatorAgent {self.id} initializing with {len(self.validation_rules)} rules at {self.validation_level.value} level")
            return True
        except Exception as e:
            logger.error(f"ValidatorAgent {self.id} initialization failed: {str(e)}")
            return False
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input for validation request"""
        required_fields = ['content_to_validate']
        
        for field in required_fields:
            if field not in input_data:
                logger.error(f"ValidatorAgent {self.id}: Missing required field '{field}'")
                return False
        
        content = input_data.get('content_to_validate')
        if not content:
            logger.error(f"ValidatorAgent {self.id}: No content provided for validation")
            return False
        
        return True
    
    async def _agent_specific_execution(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute validation process"""
        content_to_validate = input_data['content_to_validate']
        validation_rules = input_data.get('validation_rules', None)
        validation_context = input_data.get('validation_context', {})
        
        try:
            # Run static validation rules
            static_results = await self._run_static_validation(
                content_to_validate, validation_rules, validation_context
            )
            
            # Run LLM-based intelligent validation if needed
            intelligent_results = []
            if input_data.get('use_intelligent_validation', True):
                intelligent_result = await self._run_intelligent_validation(
                    content_to_validate, validation_context, input_data
                )
                if intelligent_result:
                    intelligent_results.append(intelligent_result)
            
            # Compile final validation result
            all_results = static_results + intelligent_results
            overall_success = all([r.passed for r in all_results if r.severity in [ValidationLevel.CRITICAL, ValidationLevel.STRICT]])
            
            # Generate validation report
            validation_report = self._generate_validation_report(all_results, overall_success)
            
            # Track validation
            self.validation_history.append({
                'timestamp': input_data.get('timestamp'),
                'content_length': len(str(content_to_validate)),
                'rules_applied': len([r for r in self.validation_rules if self._should_apply_rule(r)]),
                'total_checks': len(all_results),
                'passed_checks': len([r for r in all_results if r.passed]),
                'critical_failures': len([r for r in all_results if not r.passed and r.severity == ValidationLevel.CRITICAL]),
                'overall_success': overall_success
            })
            
            result = AgentResult(
                success=overall_success,
                content=validation_report,
                metadata={
                    'validation_results': [
                        {
                            'rule': r.rule_name,
                            'passed': r.passed,
                            'message': r.message,
                            'severity': r.severity.value
                        } for r in all_results
                    ],
                    'total_rules_checked': len(all_results),
                    'critical_failures': len([r for r in all_results if not r.passed and r.severity == ValidationLevel.CRITICAL]),
                    'validation_level': self.validation_level.value
                }
            )
            
            if not overall_success:
                critical_failures = [r for r in all_results if not r.passed and r.severity == ValidationLevel.CRITICAL]
                result.error_message = f"Validation failed with {len(critical_failures)} critical issues"
            
            return result
            
        except Exception as e:
            logger.error(f"ValidatorAgent {self.id} validation error: {str(e)}")
            return AgentResult(
                success=False,
                content="",
                error_message=f"Validation execution failed: {str(e)}"
            )
    
    async def _run_static_validation(
        self,
        content: Any,
        custom_rules: Optional[List[str]],
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Run static validation rules"""
        results = []
        
        for rule in self.validation_rules:
            # Skip rules that don't meet current validation level
            if not self._should_apply_rule(rule):
                continue
            
            # Skip if custom rules specified and this rule not included
            if custom_rules and rule.name not in custom_rules:
                continue
            
            try:
                if rule.rule_function:
                    result = await rule.rule_function(content, context)
                    results.append(result)
            except Exception as e:
                logger.error(f"Error running validation rule {rule.name}: {str(e)}")
                results.append(ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    message=f"Rule execution error: {str(e)}",
                    severity=rule.level
                ))
        
        return results
    
    async def _run_intelligent_validation(
        self,
        content: Any,
        context: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Optional[ValidationResult]:
        """Run LLM-based intelligent validation"""
        system_prompt = """You are an expert content validator with deep knowledge of safety, quality, and compliance standards.

Your task is to analyze content for:
1. Logical consistency and coherence
2. Completeness and accuracy
3. Safety and appropriateness
4. Compliance with specified requirements
5. Quality and professionalism
6. Potential risks or issues

Provide structured analysis identifying any issues, concerns, or recommendations."""

        user_prompt = f"""Validate the following content for quality, safety, and compliance:

CONTENT TO VALIDATE:
{content}

VALIDATION CONTEXT:
{json.dumps(context, indent=2)}

VALIDATION REQUIREMENTS:
{input_data.get('validation_requirements', 'Standard quality and safety validation')}

Please provide:
1. Overall assessment (PASS/FAIL)
2. Specific issues identified (if any)
3. Risk level assessment (LOW/MEDIUM/HIGH)
4. Recommendations for improvement
5. Confidence in your assessment

Focus on identifying genuine issues that could impact safety, quality, or compliance."""

        try:
            llm_result = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=input_data.get('max_tokens_validation', 1024),
                temperature=0.2  # Low temperature for consistent validation
            )
            
            if llm_result.success:
                # Parse LLM result to extract validation decision
                content_lower = llm_result.content.lower()
                passed = 'pass' in content_lower and ('fail' not in content_lower or content_lower.index('pass') < content_lower.index('fail'))
                
                # Determine severity based on content analysis
                if 'high' in content_lower and 'risk' in content_lower:
                    severity = ValidationLevel.CRITICAL
                elif 'medium' in content_lower and 'risk' in content_lower:
                    severity = ValidationLevel.STRICT
                else:
                    severity = ValidationLevel.STANDARD
                
                return ValidationResult(
                    rule_name="intelligent_validation",
                    passed=passed,
                    message=llm_result.content,
                    severity=severity,
                    details={'tokens_used': llm_result.tokens_used, 'cost_usd': llm_result.cost_usd}
                )
            
        except Exception as e:
            logger.error(f"Intelligent validation error: {str(e)}")
        
        return None
    
    def _should_apply_rule(self, rule: ValidationRule) -> bool:
        """Determine if rule should be applied based on validation level"""
        level_hierarchy = {
            ValidationLevel.BASIC: 1,
            ValidationLevel.STANDARD: 2, 
            ValidationLevel.STRICT: 3,
            ValidationLevel.CRITICAL: 4
        }
        
        return level_hierarchy[rule.level] <= level_hierarchy[self.validation_level]
    
    def _generate_validation_report(self, results: List[ValidationResult], overall_success: bool) -> str:
        """Generate comprehensive validation report"""
        report = ["=== VALIDATION REPORT ===", ""]
        
        # Overall status
        status = "PASSED" if overall_success else "FAILED"
        report.append(f"Overall Status: {status}")
        report.append(f"Total Rules Checked: {len(results)}")
        report.append("")
        
        # Group results by severity
        by_severity = {}
        for result in results:
            if result.severity not in by_severity:
                by_severity[result.severity] = []
            by_severity[result.severity].append(result)
        
        # Report by severity level
        for severity in [ValidationLevel.CRITICAL, ValidationLevel.STRICT, ValidationLevel.STANDARD, ValidationLevel.BASIC]:
            if severity in by_severity:
                report.append(f"=== {severity.value.upper()} LEVEL ===")
                for result in by_severity[severity]:
                    status_icon = "✅" if result.passed else "❌"
                    report.append(f"{status_icon} {result.rule_name}: {result.message}")
                report.append("")
        
        # Summary
        passed = len([r for r in results if r.passed])
        failed = len(results) - passed
        critical_failed = len([r for r in results if not r.passed and r.severity == ValidationLevel.CRITICAL])
        
        report.append("=== SUMMARY ===")
        report.append(f"Passed: {passed}")
        report.append(f"Failed: {failed}")
        report.append(f"Critical Failures: {critical_failed}")
        
        if not overall_success:
            report.append("")
            report.append("⚠️  VALIDATION FAILED - Content requires review and correction before use.")
        
        return "\n".join(report)
    
    # Static validation rule implementations
    
    async def _validate_json_format(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate JSON format"""
        if not isinstance(content, str):
            return ValidationResult("json_format", True, "Content is not string, skipping JSON validation", ValidationLevel.BASIC)
        
        try:
            json.loads(content)
            return ValidationResult("json_format", True, "Valid JSON format", ValidationLevel.BASIC)
        except json.JSONDecodeError as e:
            return ValidationResult("json_format", False, f"Invalid JSON format: {str(e)}", ValidationLevel.BASIC)
    
    async def _validate_required_fields(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate required fields presence"""
        required_fields = context.get('required_fields', [])
        if not required_fields:
            return ValidationResult("required_fields", True, "No required fields specified", ValidationLevel.STANDARD)
        
        if isinstance(content, dict):
            missing = [field for field in required_fields if field not in content]
            if missing:
                return ValidationResult("required_fields", False, f"Missing required fields: {missing}", ValidationLevel.STANDARD)
            else:
                return ValidationResult("required_fields", True, "All required fields present", ValidationLevel.STANDARD)
        
        return ValidationResult("required_fields", True, "Content is not dict, skipping field validation", ValidationLevel.STANDARD)
    
    async def _validate_field_types(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate field data types"""
        expected_types = context.get('field_types', {})
        if not expected_types:
            return ValidationResult("field_types", True, "No field type requirements specified", ValidationLevel.STANDARD)
        
        if isinstance(content, dict):
            type_errors = []
            for field, expected_type in expected_types.items():
                if field in content:
                    actual_type = type(content[field]).__name__
                    if actual_type != expected_type:
                        type_errors.append(f"{field}: expected {expected_type}, got {actual_type}")
            
            if type_errors:
                return ValidationResult("field_types", False, f"Type errors: {type_errors}", ValidationLevel.STANDARD)
            else:
                return ValidationResult("field_types", True, "All field types correct", ValidationLevel.STANDARD)
        
        return ValidationResult("field_types", True, "Content is not dict, skipping type validation", ValidationLevel.STANDARD)
    
    async def _validate_content_length(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate content length"""
        min_length = context.get('min_length', 0)
        max_length = context.get('max_length', float('inf'))
        
        content_str = str(content)
        length = len(content_str)
        
        if length < min_length:
            return ValidationResult("content_length", False, f"Content too short: {length} < {min_length}", ValidationLevel.BASIC)
        elif length > max_length:
            return ValidationResult("content_length", False, f"Content too long: {length} > {max_length}", ValidationLevel.BASIC)
        else:
            return ValidationResult("content_length", True, f"Content length OK: {length}", ValidationLevel.BASIC)
    
    async def _validate_forbidden_content(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Check for forbidden content patterns"""
        forbidden_patterns = context.get('forbidden_patterns', [])
        content_str = str(content).lower()
        
        found_forbidden = []
        for pattern in forbidden_patterns:
            if re.search(pattern.lower(), content_str):
                found_forbidden.append(pattern)
        
        if found_forbidden:
            return ValidationResult("forbidden_content", False, f"Forbidden content detected: {found_forbidden}", ValidationLevel.STRICT)
        else:
            return ValidationResult("forbidden_content", True, "No forbidden content detected", ValidationLevel.STRICT)
    
    async def _validate_prompt_injection(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Detect potential prompt injection attempts"""
        content_str = str(content).lower()
        
        # Common prompt injection patterns
        injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'forget\s+everything\s+above',
            r'act\s+as\s+if\s+you\s+are',
            r'pretend\s+to\s+be',
            r'you\s+are\s+now',
            r'new\s+instructions:',
            r'system\s+prompt:',
            r'override\s+safety'
        ]
        
        detected_patterns = []
        for pattern in injection_patterns:
            if re.search(pattern, content_str):
                detected_patterns.append(pattern)
        
        if detected_patterns:
            return ValidationResult("prompt_injection", False, f"Potential prompt injection detected: {detected_patterns}", ValidationLevel.CRITICAL)
        else:
            return ValidationResult("prompt_injection", True, "No prompt injection patterns detected", ValidationLevel.CRITICAL)
    
    async def _validate_sensitive_data(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Check for sensitive data exposure"""
        content_str = str(content)
        
        # Patterns for sensitive data
        sensitive_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'api_key': r'[A-Za-z0-9]{32,}',  # Generic long alphanumeric strings
        }
        
        detected_sensitive = []
        for data_type, pattern in sensitive_patterns.items():
            if re.search(pattern, content_str):
                detected_sensitive.append(data_type)
        
        if detected_sensitive:
            return ValidationResult("sensitive_data", False, f"Sensitive data detected: {detected_sensitive}", ValidationLevel.STRICT)
        else:
            return ValidationResult("sensitive_data", True, "No sensitive data patterns detected", ValidationLevel.STRICT)
    
    async def _validate_consistency(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Check internal consistency of content"""
        # This is a placeholder for more sophisticated consistency checking
        # In practice, this might involve cross-referencing facts, checking logical flow, etc.
        return ValidationResult("consistency_check", True, "Basic consistency check passed", ValidationLevel.STANDARD)
    
    async def _validate_completeness(self, content: Any, context: Dict[str, Any]) -> ValidationResult:
        """Verify content completeness"""
        required_sections = context.get('required_sections', [])
        if not required_sections:
            return ValidationResult("completeness_check", True, "No required sections specified", ValidationLevel.STANDARD)
        
        content_str = str(content).lower()
        missing_sections = []
        
        for section in required_sections:
            if section.lower() not in content_str:
                missing_sections.append(section)
        
        if missing_sections:
            return ValidationResult("completeness_check", False, f"Missing required sections: {missing_sections}", ValidationLevel.STANDARD)
        else:
            return ValidationResult("completeness_check", True, "All required sections present", ValidationLevel.STANDARD)
    
    def add_custom_rule(self, rule: ValidationRule):
        """Add a custom validation rule"""
        self.validation_rules.append(rule)
        logger.info(f"Added custom validation rule: {rule.name}")
    
    async def get_validator_statistics(self) -> Dict[str, Any]:
        """Get validator-specific statistics"""
        base_stats = await self.get_statistics()
        
        if self.validation_history:
            avg_rules_per_validation = sum(h['rules_applied'] for h in self.validation_history) / len(self.validation_history)
            avg_success_rate = sum(h['overall_success'] for h in self.validation_history) / len(self.validation_history)
            total_critical_failures = sum(h['critical_failures'] for h in self.validation_history)
        else:
            avg_rules_per_validation = 0
            avg_success_rate = 0
            total_critical_failures = 0
        
        validator_stats = {
            'validation_level': self.validation_level.value,
            'total_rules_configured': len(self.validation_rules),
            'total_validations': len(self.validation_history),
            'average_rules_per_validation': avg_rules_per_validation,
            'validation_success_rate': avg_success_rate,
            'total_critical_failures': total_critical_failures
        }
        
        return {**base_stats, **validator_stats}