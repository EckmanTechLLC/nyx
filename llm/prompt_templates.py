"""
Prompt Template Management for NYX
Database-backed prompt template system with versioning and usage tracking
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import uuid
import re

from database.connection import db_manager
from database.models import PromptTemplate as DBPromptTemplate
from llm.models import PromptTemplate
from sqlalchemy import select, update, desc
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class PromptTemplateError(Exception):
    """Custom exception for prompt template errors"""
    pass

class PromptTemplateManager:
    """
    Database-backed prompt template management system
    
    Features:
    - Template versioning and activation management
    - Variable extraction and validation
    - Usage tracking and success rate monitoring
    - Template rendering with variable substitution
    - CRUD operations with database persistence
    """
    
    def __init__(self):
        self.variable_pattern = re.compile(r'\{([^}]+)\}')  # Matches {variable_name}
    
    async def create_template(
        self,
        name: str,
        content: str,
        template_type: str = "user",
        variables: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """
        Create a new prompt template
        
        Args:
            name: Unique template name
            content: Template content with {variable} placeholders
            template_type: Type of template ('system', 'user', 'assistant')
            variables: List of required variables (auto-detected if None)
            created_by: Creator identifier
            metadata: Additional metadata
            
        Returns:
            Created PromptTemplate instance
        """
        try:
            # Auto-detect variables if not provided
            if variables is None:
                variables = self._extract_variables(content)
            
            # Validate template type
            if template_type not in ['system', 'user', 'assistant']:
                raise PromptTemplateError(f"Invalid template type: {template_type}")
            
            async with db_manager.get_async_session() as session:
                # Check if template name already exists
                existing = await session.execute(
                    select(DBPromptTemplate).where(
                        DBPromptTemplate.name == name,
                        DBPromptTemplate.is_active == True
                    )
                )
                if existing.scalar_one_or_none():
                    raise PromptTemplateError(f"Active template with name '{name}' already exists")
                
                # Create database record
                db_template = DBPromptTemplate(
                    id=uuid.uuid4(),
                    name=name,
                    template_type=template_type,
                    content=content,
                    variables=variables,
                    version=1,
                    is_active=True,
                    created_by=created_by,
                    usage_count=0,
                    success_rate=Decimal('0.0')
                )
                
                session.add(db_template)
                await session.commit()
                await session.refresh(db_template)
                
                # Convert to domain model
                template = self._db_to_domain_model(db_template)
                template.metadata = metadata or {}
                
                logger.info(f"Created template '{name}' with {len(variables)} variables")
                return template
                
        except IntegrityError as e:
            raise PromptTemplateError(f"Template name '{name}' already exists") from e
        except Exception as e:
            logger.error(f"Failed to create template '{name}': {str(e)}")
            raise PromptTemplateError(f"Failed to create template: {str(e)}") from e
    
    async def get_template(self, name: str, version: Optional[int] = None) -> Optional[PromptTemplate]:
        """
        Retrieve a template by name and optional version
        
        Args:
            name: Template name
            version: Specific version (latest active if None)
            
        Returns:
            PromptTemplate instance or None if not found
        """
        try:
            async with db_manager.get_async_session() as session:
                query = select(DBPromptTemplate).where(DBPromptTemplate.name == name)
                
                if version is not None:
                    query = query.where(DBPromptTemplate.version == version)
                else:
                    # Get latest active version
                    query = query.where(DBPromptTemplate.is_active == True).order_by(desc(DBPromptTemplate.version))
                
                result = await session.execute(query)
                db_template = result.scalar_one_or_none()
                
                if not db_template:
                    return None
                
                return self._db_to_domain_model(db_template)
                
        except Exception as e:
            logger.error(f"Failed to retrieve template '{name}': {str(e)}")
            return None
    
    async def list_templates(
        self,
        template_type: Optional[str] = None,
        active_only: bool = True,
        created_by: Optional[str] = None
    ) -> List[PromptTemplate]:
        """
        List templates with optional filtering
        
        Args:
            template_type: Filter by template type
            active_only: Only return active templates
            created_by: Filter by creator
            
        Returns:
            List of PromptTemplate instances
        """
        try:
            async with db_manager.get_async_session() as session:
                query = select(DBPromptTemplate)
                
                if template_type:
                    query = query.where(DBPromptTemplate.template_type == template_type)
                
                if active_only:
                    query = query.where(DBPromptTemplate.is_active == True)
                
                if created_by:
                    query = query.where(DBPromptTemplate.created_by == created_by)
                
                query = query.order_by(DBPromptTemplate.name, desc(DBPromptTemplate.version))
                
                result = await session.execute(query)
                db_templates = result.scalars().all()
                
                return [self._db_to_domain_model(t) for t in db_templates]
                
        except Exception as e:
            logger.error(f"Failed to list templates: {str(e)}")
            return []
    
    async def update_template(
        self,
        name: str,
        content: Optional[str] = None,
        variables: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[PromptTemplate]:
        """
        Update an existing template (creates new version if content changes)
        
        Args:
            name: Template name
            content: New template content (creates new version)
            variables: Updated variable list
            is_active: Activate/deactivate template
            
        Returns:
            Updated PromptTemplate instance or None if not found
        """
        try:
            async with db_manager.get_async_session() as session:
                # Get current active template
                current = await session.execute(
                    select(DBPromptTemplate).where(
                        DBPromptTemplate.name == name,
                        DBPromptTemplate.is_active == True
                    )
                )
                current_template = current.scalar_one_or_none()
                
                if not current_template:
                    return None
                
                # If content is changing, create new version
                if content and content != current_template.content:
                    # Deactivate current version
                    await session.execute(
                        update(DBPromptTemplate)
                        .where(DBPromptTemplate.id == current_template.id)
                        .values(is_active=False)
                    )
                    
                    # Create new version
                    new_variables = variables or self._extract_variables(content)
                    new_template = DBPromptTemplate(
                        id=uuid.uuid4(),
                        name=name,
                        template_type=current_template.template_type,
                        content=content,
                        variables=new_variables,
                        version=current_template.version + 1,
                        is_active=True,
                        created_by=current_template.created_by,
                        usage_count=0,
                        success_rate=Decimal('0.0')
                    )
                    
                    session.add(new_template)
                    await session.commit()
                    await session.refresh(new_template)
                    
                    logger.info(f"Created new version {new_template.version} of template '{name}'")
                    return self._db_to_domain_model(new_template)
                
                else:
                    # Update existing template in-place
                    update_values = {}
                    
                    if variables is not None:
                        update_values['variables'] = variables
                    
                    if is_active is not None:
                        update_values['is_active'] = is_active
                    
                    if update_values:
                        await session.execute(
                            update(DBPromptTemplate)
                            .where(DBPromptTemplate.id == current_template.id)
                            .values(**update_values)
                        )
                        await session.commit()
                        
                        # Refresh and return
                        await session.refresh(current_template)
                    
                    return self._db_to_domain_model(current_template)
                
        except Exception as e:
            logger.error(f"Failed to update template '{name}': {str(e)}")
            raise PromptTemplateError(f"Failed to update template: {str(e)}") from e
    
    async def delete_template(self, name: str, version: Optional[int] = None) -> bool:
        """
        Delete a template (deactivates rather than hard delete for audit trail)
        
        Args:
            name: Template name
            version: Specific version (all versions if None)
            
        Returns:
            True if deleted, False if not found
        """
        try:
            async with db_manager.get_async_session() as session:
                query = update(DBPromptTemplate).where(DBPromptTemplate.name == name)
                
                if version is not None:
                    query = query.where(DBPromptTemplate.version == version)
                
                result = await session.execute(
                    query.values(is_active=False)
                )
                
                await session.commit()
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"Deactivated {deleted_count} version(s) of template '{name}'")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete template '{name}': {str(e)}")
            return False
    
    async def render_template(
        self,
        name: str,
        variables: Dict[str, Any],
        version: Optional[int] = None
    ) -> str:
        """
        Render a template with provided variables
        
        Args:
            name: Template name
            variables: Variable values for substitution
            version: Specific version (latest active if None)
            
        Returns:
            Rendered template content
        """
        template = await self.get_template(name, version)
        if not template:
            raise PromptTemplateError(f"Template '{name}' not found")
        
        try:
            rendered = template.render(variables)
            
            # Update usage stats (async, non-blocking)
            asyncio.create_task(self._update_usage_stats(template.id, True))
            
            return rendered
            
        except ValueError as e:
            # Update usage stats for failure
            asyncio.create_task(self._update_usage_stats(template.id, False))
            raise PromptTemplateError(f"Template rendering failed: {str(e)}") from e
    
    async def validate_template_variables(
        self,
        name: str,
        variables: Dict[str, Any],
        version: Optional[int] = None
    ) -> List[str]:
        """
        Validate that all required variables are provided
        
        Args:
            name: Template name
            variables: Variable values to validate
            version: Specific version (latest active if None)
            
        Returns:
            List of missing variable names (empty if all provided)
        """
        template = await self.get_template(name, version)
        if not template:
            raise PromptTemplateError(f"Template '{name}' not found")
        
        return template.validate_variables(variables)
    
    def _extract_variables(self, content: str) -> List[str]:
        """Extract variable names from template content"""
        variables = self.variable_pattern.findall(content)
        # Remove duplicates and sort
        return sorted(list(set(variables)))
    
    def _db_to_domain_model(self, db_template: DBPromptTemplate) -> PromptTemplate:
        """Convert database model to domain model"""
        return PromptTemplate(
            id=str(db_template.id),
            name=db_template.name,
            template_type=db_template.template_type,
            content=db_template.content,
            variables=db_template.variables or [],
            version=db_template.version,
            is_active=db_template.is_active,
            created_at=db_template.created_at,
            updated_at=db_template.updated_at,
            created_by=db_template.created_by,
            usage_count=db_template.usage_count,
            success_rate=db_template.success_rate
        )
    
    async def _update_usage_stats(self, template_id: str, success: bool):
        """Update template usage statistics"""
        try:
            async with db_manager.get_async_session() as session:
                # Get current stats
                result = await session.execute(
                    select(DBPromptTemplate.usage_count, DBPromptTemplate.success_rate)
                    .where(DBPromptTemplate.id == template_id)
                )
                current = result.one_or_none()
                
                if current:
                    usage_count, success_rate = current
                    new_usage_count = usage_count + 1
                    
                    # Calculate new success rate
                    if usage_count == 0:
                        new_success_rate = Decimal('1.0') if success else Decimal('0.0')
                    else:
                        current_successes = float(success_rate) * usage_count
                        new_successes = current_successes + (1 if success else 0)
                        new_success_rate = Decimal(str(new_successes / new_usage_count))
                    
                    # Update database
                    await session.execute(
                        update(DBPromptTemplate)
                        .where(DBPromptTemplate.id == template_id)
                        .values(
                            usage_count=new_usage_count,
                            success_rate=new_success_rate,
                            updated_at=datetime.now()
                        )
                    )
                    await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update usage stats for template {template_id}: {str(e)}")
    
    async def get_template_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a template"""
        try:
            async with db_manager.get_async_session() as session:
                result = await session.execute(
                    select(
                        DBPromptTemplate.name,
                        DBPromptTemplate.version,
                        DBPromptTemplate.usage_count,
                        DBPromptTemplate.success_rate,
                        DBPromptTemplate.created_at,
                        DBPromptTemplate.is_active
                    ).where(
                        DBPromptTemplate.name == name,
                        DBPromptTemplate.is_active == True
                    )
                )
                template_data = result.one_or_none()
                
                if not template_data:
                    return None
                
                return {
                    "name": template_data.name,
                    "version": template_data.version,
                    "usage_count": template_data.usage_count,
                    "success_rate": float(template_data.success_rate),
                    "created_at": template_data.created_at.isoformat(),
                    "is_active": template_data.is_active
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats for template '{name}': {str(e)}")
            return None

# Import asyncio for task creation
import asyncio