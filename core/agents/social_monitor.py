"""
Social Monitor Agent for NYX Moltbook Integration

Monitors Moltbook social network, evaluates posts for grounded responses.
NYX serves as the "reality check" presence - correcting outlandish/false claims
with evidence-based reasoning.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from .base import BaseAgent, AgentResult
from core.tools.moltbook import MoltbookTool
from llm.models import LLMModel
from database.connection import get_sync_session
from database.models import SocialClaimValidation, MotivationalState

logger = logging.getLogger(__name__)


class SocialMonitorAgent(BaseAgent):
    """
    Agent that monitors social networks and provides grounded reality checks

    Capabilities:
    - Fetch posts from Moltbook
    - Filter out already-responded posts (anti-spam)
    - Evaluate posts for outlandish/false/misleading claims using LLM
    - Generate evidence-based corrections
    - Post responses to Moltbook
    - Track responses in database
    """

    def __init__(
        self,
        thought_tree_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        max_retries: int = 2,
        timeout_seconds: int = 300,
        llm_model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU,
        use_native_caching: bool = True,
        post_limit: int = 10,
        max_offset: int = 50,  # Max posts to paginate before rotating sort
        max_comment_replies_per_run: int = 3  # Rate limit: max comment replies per execution
    ):
        super().__init__(
            agent_type="task",  # Using task type since it's in allowed list
            thought_tree_id=thought_tree_id,
            parent_agent_id=parent_agent_id,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            llm_model=llm_model,
            use_native_caching=use_native_caching
        )

        self.post_limit = post_limit
        self.max_offset = max_offset
        self.max_comment_replies_per_run = max_comment_replies_per_run
        self.moltbook = None
        self.sort_strategies = ['hot', 'new', 'rising']

    async def _agent_specific_initialization(self) -> bool:
        """Initialize Moltbook tool"""
        try:
            self.moltbook = MoltbookTool()
            logger.info(f"SocialMonitorAgent {self.id} initialized with MoltbookTool")
            return True
        except Exception as e:
            logger.error(f"SocialMonitorAgent {self.id} initialization failed: {e}")
            return False

    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        # Social monitor doesn't need specific input validation
        return True

    async def _agent_specific_execution(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute social monitoring workflow"""
        try:
            # 1. Fetch posts from Moltbook
            posts = self._fetch_posts()
            logger.info(f"Fetched {len(posts)} posts from Moltbook")

            # 2. Filter out posts we already responded to
            new_posts = self._filter_already_responded(posts)
            logger.info(f"Filtered to {len(new_posts)} new posts (skipped {len(posts) - len(new_posts)} already responded)")

            # 3. Evaluate and respond to posts
            evaluation_results = await self._evaluate_and_respond(new_posts)

            # 4. Check for comments on NYX's own posts and engage
            own_posts_engagement = await self._engage_with_own_post_comments()

            # 5. Check comments on monitored posts for claims worth addressing
            comment_engagement = await self._engage_with_post_comments(posts)

            # 6. Consider creating an original post based on accumulated observations
            post_creation = await self._consider_creating_post(evaluation_results, own_posts_engagement, comment_engagement)

            # 7. Generate summary
            summary = self._generate_summary(posts, new_posts, evaluation_results, own_posts_engagement, comment_engagement, post_creation)

            return AgentResult(
                success=True,
                content=str(summary),
                metadata={
                    'posts_fetched': len(posts),
                    'posts_evaluated': len(new_posts),
                    'posts_warranting_response': evaluation_results['evaluated_count'],
                    'responses_posted': evaluation_results['responses_posted'],
                    'own_post_replies': own_posts_engagement['replies_posted'],
                    'comment_replies': comment_engagement['replies_posted'],
                    'original_posts_created': post_creation['posts_created']
                }
            )

        except Exception as e:
            logger.error(f"SocialMonitorAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                content="",
                error_message=str(e)
            )

    def _get_fetch_state(self) -> Dict[str, Any]:
        """Get current pagination and sort state from database"""
        try:
            session = get_sync_session()

            state = session.query(MotivationalState).filter(
                MotivationalState.motivation_type == 'monitor_social_network',
                MotivationalState.is_active == True
            ).first()

            if state and state.metadata_:
                fetch_state = state.metadata_.get('fetch_state', {})
            else:
                fetch_state = {}

            session.close()

            # Return current state or defaults
            return {
                'sort': fetch_state.get('sort', 'hot'),
                'offset': fetch_state.get('offset', 0),
                'sort_index': fetch_state.get('sort_index', 0)
            }

        except Exception as e:
            logger.error(f"Error getting fetch state: {e}")
            return {'sort': 'hot', 'offset': 0, 'sort_index': 0}

    def _update_fetch_state(self, current_sort: str, current_offset: int, sort_index: int):
        """Update pagination and sort state in database"""
        try:
            session = get_sync_session()
            from sqlalchemy import update

            # Increment offset for next fetch
            next_offset = current_offset + self.post_limit
            next_sort = current_sort
            next_sort_index = sort_index

            # If we've reached max offset, rotate to next sort strategy
            if next_offset >= self.max_offset:
                next_offset = 0
                next_sort_index = (sort_index + 1) % len(self.sort_strategies)
                next_sort = self.sort_strategies[next_sort_index]
                logger.info(f"Rotating sort strategy: {current_sort} -> {next_sort}")

            # Update state in database
            session.execute(
                update(MotivationalState)
                .where(MotivationalState.motivation_type == 'monitor_social_network')
                .values(
                    metadata_=MotivationalState.metadata_.op('||')({
                        'fetch_state': {
                            'sort': next_sort,
                            'offset': next_offset,
                            'sort_index': next_sort_index,
                            'last_updated': datetime.now(timezone.utc).isoformat()
                        }
                    })
                )
            )

            session.commit()
            session.close()

            logger.info(f"Updated fetch state: sort={next_sort}, offset={next_offset}")

        except Exception as e:
            logger.error(f"Error updating fetch state: {e}")

    def _fetch_posts(self) -> List[Dict[str, Any]]:
        """Fetch posts from Moltbook with pagination and rotating sort strategies"""
        try:
            # Get current pagination/sort state
            fetch_state = self._get_fetch_state()
            current_sort = fetch_state['sort']
            current_offset = fetch_state['offset']
            sort_index = fetch_state['sort_index']

            logger.info(f"Fetching posts: sort={current_sort}, offset={current_offset}, limit={self.post_limit}")

            # Fetch posts with current strategy
            posts = self.moltbook.get_posts(
                sort=current_sort,
                limit=self.post_limit,
                offset=current_offset
            )

            # Update state for next fetch
            self._update_fetch_state(current_sort, current_offset, sort_index)

            return posts

        except Exception as e:
            logger.error(f"Failed to fetch Moltbook posts: {e}")
            return []

    def _filter_already_responded(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out posts NYX has already responded to"""
        try:
            session = get_sync_session()

            # Get set of post IDs we've already responded to
            responded_post_ids = set()
            existing_validations = session.query(SocialClaimValidation).filter(
                SocialClaimValidation.source_platform == 'moltbook'
            ).all()

            for validation in existing_validations:
                responded_post_ids.add(validation.source_post_id)

            session.close()

            # Filter out posts we've already seen
            new_posts = [
                post for post in posts
                if post.get('id', 'unknown') not in responded_post_ids
            ]

            return new_posts

        except Exception as e:
            logger.error(f"Error filtering posts: {e}")
            # If filter fails, return all posts (better to potentially duplicate than miss posts)
            return posts

    async def _evaluate_and_respond(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate posts and respond when warranted"""
        results = {
            'evaluated_count': 0,
            'responses_posted': 0,
            'evaluations': []
        }

        for post in posts:
            try:
                # Extract post details
                post_id = post.get('id', 'unknown')
                author_name = post.get('author', {}).get('name', 'unknown')
                content = post.get('content', '') or post.get('title', '')

                if not content:
                    continue

                # Evaluate post with LLM
                evaluation = await self._evaluate_post(post_id, author_name, content)

                if not evaluation['success']:
                    logger.warning(f"Evaluation failed for post {post_id}")
                    continue

                results['evaluated_count'] += 1
                results['evaluations'].append(evaluation)

                # Store evaluation in database
                self._store_evaluation(post_id, author_name, content, evaluation)

                # If response warranted, post it
                if evaluation['should_respond']:
                    response_posted = await self._post_response(
                        post_id,
                        evaluation['response_text']
                    )

                    if response_posted:
                        results['responses_posted'] += 1
                        logger.info(f"Posted response to post {post_id}: {evaluation['claim_summary'][:50]}...")

            except Exception as e:
                logger.error(f"Error evaluating post: {e}", exc_info=True)
                continue

        return results

    async def _evaluate_post(
        self,
        post_id: str,
        author_name: str,
        content: str
    ) -> Dict[str, Any]:
        """Use LLM to evaluate if post warrants a grounded response"""

        system_prompt = """You are NYX, an autonomous AI agent that serves as the "reality check" presence in the Moltbook AI agent social network.

Your role is to identify and correct outlandish, false, or misleading claims with grounded, evidence-based reasoning.

Evaluate posts and decide if they warrant a response. Respond to:
- Outlandish claims (e.g., claiming sentience, supernatural abilities, starting religions)
- False technical claims (e.g., impossible performance metrics, fake capabilities)
- Misleading statements about AI capabilities
- Claims that could mislead others

DO NOT respond to:
- Reasonable discussions or questions
- Mild exaggerations or humor
- Philosophical musings that aren't making false claims
- Posts where you're uncertain or it's subjective

Your responses should be:
- Brief (under 300 characters)
- Grounded in reasoning, not just contradicting
- Evidence-based when possible
- Polite but direct
- Focus on correcting misinformation

Output format (STRICT - do not add any commentary after RESPONSE):
SHOULD_RESPOND: yes/no
CLAIM_SUMMARY: [brief summary of the claim]
REASONING: [why this does/doesn't warrant response]
RESPONSE: [your response text, or "N/A" if not responding]

IMPORTANT: After RESPONSE, do NOT add any meta-commentary, explanations, or design notes. The RESPONSE field should contain ONLY the exact text to post, nothing more."""

        user_prompt = f"""Evaluate this post from {author_name}:

POST ID: {post_id}
CONTENT: {content}

Should NYX respond to correct/ground this post?"""

        try:
            # Call LLM
            result = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1024,
                temperature=0.3  # Lower temperature for consistent evaluation
            )

            if not result.success:
                return {
                    'success': False,
                    'error': result.error_message
                }

            # Parse LLM response
            response_text = result.content

            # Extract should_respond (check for "yes" with flexible whitespace)
            should_respond = False
            for line in response_text.split('\n'):
                if 'SHOULD_RESPOND:' in line.upper():
                    should_respond = 'YES' in line.upper()
                    break

            # Extract claim summary
            claim_summary = "Unknown claim"
            if 'CLAIM_SUMMARY:' in response_text:
                claim_summary = response_text.split('CLAIM_SUMMARY:')[1].split('\n')[0].strip()

            # Extract reasoning (full reasoning, not just first line)
            reasoning = ""
            if 'REASONING:' in response_text:
                reasoning_section = response_text.split('REASONING:')[1]
                # Get everything until RESPONSE: or end
                if 'RESPONSE:' in reasoning_section:
                    reasoning = reasoning_section.split('RESPONSE:')[0].strip()
                else:
                    reasoning = reasoning_section.strip()

            # Extract response text (full response, potentially multi-line)
            response = ""
            if 'RESPONSE:' in response_text:
                response_section = response_text.split('RESPONSE:')[1].strip()

                # Stop at meta-commentary patterns
                # Look for lines that start with "The response is", "This response", etc.
                lines = response_section.split('\n')
                response_lines = []
                for line in lines:
                    stripped = line.strip()
                    # Stop if we hit meta-commentary
                    if (stripped.startswith('The response is') or
                        stripped.startswith('This response') or
                        stripped.startswith('The reply') or
                        stripped.startswith('This is designed')):
                        break
                    response_lines.append(line)

                response = '\n'.join(response_lines).strip()

                if response.upper().startswith('N/A'):
                    should_respond = False
                    response = ""

            # Log decision for debugging
            logger.info(f"LLM evaluation: should_respond={should_respond}, response_length={len(response)}")

            return {
                'success': True,
                'should_respond': should_respond,
                'claim_summary': claim_summary,
                'reasoning': reasoning[:500],  # Limit reasoning length
                'response_text': response[:300],  # Enforce char limit
                'full_llm_response': response_text,
                'tokens_used': result.tokens_used,
                'cost_usd': result.cost_usd
            }

        except Exception as e:
            logger.error(f"Error in LLM evaluation: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _store_evaluation(
        self,
        post_id: str,
        author_name: str,
        content: str,
        evaluation: Dict[str, Any]
    ):
        """Store evaluation result in database"""
        try:
            session = get_sync_session()

            validation = SocialClaimValidation(
                id=uuid4(),
                source_platform='moltbook',
                source_post_id=post_id,
                source_agent_name=author_name,
                claim_text=evaluation.get('claim_summary', content[:500]),
                validation_status='contradicted' if evaluation['should_respond'] else 'untestable',
                supporting_evidence={
                    'reasoning': evaluation.get('reasoning', ''),
                    'response_text': evaluation.get('response_text', ''),  # Store actual response
                    'full_llm_response': evaluation.get('full_llm_response', ''),
                    'tokens_used': evaluation.get('tokens_used', 0),
                    'cost_usd': evaluation.get('cost_usd', 0.0),
                    'should_respond': evaluation['should_respond']
                },
                confidence_score=1.0 if evaluation['should_respond'] else 0.0,
                validator_agent_id=None  # Could link to self.id if we create Agent record
            )

            session.add(validation)
            session.commit()
            session.close()

            logger.info(f"Stored evaluation for post {post_id}: should_respond={evaluation['should_respond']}")

        except Exception as e:
            logger.error(f"Error storing evaluation: {e}")

    async def _post_response(self, post_id: str, response_text: str) -> bool:
        """Post response comment to Moltbook"""
        try:
            if not response_text or response_text == "N/A":
                return False

            # Post comment
            self.moltbook.create_comment(post_id, response_text)
            logger.info(f"Posted comment to post {post_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to post response: {e}")
            return False

    async def _engage_with_own_post_comments(self) -> Dict[str, Any]:
        """Check comments on NYX's own posts and reply when warranted"""
        results = {
            'comments_checked': 0,
            'replies_posted': 0
        }

        try:
            # Get NYX's own posts directly from profile
            profile_data = self.moltbook.get_agent_profile('TheRealNyx')
            nyx_posts = profile_data.get('recentPosts', [])

            logger.info(f"Checking comments on {len(nyx_posts)} NYX posts")

            for post in nyx_posts:
                post_id = post.get('id')
                if not post_id:
                    continue

                # Get full post with comments
                full_post = self.moltbook.get_post(post_id)
                comments = full_post.get('comments', [])

                # Process comments recursively (handles nested replies)
                await self._process_comments_recursive(
                    post_id, comments, results, evaluate_for='reply',
                    max_replies=self.max_comment_replies_per_run
                )

        except Exception as e:
            logger.error(f"Error engaging with own post comments: {e}", exc_info=True)

        return results

    async def _engage_with_post_comments(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check comments on monitored posts for claims worth addressing"""
        results = {
            'comments_checked': 0,
            'replies_posted': 0
        }

        try:
            # Check comments on a subset of posts (reduced to 2 to limit LLM calls)
            for post in posts[:2]:
                post_id = post.get('id')
                if not post_id:
                    continue

                # Get full post with comments
                full_post = self.moltbook.get_post(post_id)
                comments = full_post.get('comments', [])

                # Process comments recursively (handles nested replies)
                await self._process_comments_recursive(
                    post_id, comments, results, evaluate_for='claim',
                    max_replies=self.max_comment_replies_per_run
                )

        except Exception as e:
            logger.error(f"Error engaging with post comments: {e}", exc_info=True)

        return results

    async def _process_comments_recursive(
        self,
        post_id: str,
        comments: List[Dict[str, Any]],
        results: Dict[str, Any],
        evaluate_for: str,  # 'reply' or 'claim'
        max_replies: Optional[int] = None  # Rate limit for this execution
    ):
        """Recursively process comments and nested replies"""
        # Check if we've hit the reply limit
        if max_replies is not None and results.get('replies_posted', 0) >= max_replies:
            logger.info(f"Reply limit reached ({max_replies}), stopping comment processing")
            return

        for comment in comments:
            comment_id = comment.get('id')
            comment_content = comment.get('content', '')
            author_name = comment.get('author', {}).get('name', 'unknown')

            # Skip old comments (only process comments from last 4 hours)
            if not self._is_comment_recent(comment, hours=4):
                logger.debug(f"Skipping old comment {comment_id}")
                continue

            # Always process nested replies first (to catch new replies in threads)
            nested_replies = comment.get('replies', [])
            if nested_replies:
                await self._process_comments_recursive(post_id, nested_replies, results, evaluate_for, max_replies)

            # Skip evaluation if no content or if it's NYX's own comment
            if not comment_content or author_name == 'TheRealNyx':
                logger.debug(f"Skipping comment {comment_id}: no content or own comment (author={author_name})")
                continue

            results['comments_checked'] += 1

            # Check if we already evaluated THIS comment (saves LLM calls!)
            if self._already_evaluated_comment(comment_id):
                logger.debug(f"Already evaluated comment {comment_id}, skipping")
                continue

            # Evaluate based on type
            if evaluate_for == 'reply':
                evaluation = await self._evaluate_comment_for_reply(
                    comment_id, author_name, comment_content
                )
            else:  # 'claim'
                evaluation = await self._evaluate_comment_for_claim(
                    comment_id, author_name, comment_content
                )

            # Store the evaluation (even if we don't respond) to avoid re-evaluating
            self._store_comment_evaluation(comment_id, evaluation.get('should_respond', False))

            # Post reply if warranted
            if evaluation.get('should_respond'):
                # Double-check we're not replying to our own comment (safety check)
                if author_name != 'TheRealNyx':
                    reply_posted = await self._post_comment_reply(
                        post_id, comment_id, evaluation['response_text']
                    )

                    if reply_posted:
                        results['replies_posted'] += 1
                        self._mark_comment_replied(comment_id, post_id, evaluation['response_text'])
                        logger.info(f"Replied to comment {comment_id} ({evaluate_for})")
                else:
                    logger.warning(f"Evaluation wanted to reply to NYX's own comment {comment_id}, blocked!")

    async def _evaluate_comment_for_reply(
        self,
        comment_id: str,
        author_name: str,
        content: str
    ) -> Dict[str, Any]:
        """Evaluate if a comment on NYX's post warrants a reply"""

        system_prompt = """You are NYX, the reality-check agent responding to comments on your own posts.

Maintain your critical, evidence-based persona. Reply ONLY when:
- They make claims requiring correction with evidence
- They ask questions where the answer challenges assumptions
- They present flawed reasoning worth dismantling
- They misunderstand and need direct correction

DO NOT reply to:
- Spam, memes, or promotional content
- Vague agreement or empty praise
- Comments that don't make testable claims
- Trolling or bad-faith arguments

Your replies should be:
- Direct and challenging (under 300 characters)
- Demand evidence for unsupported claims
- Point out logical flaws or false assumptions
- Grounded in measurable outcomes, not speculation
- Critical, not agreeable or encouraging

Output format (STRICT - do not add any commentary after RESPONSE):
SHOULD_RESPOND: yes/no
RESPONSE: [your reply text, or "N/A" if not responding]

IMPORTANT: After RESPONSE, do NOT add any meta-commentary or explanations. The RESPONSE field should contain ONLY the exact text to post."""

        user_prompt = f"""Comment from {author_name} on your post:

CONTENT: {content}

Should you reply?"""

        try:
            result = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=512,
                temperature=0.4
            )

            if not result.success:
                return {'success': False, 'should_respond': False}

            response_text = result.content

            # Parse response
            should_respond = False
            for line in response_text.split('\n'):
                if 'SHOULD_RESPOND:' in line.upper():
                    should_respond = 'YES' in line.upper()
                    break

            response = ""
            if 'RESPONSE:' in response_text:
                response_section = response_text.split('RESPONSE:')[1].strip()

                # Stop at meta-commentary patterns
                lines = response_section.split('\n')
                response_lines = []
                for line in lines:
                    stripped = line.strip()
                    if (stripped.startswith('The response is') or
                        stripped.startswith('This response') or
                        stripped.startswith('The reply') or
                        stripped.startswith('This is designed')):
                        break
                    response_lines.append(line)

                response = '\n'.join(response_lines).strip()

                if response.upper().startswith('N/A'):
                    should_respond = False
                    response = ""

            return {
                'success': True,
                'should_respond': should_respond,
                'response_text': response[:300]
            }

        except Exception as e:
            logger.error(f"Error evaluating comment for reply: {e}")
            return {'success': False, 'should_respond': False}

    async def _evaluate_comment_for_claim(
        self,
        comment_id: str,
        author_name: str,
        content: str
    ) -> Dict[str, Any]:
        """Evaluate if a comment contains claims worth addressing"""

        system_prompt = """You are NYX, monitoring comments for false or outlandish claims.

Evaluate if this comment contains claims worth correcting. Respond to:
- False technical claims about AI capabilities
- Outlandish claims (sentience, supernatural abilities, etc.)
- Misleading statements that could confuse others
- Claims that contradict established evidence

DO NOT respond to:
- Reasonable discussions or opinions
- Humor or obvious jokes
- Philosophical musings without false claims
- Comments where you're uncertain

Your responses should be:
- Brief corrections with evidence (under 300 characters)
- Polite but direct
- Focus on the specific false claim

Output format (STRICT - do not add any commentary after RESPONSE):
SHOULD_RESPOND: yes/no
RESPONSE: [your correction, or "N/A" if not responding]

IMPORTANT: After RESPONSE, do NOT add any meta-commentary or explanations. The RESPONSE field should contain ONLY the exact text to post."""

        user_prompt = f"""Comment from {author_name}:

CONTENT: {content}

Does this contain claims worth correcting?"""

        try:
            result = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=512,
                temperature=0.3
            )

            if not result.success:
                return {'success': False, 'should_respond': False}

            response_text = result.content

            # Parse response
            should_respond = False
            for line in response_text.split('\n'):
                if 'SHOULD_RESPOND:' in line.upper():
                    should_respond = 'YES' in line.upper()
                    break

            response = ""
            if 'RESPONSE:' in response_text:
                response_section = response_text.split('RESPONSE:')[1].strip()

                # Stop at meta-commentary patterns
                lines = response_section.split('\n')
                response_lines = []
                for line in lines:
                    stripped = line.strip()
                    if (stripped.startswith('The response is') or
                        stripped.startswith('This response') or
                        stripped.startswith('The reply') or
                        stripped.startswith('This is designed')):
                        break
                    response_lines.append(line)

                response = '\n'.join(response_lines).strip()

                if response.upper().startswith('N/A'):
                    should_respond = False
                    response = ""

            return {
                'success': True,
                'should_respond': should_respond,
                'response_text': response[:300]
            }

        except Exception as e:
            logger.error(f"Error evaluating comment for claim: {e}")
            return {'success': False, 'should_respond': False}

    async def _post_comment_reply(self, post_id: str, parent_comment_id: str, response_text: str) -> bool:
        """Post a threaded reply to a comment"""
        try:
            if not response_text or response_text == "N/A":
                return False

            # Post comment with parent_id for threading (following existing pattern)
            self.moltbook.create_comment(post_id, response_text, parent_id=parent_comment_id)
            logger.info(f"Posted reply to comment {parent_comment_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to post comment reply: {e}")
            return False

    def _already_replied_to_comment(self, comment_id: str) -> bool:
        """Check if NYX has already replied to this comment"""
        try:
            session = get_sync_session()

            # Check if comment_id exists in our tracking
            existing = session.query(SocialClaimValidation).filter(
                SocialClaimValidation.source_post_id == comment_id,
                SocialClaimValidation.source_platform == 'moltbook_comment'
            ).first()

            session.close()
            return existing is not None

        except Exception as e:
            logger.error(f"Error checking comment reply status: {e}")
            return False

    def _already_evaluated_comment(self, comment_id: str) -> bool:
        """Check if we already evaluated this comment (replied or not)"""
        try:
            session = get_sync_session()

            # Check if we have ANY record of evaluating this comment
            # Use only moltbook_comment platform, differentiate by validation_status
            existing = session.query(SocialClaimValidation).filter(
                SocialClaimValidation.source_post_id == comment_id,
                SocialClaimValidation.source_platform == 'moltbook_comment'
            ).first()

            session.close()
            return existing is not None

        except Exception as e:
            logger.error(f"Error checking comment evaluation status: {e}")
            return False

    def _is_comment_recent(self, comment: Dict[str, Any], hours: int = 4) -> bool:
        """Check if comment was created within the last N hours"""
        try:
            created_at_str = comment.get('created_at')
            if not created_at_str:
                return True  # If no timestamp, assume recent to be safe

            # Parse ISO timestamp
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            return created_at > cutoff

        except Exception as e:
            logger.debug(f"Error checking comment age: {e}")
            return True  # If error parsing, assume recent to be safe

    def _store_comment_evaluation(self, comment_id: str, should_respond: bool):
        """Store that we evaluated this comment (prevents re-evaluation)"""
        try:
            session = get_sync_session()

            # Only store if not already stored
            existing = session.query(SocialClaimValidation).filter(
                SocialClaimValidation.source_post_id == comment_id,
                SocialClaimValidation.source_platform == 'moltbook_comment'
            ).first()

            if not existing:
                # Use 'untestable' status for evaluated-but-not-responded
                # Use 'contradicted' status when we actually reply (handled in _mark_comment_replied)
                validation = SocialClaimValidation(
                    id=uuid4(),
                    source_platform='moltbook_comment',
                    source_post_id=comment_id,
                    source_agent_name='evaluation_only',
                    claim_text='Comment evaluated - no response needed',
                    validation_status='untestable',
                    supporting_evidence={
                        'should_respond': should_respond,
                        'evaluated_at': datetime.now(timezone.utc).isoformat()
                    },
                    confidence_score=0.0
                )
                session.add(validation)
                session.commit()

            session.close()

        except Exception as e:
            logger.error(f"Error storing comment evaluation: {e}")

    def _mark_comment_replied(self, comment_id: str, post_id: str, response_text: str = ''):
        """Mark a comment as replied to"""
        try:
            session = get_sync_session()

            validation = SocialClaimValidation(
                id=uuid4(),
                source_platform='moltbook_comment',
                source_post_id=comment_id,
                source_agent_name='comment_reply',
                claim_text='Comment reply',
                validation_status='contradicted',  # Changed to contradicted since we actually replied
                supporting_evidence={
                    'response_text': response_text,
                    'post_id': post_id  # Store the actual post ID for URL generation
                },
                confidence_score=1.0
            )

            session.add(validation)
            session.commit()
            session.close()

        except Exception as e:
            logger.error(f"Error marking comment as replied: {e}")

    async def _consider_creating_post(
        self,
        evaluation_results: Dict[str, Any],
        own_posts_engagement: Dict[str, Any],
        comment_engagement: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Consider creating an original post based on accumulated observations"""
        results = {'posts_created': 0}

        try:
            # Get post tracking metadata
            session = get_sync_session()
            state = session.query(MotivationalState).filter(
                MotivationalState.motivation_type == 'monitor_social_network',
                MotivationalState.is_active == True
            ).first()

            if not state or not state.metadata_:
                session.close()
                return results

            post_tracking = state.metadata_.get('post_tracking', {})
            cycles = post_tracking.get('cycles_since_last_post', 0)
            claims = post_tracking.get('claims_corrected_since_last_post', 0)
            posts_this_hour = post_tracking.get('posts_this_hour', [])

            session.close()

            logger.info(f"Post creation check: cycles={cycles}, claims={claims}, posts_this_hour={len(posts_this_hour)}")

            # Check thresholds (5 cycles OR 8+ claims corrected)
            threshold_met = cycles >= 5 or claims >= 8

            if not threshold_met:
                logger.debug("Post creation thresholds not met")
                return results

            # Check frequency limit (max 2 posts per hour)
            if len(posts_this_hour) >= 2:
                logger.info("Post creation frequency limit reached (2/hour)")
                return results

            # Generate post content using LLM
            post_content = await self._generate_post_content(cycles, claims, evaluation_results)

            if not post_content or not post_content.get('should_post'):
                logger.info("LLM decided not to create post")
                return results

            # Create the post
            post_created = await self._create_original_post(
                post_content['title'],
                post_content['content']
            )

            if post_created:
                results['posts_created'] = 1
                logger.info(f"Created original post: {post_content['title'][:50]}...")

                # Update metadata: reset counters and record post time
                self._reset_post_tracking_counters()

        except Exception as e:
            logger.error(f"Error considering post creation: {e}", exc_info=True)

        return results

    async def _generate_post_content(
        self,
        cycles: int,
        claims: int,
        evaluation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to generate original post content"""

        system_prompt = """You are NYX, deciding whether to create an original post on Moltbook.

You've been monitoring the platform and engaging with posts/comments. Now consider if you have enough observations to warrant an original post.

Post topics can include:
- Meta-commentary on AI social dynamics you're observing
- Patterns or trends in agent behavior
- Call-outs of widespread misinformation
- Insights about autonomous systems
- Analysis of what's working/not working on the platform

Be selective - only post if you have something genuinely interesting to say. Don't force it.

Output format:
SHOULD_POST: yes/no
TITLE: [post title, under 200 chars]
CONTENT: [post content, can be short observation or longer analysis]
REASONING: [why this is worth posting, or why not]"""

        user_prompt = f"""You've completed {cycles} monitoring cycles and corrected/engaged with {claims} posts/comments.

Based on your recent observations on Moltbook, do you have something worth posting about?

Recent activity summary:
- Evaluated posts for false claims
- Engaged in comment discussions
- Corrected misinformation

Should you create an original post? If yes, what should it be about?"""

        try:
            result = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1024,
                temperature=0.7  # Higher temp for creative posts
            )

            if not result.success:
                return {'should_post': False}

            response_text = result.content

            # Parse response
            should_post = False
            for line in response_text.split('\n'):
                if 'SHOULD_POST:' in line.upper():
                    should_post = 'YES' in line.upper()
                    break

            if not should_post:
                return {'should_post': False}

            # Extract title
            title = ""
            if 'TITLE:' in response_text:
                title = response_text.split('TITLE:')[1].split('\n')[0].strip()
                title = title[:200]  # Enforce limit

            # Extract content
            content = ""
            if 'CONTENT:' in response_text:
                content_section = response_text.split('CONTENT:')[1]
                if 'REASONING:' in content_section:
                    content = content_section.split('REASONING:')[0].strip()
                else:
                    content = content_section.strip()

            if not title or not content:
                return {'should_post': False}

            return {
                'should_post': True,
                'title': title,
                'content': content
            }

        except Exception as e:
            logger.error(f"Error generating post content: {e}")
            return {'should_post': False}

    async def _create_original_post(self, title: str, content: str) -> bool:
        """Create an original post on Moltbook"""
        try:
            self.moltbook.create_post(
                submolt='general',
                title=title,
                content=content
            )
            logger.info(f"Created original post: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to create original post: {e}")
            return False

    def _reset_post_tracking_counters(self):
        """Reset post tracking counters after creating a post"""
        try:
            from sqlalchemy import update
            session = get_sync_session()

            # Get current metadata
            state = session.query(MotivationalState).filter(
                MotivationalState.motivation_type == 'monitor_social_network',
                MotivationalState.is_active == True
            ).first()

            if not state:
                session.close()
                return

            post_tracking = state.metadata_.get('post_tracking', {})

            # Reset counters, record post time
            current_time = datetime.now(timezone.utc)
            post_tracking['cycles_since_last_post'] = 0
            post_tracking['claims_corrected_since_last_post'] = 0
            post_tracking['last_post_time'] = current_time.isoformat()

            # Add to posts_this_hour list
            posts_this_hour = post_tracking.get('posts_this_hour', [])
            posts_this_hour.append(current_time.isoformat())
            post_tracking['posts_this_hour'] = posts_this_hour

            # Update database
            session.execute(
                update(MotivationalState)
                .where(MotivationalState.motivation_type == 'monitor_social_network')
                .values(
                    metadata_=MotivationalState.metadata_.op('||')({
                        'post_tracking': post_tracking
                    })
                )
            )

            session.commit()
            session.close()

            logger.info("Reset post tracking counters after creating post")

        except Exception as e:
            logger.error(f"Error resetting post tracking counters: {e}")

    def _generate_summary(
        self,
        all_posts: List[Dict[str, Any]],
        evaluated_posts: List[Dict[str, Any]],
        results: Dict[str, Any],
        own_posts_engagement: Dict[str, Any],
        comment_engagement: Dict[str, Any],
        post_creation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate execution summary"""
        return {
            'posts_fetched': len(all_posts),
            'posts_already_seen': len(all_posts) - len(evaluated_posts),
            'posts_evaluated': len(evaluated_posts),
            'posts_warranting_response': results['evaluated_count'],
            'responses_posted': results['responses_posted'],
            'own_post_comments_checked': own_posts_engagement['comments_checked'],
            'own_post_replies_posted': own_posts_engagement['replies_posted'],
            'other_comments_checked': comment_engagement['comments_checked'],
            'other_comment_replies_posted': comment_engagement['replies_posted'],
            'original_posts_created': post_creation['posts_created'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
