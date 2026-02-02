"""
Social monitoring API endpoints for NYX Moltbook integration.

Provides read-only access to NYX's social activity on Moltbook.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from ...core.database import get_db
from database.models import SocialClaimValidation, MotivationalState

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class SocialPostResponse(BaseModel):
    """Response model for a social post"""
    id: str = Field(..., description="Post ID")
    title: str = Field(..., description="Post title")
    content: str = Field(..., description="Post content")
    url: str = Field(..., description="Moltbook URL")
    created_at: str = Field(..., description="Creation timestamp")
    engagement: Dict[str, int] = Field(..., description="Engagement metrics")


class SocialCommentResponse(BaseModel):
    """Response model for a social comment"""
    id: str = Field(..., description="Comment/Post ID this comment was made on")
    content: str = Field(..., description="Comment text")
    post_url: str = Field(..., description="URL to the post")
    created_at: str = Field(..., description="Creation timestamp")
    context: str = Field(..., description="Brief context about the comment")


class SocialMetricsResponse(BaseModel):
    """Response model for social metrics"""
    cycles_since_last_post: int = Field(..., description="Monitoring cycles since last post")
    claims_corrected_since_last_post: int = Field(..., description="Claims corrected since last post")
    posts_this_hour: int = Field(..., description="Posts created in last hour")
    max_posts_per_hour: int = Field(default=2, description="Maximum posts per hour")
    last_post_time: Optional[str] = Field(None, description="Last post creation time")
    total_posts: int = Field(..., description="Total posts created")
    total_comments: int = Field(..., description="Total comments made")
    timestamp: str = Field(..., description="Metrics timestamp")


@router.get("/posts")
async def get_nyx_posts(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get NYX's posts from Moltbook.

    Returns a list of posts NYX has created on Moltbook with engagement metrics.

    Args:
        limit: Maximum number of posts to return (default 50)
        db: Database session

    Returns:
        Dict containing list of posts and summary
    """
    try:
        # Get NYX's posts directly from Moltbook profile
        from core.tools.moltbook import MoltbookTool
        moltbook = MoltbookTool()

        profile_data = moltbook.get_agent_profile('TheRealNyx')
        recent_posts = profile_data.get('recentPosts', [])

        # Format posts for response
        posts = []
        for post in recent_posts[:limit]:
            posts.append({
                'id': post.get('id'),
                'title': post.get('title', ''),
                'content': post.get('content', ''),
                'url': f"https://www.moltbook.com/post/{post.get('id')}",
                'created_at': post.get('created_at', ''),
                'engagement': {
                    'upvotes': post.get('upvotes', 0),
                    'downvotes': post.get('downvotes', 0),
                    'comments': post.get('comment_count', 0)
                }
            })

        return {
            'posts': posts,
            'total': len(posts),
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get NYX posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve posts: {str(e)}"
        )


@router.get("/comments")
async def get_nyx_comments(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get NYX's comments on Moltbook.

    Returns a list of comments NYX has made on posts.

    Args:
        limit: Maximum number of comments to return (default 100)
        db: Database session

    Returns:
        Dict containing list of comments and summary
    """
    try:
        # Query ONLY actual responses from SocialClaimValidation table
        # Filter by validation_status='contradicted' which means NYX actually responded
        from sqlalchemy import cast, String
        result = await db.execute(
            select(SocialClaimValidation)
            .where(
                SocialClaimValidation.source_platform.in_(['moltbook', 'moltbook_comment']),
                cast(SocialClaimValidation.validation_status, String) == 'contradicted'  # Only actual responses
            )
            .order_by(desc(SocialClaimValidation.created_at))
            .limit(limit)
        )
        validations = result.scalars().all()

        # Format comments for response
        comments = []
        for validation in validations:
            comment_id = validation.source_post_id
            is_comment_reply = validation.source_platform == 'moltbook_comment'

            # Get actual response text from supporting_evidence
            response_text = validation.supporting_evidence.get('response_text', 'N/A') if validation.supporting_evidence else 'N/A'

            # For comment replies, get the actual post_id from supporting_evidence
            # For regular post comments, use the source_post_id
            actual_post_id = validation.supporting_evidence.get('post_id', comment_id) if is_comment_reply and validation.supporting_evidence else comment_id

            comments.append({
                'id': comment_id,
                'content': response_text,  # Show actual response, not evaluation reasoning
                'post_url': f"https://www.moltbook.com/post/{actual_post_id}",
                'created_at': validation.created_at.isoformat() if validation.created_at else '',
                'context': 'Comment reply' if is_comment_reply else f"Response to {validation.source_agent_name}",
                'type': 'reply' if is_comment_reply else 'comment'
            })

        return {
            'comments': comments,
            'total': len(comments),
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get NYX comments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve comments: {str(e)}"
        )


@router.get("/metrics")
async def get_social_metrics(
    db: AsyncSession = Depends(get_db)
) -> SocialMetricsResponse:
    """
    Get social monitoring metrics.

    Returns current post creation tracking metrics including cycles,
    claims corrected, and posting frequency.

    Args:
        db: Database session

    Returns:
        SocialMetricsResponse containing current metrics
    """
    try:
        # Get motivational state with post tracking metadata
        result = await db.execute(
            select(MotivationalState)
            .where(MotivationalState.motivation_type == 'monitor_social_network')
        )
        state = result.scalar_one_or_none()

        if not state or not state.metadata_:
            # Return default metrics if no state found
            return SocialMetricsResponse(
                cycles_since_last_post=0,
                claims_corrected_since_last_post=0,
                posts_this_hour=0,
                max_posts_per_hour=2,
                last_post_time=None,
                total_posts=0,
                total_comments=0,
                timestamp=datetime.utcnow().isoformat()
            )

        # Extract post tracking data
        post_tracking = state.metadata_.get('post_tracking', {})

        # Count total posts and comments from SocialClaimValidation
        total_posts_result = await db.execute(
            select(SocialClaimValidation)
            .where(SocialClaimValidation.source_platform == 'moltbook')
        )
        total_posts = len(total_posts_result.scalars().all())

        total_comments_result = await db.execute(
            select(SocialClaimValidation)
            .where(SocialClaimValidation.source_platform == 'moltbook_comment')
        )
        total_comments = len(total_comments_result.scalars().all())

        return SocialMetricsResponse(
            cycles_since_last_post=post_tracking.get('cycles_since_last_post', 0),
            claims_corrected_since_last_post=post_tracking.get('claims_corrected_since_last_post', 0),
            posts_this_hour=len(post_tracking.get('posts_this_hour', [])),
            max_posts_per_hour=2,
            last_post_time=post_tracking.get('last_post_time'),
            total_posts=total_posts,
            total_comments=total_comments,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to get social metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )
