import hashlib
from typing import Dict, List, Optional, Tuple
from django.core.cache import cache
from django.utils import timezone
import re


class MediaPaginationManager:
    CACHE_PREFIX = "media_pagination"
    CACHE_TIMEOUT = 60 * 60 * 24
    ITEMS_PER_PAGE = 3

    def __init__(self):
        pass

    def _get_cache_key(self, user_id: int, query: str, media_type: str) -> str:
        normalized_query = query.lower().strip()
        query_hash = hashlib.md5(
            normalized_query.encode('utf-8')
        ).hexdigest()[:16]
        return (
            f"{self.CACHE_PREFIX}:{user_id}:"
            f"{media_type}:{query_hash}"
        )

    def get_pagination_state(self, user_id: int, query: str, media_type: str) -> Optional[Dict]:
        cache_key = self._get_cache_key(user_id, query, media_type)
        return cache.get(cache_key)

    def save_pagination_state(
        self,
        user_id: int,
        query: str,
        media_type: str,
        shown_items: List[str],
        total_available: int,
        current_offset: int
    ) -> None:
        cache_key = self._get_cache_key(user_id, query, media_type)

        state = {
            'shown_items': shown_items,
            'total_available': total_available,
            'current_offset': current_offset,
            'last_updated': timezone.now().isoformat(),
            'query': query,
            'media_type': media_type
        }

        cache.set(cache_key, state, self.CACHE_TIMEOUT)

        print(
            f"Saved pagination state: {len(shown_items)} items "
            f"shown, offset {current_offset}"
        )

    def record_shown_items(
        self,
        user_id: int,
        query: str,
        media_type: str,
        items: List[Dict],
        is_initial: bool = True
    ) -> None:
        if media_type == 'video':
            item_ids = [
                item.get('video_id', '') for item in items
                if item.get('video_id')
            ]
        else:
            item_ids = [
                item.get('url', '') for item in items
                if item.get('url')
            ]

        state = self.get_pagination_state(user_id, query, media_type)

        if state is None or is_initial:
            shown_items = item_ids
            current_offset = len(item_ids)
        else:
            shown_items = state['shown_items'] + item_ids
            current_offset = state['current_offset'] + len(item_ids)

        self.save_pagination_state(
            user_id=user_id,
            query=query,
            media_type=media_type,
            shown_items=shown_items,
            total_available=current_offset,
            current_offset=current_offset
        )

    def get_next_batch(
        self,
        user_id: int,
        query: str,
        media_type: str,
        all_available_items: List[Dict]
    ) -> Tuple[List[Dict], bool]:
        state = self.get_pagination_state(user_id, query, media_type)

        if state is None:
            next_batch = all_available_items[:self.ITEMS_PER_PAGE]
            has_more = len(all_available_items) > self.ITEMS_PER_PAGE
            return next_batch, has_more

        shown_ids = set(state['shown_items'])

        if media_type == 'video':
            unseen_items = [
                item for item in all_available_items
                if item.get('video_id') not in shown_ids
            ]
        else:
            unseen_items = [
                item for item in all_available_items
                if item.get('url') not in shown_ids
            ]

        next_batch = unseen_items[:self.ITEMS_PER_PAGE]
        has_more = len(unseen_items) > self.ITEMS_PER_PAGE

        print(
            f"Pagination: {len(shown_ids)} shown, "
            f"{len(unseen_items)} unseen, returning {len(next_batch)}"
        )

        return next_batch, has_more

    def clear_all_user_states(self, user_id: int) -> None:
        user_keys_key = f"{self.CACHE_PREFIX}:user_keys:{user_id}"
        user_keys = cache.get(user_keys_key, [])

        for cache_key in user_keys:
            cache.delete(cache_key)

        cache.delete(user_keys_key)
        print(f"Cleared all pagination states for user {user_id}")


def detect_more_request(user_message: str) -> bool:
    msg_lower = user_message.lower().strip()

    more_patterns = [
        r"^more\?*$",
        r"^are there more\?*$",
        r"^any more\?*$",
        r"^got more\?*$",
        r"^show me more",
        r"^give me more",
        r"^more (videos|images|of (these|those|them))",
        r"^another (one|video|image)",
        r"^what else",
        r"^anything else",
        r"^other (videos|images|options)",
        r"^(show|get|find) (me )?(some )?(other|more|another)",
    ]

    if any(re.search(pattern, msg_lower) for pattern in more_patterns):
        return True

    if msg_lower in ["more", "more?", "more!", "another", "another?"]:
        return True

    return False


def generate_more_response_message(
    has_items: bool,
    item_count: int,
    has_more: bool,
    media_type: str,
    query: str
) -> Tuple[str, str]:
    media_word = f"{media_type}s"

    if not has_items:
        intro = f"I don't have additional {media_word} at the moment."
        outro = (
            "Feel free to explore the ones I shared earlier, "
            "or ask about a different topic!"
        )
        return intro, outro

    if item_count == 1:
        intro = f"Here's another {media_type} about {query}:"
    else:
        intro = f"Here are {item_count} more {media_word} about {query}:"

    if has_more:
        outro = f"Let me know if you'd like to see even more {media_word}!"
    else:
        outro = (
            f"That's all the {media_word} I have for now on this topic. "
            "Feel free to ask about something else!"
        )

    return intro, outro


def generate_no_previous_media_fallback(
    media_type: str = None, count: int = 3
) -> str:
    if media_type == "video":
        if count == 1:
            return (
                "I couldn't find a video on that topic right now. "
                "Feel free to try a different search term if you'd like!"
            )
        else:
            return (
                "I couldn't find videos on that topic at the moment. "
                "You're welcome to search for something else if you'd "
                "like to explore other content."
            )
    elif media_type == "image":
        if count == 1:
            return (
                "I wasn't able to find an image for that search. "
                "If you'd like, you can try a different topic!"
            )
        else:
            return (
                "I couldn't find images on that topic right now. "
                "Feel free to search for something different if you're "
                "interested in other visuals."
            )
    else:
        return (
            "I don't have a previous search to show more from. "
            "Try asking for videos or images about a specific topic!"
        )


def generate_no_results_fallback(
    query: str, media_type: str, count: int = 3
) -> str:
    if media_type == "video":
        if count == 1:
            return (
                "I couldn't find a video on that topic right now. "
                "Feel free to try a different search term if you'd like!"
            )
        else:
            return (
                "I couldn't find videos on that topic at the moment. "
                "You're welcome to search for something else if you'd "
                "like to explore other content."
            )
    elif media_type == "image":
        if count == 1:
            return (
                "I wasn't able to find an image for that search. "
                "If you'd like, you can try a different topic!"
            )
        else:
            return (
                "I couldn't find images on that topic right now. "
                "Feel free to search for something different if you're "
                "interested in other visuals."
            )
    else:
        return (
            f"I couldn't find any {media_type}s about that topic. "
            "Could you try a different search term?"
        )