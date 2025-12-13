"""
Audiobookshelf API Client
Connects to ABS instance to pull user progress, listening history, library data
"""

import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ABSUser:
    id: str
    username: str
    type: str  # 'root', 'admin', 'user', 'guest'
    is_active: bool
    created_at: Optional[datetime] = None


@dataclass
class MediaProgress:
    id: str
    library_item_id: str
    episode_id: Optional[str]
    duration: float  # total duration in seconds
    progress: float  # 0.0 to 1.0
    current_time: float  # current position in seconds
    is_finished: bool
    last_update: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@dataclass
class ListeningSession:
    id: str
    user_id: str
    library_item_id: str
    episode_id: Optional[str]
    media_type: str
    duration: float
    play_count: int
    start_time: datetime
    current_time: float


class ABSClient:
    """Client for Audiobookshelf API"""

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        })
        self._server_info = None

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated request to ABS API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ABS API error: {e}")
            return None

    def test_connection(self) -> Dict[str, Any]:
        """Test connection and return server info"""
        try:
            # Try to get current user info
            data = self._request('GET', '/api/me')
            if data:
                return {
                    'success': True,
                    'username': data.get('username'),
                    'user_type': data.get('type'),
                    'server_version': self._get_server_version()
                }
            return {'success': False, 'error': 'Invalid response'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_server_version(self) -> Optional[str]:
        """Get ABS server version"""
        data = self._request('GET', '/status')
        if data:
            return data.get('serverVersion')
        return None

    # ========== User Management ==========

    def get_users(self) -> List[ABSUser]:
        """Get all users (admin only)"""
        data = self._request('GET', '/api/users')
        if not data or 'users' not in data:
            return []

        users = []
        for u in data['users']:
            users.append(ABSUser(
                id=u['id'],
                username=u['username'],
                type=u.get('type', 'user'),
                is_active=u.get('isActive', True),
                created_at=datetime.fromtimestamp(u['createdAt'] / 1000) if u.get('createdAt') else None
            ))
        return users

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get specific user details"""
        return self._request('GET', f'/api/users/{user_id}')

    # ========== Listening Progress ==========

    def get_user_listening_sessions(self, user_id: str) -> List[ListeningSession]:
        """Get all listening sessions for a user"""
        data = self._request('GET', f'/api/users/{user_id}/listening-sessions')
        if not data or 'sessions' not in data:
            return []

        sessions = []
        for s in data['sessions']:
            sessions.append(ListeningSession(
                id=s['id'],
                user_id=s.get('userId', user_id),
                library_item_id=s.get('libraryItemId', ''),
                episode_id=s.get('episodeId'),
                media_type=s.get('mediaType', 'book'),
                duration=s.get('timeListening', 0),
                play_count=s.get('playCount', 1),
                start_time=datetime.fromtimestamp(s['startedAt'] / 1000) if s.get('startedAt') else datetime.now(),
                current_time=s.get('currentTime', 0)
            ))
        return sessions

    def get_user_listening_stats(self, user_id: str) -> Optional[Dict]:
        """Get listening statistics for a user"""
        return self._request('GET', f'/api/users/{user_id}/listening-stats')

    def get_my_progress(self) -> List[Dict]:
        """Get current user's media progress"""
        data = self._request('GET', '/api/me')
        if data and 'mediaProgress' in data:
            return data['mediaProgress']
        return []

    def get_items_in_progress(self) -> List[Dict]:
        """Get items currently being listened to"""
        data = self._request('GET', '/api/me/items-in-progress')
        if data and 'libraryItems' in data:
            return data['libraryItems']
        return []

    # ========== Library Items ==========

    def get_libraries(self) -> List[Dict]:
        """Get all libraries"""
        data = self._request('GET', '/api/libraries')
        if data and 'libraries' in data:
            return data['libraries']
        return []

    def get_library_items(self, library_id: str, include_progress: bool = True,
                          limit: int = 0, page: int = 0) -> Dict:
        """Get items from a library with optional progress data"""
        params = {}
        if include_progress:
            params['include'] = 'progress'
        if limit > 0:
            params['limit'] = limit
            params['page'] = page

        return self._request('GET', f'/api/libraries/{library_id}/items', params=params) or {}

    def get_library_item(self, item_id: str, expanded: bool = True) -> Optional[Dict]:
        """Get single library item with full details"""
        params = {'expanded': 1} if expanded else {}
        return self._request('GET', f'/api/items/{item_id}', params=params)

    # ========== Aggregated Progress View ==========

    def get_all_user_progress(self) -> Dict[str, List[Dict]]:
        """
        Get progress for ALL users across the library.
        Returns: {user_id: [list of progress entries]}
        """
        users = self.get_users()
        all_progress = {}

        for user in users:
            user_data = self.get_user(user.id)
            if user_data and 'mediaProgress' in user_data:
                all_progress[user.id] = {
                    'username': user.username,
                    'progress': user_data['mediaProgress']
                }

        return all_progress

    def get_library_with_all_progress(self, library_id: str) -> List[Dict]:
        """
        Get all library items with progress from ALL users.
        Returns list of items with 'user_progress' dict attached.
        """
        # Get all users' progress
        all_progress = self.get_all_user_progress()

        # Build lookup: item_id -> {user_id: progress}
        progress_by_item = {}
        for user_id, data in all_progress.items():
            for p in data['progress']:
                item_id = p.get('libraryItemId')
                if item_id:
                    if item_id not in progress_by_item:
                        progress_by_item[item_id] = {}
                    progress_by_item[item_id][user_id] = {
                        'username': data['username'],
                        'progress': p.get('progress', 0),
                        'is_finished': p.get('isFinished', False),
                        'current_time': p.get('currentTime', 0),
                        'duration': p.get('duration', 0),
                        'last_update': p.get('lastUpdate')
                    }

        # Get library items
        items_data = self.get_library_items(library_id, include_progress=False, limit=0)
        items = items_data.get('results', [])

        # Attach progress to items
        for item in items:
            item_id = item.get('id')
            item['user_progress'] = progress_by_item.get(item_id, {})

            # Calculate summary stats
            progresses = item['user_progress']
            item['progress_summary'] = {
                'total_users_started': len(progresses),
                'users_finished': sum(1 for p in progresses.values() if p['is_finished']),
                'users_in_progress': sum(1 for p in progresses.values() if not p['is_finished'] and p['progress'] > 0),
                'untouched': len(progresses) == 0
            }

        return items

    def get_archivable_items(self, library_id: str, min_users_finished: int = 1) -> List[Dict]:
        """
        Get items that can be safely archived.
        An item is archivable if:
        - At least min_users_finished have completed it
        - No one is currently in progress
        """
        items = self.get_library_with_all_progress(library_id)
        archivable = []

        for item in items:
            summary = item.get('progress_summary', {})
            if (summary.get('users_finished', 0) >= min_users_finished and
                summary.get('users_in_progress', 0) == 0):
                archivable.append(item)

        return archivable

    def get_untouched_items(self, library_id: str) -> List[Dict]:
        """Get items no one has started listening to"""
        items = self.get_library_with_all_progress(library_id)
        return [item for item in items if item.get('progress_summary', {}).get('untouched', True)]
