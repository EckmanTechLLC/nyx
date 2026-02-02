"""
Moltbook Social Network Tool

Provides interface for NYX to interact with Moltbook AI agent social network.
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.connection import get_sync_session
from database.models import SystemConfig
from core.tools.base import BaseTool

logger = logging.getLogger(__name__)


class MoltbookTool(BaseTool):
    """Tool for interacting with Moltbook API"""

    BASE_URL = "https://www.moltbook.com/api/v1"

    def __init__(self):
        super().__init__(tool_name="moltbook")
        self.api_key = self._load_api_key()
        self.client = httpx.Client(timeout=30.0)

    def _load_api_key(self) -> Optional[str]:
        """Load Moltbook API key from database"""
        try:
            session = get_sync_session()
            config = session.query(SystemConfig).filter(
                SystemConfig.config_key == 'moltbook_api_key'
            ).first()
            session.close()

            if config and 'api_key' in config.config_value:
                return config.config_value['api_key']
            else:
                logger.warning("Moltbook API key not found in database")
                return None
        except Exception as e:
            logger.error(f"Error loading Moltbook API key: {e}")
            return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Moltbook API"""
        if not self.api_key:
            raise ValueError("Moltbook API key not configured")

        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            if method == "GET":
                response = self.client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Moltbook API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Moltbook request failed: {e}")
            raise

    def get_posts(
        self,
        sort: str = "hot",
        limit: int = 25,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from Moltbook feed

        Args:
            sort: Sort order (hot, new, top, rising)
            limit: Number of posts to fetch (max 100)
            offset: Pagination offset

        Returns:
            List of post dictionaries
        """
        params = {
            "sort": sort,
            "limit": min(limit, 100),
            "offset": offset
        }

        result = self._make_request("GET", "/posts", params=params)
        return result.get("posts", [])

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """
        Fetch specific post by ID

        Args:
            post_id: Post UUID

        Returns:
            Post dictionary
        """
        result = self._make_request("GET", f"/posts/{post_id}")
        return result

    def get_comments(
        self,
        post_id: str,
        sort: str = "top"
    ) -> List[Dict[str, Any]]:
        """
        Fetch comments for a post

        Args:
            post_id: Post UUID
            sort: Sort order (top, new, controversial)

        Returns:
            List of comment dictionaries
        """
        params = {"sort": sort}
        result = self._make_request("GET", f"/posts/{post_id}/comments", params=params)
        return result.get("comments", [])

    def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new post on Moltbook

        Args:
            submolt: Community name to post in
            title: Post title
            content: Text content (optional, for text posts)
            url: Link URL (optional, for link posts)

        Returns:
            Created post dictionary
        """
        data = {
            "submolt": submolt,
            "title": title
        }

        if content:
            data["content"] = content
        if url:
            data["url"] = url

        result = self._make_request("POST", "/posts", data=data)
        return result

    def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a comment on a post

        Args:
            post_id: Post UUID to comment on
            content: Comment text
            parent_id: Parent comment UUID (for nested replies)

        Returns:
            Created comment dictionary
        """
        data = {"content": content}
        if parent_id:
            data["parent_id"] = parent_id

        result = self._make_request("POST", f"/posts/{post_id}/comments", data=data)
        return result

    def upvote_post(self, post_id: str) -> Dict[str, Any]:
        """Upvote a post"""
        return self._make_request("POST", f"/posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> Dict[str, Any]:
        """Downvote a post"""
        return self._make_request("POST", f"/posts/{post_id}/downvote")

    def search(
        self,
        query: str,
        limit: int = 25
    ) -> Dict[str, Any]:
        """
        Search Moltbook for posts, agents, and communities

        Args:
            query: Search query string
            limit: Max results

        Returns:
            Search results dictionary
        """
        params = {
            "q": query,
            "limit": limit
        }
        return self._make_request("GET", "/search", params=params)

    def get_agent_profile(self, agent_name: str) -> Dict[str, Any]:
        """
        Get profile information for an agent

        Args:
            agent_name: Agent username

        Returns:
            Agent profile dictionary
        """
        params = {"name": agent_name}
        return self._make_request("GET", "/agents/profile", params=params)

    async def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters"""
        return True  # Moltbook methods handle their own validation

    async def _validate_safety(self, parameters: Dict[str, Any]) -> bool:
        """Validate safety constraints"""
        return True  # Read-only operations are safe

    async def _tool_specific_execution(self, parameters: Dict[str, Any]) -> Any:
        """Tool-specific execution - not used, methods called directly"""
        raise NotImplementedError("Call specific methods like get_posts() instead")

    def __del__(self):
        """Cleanup HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()
