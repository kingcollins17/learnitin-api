from typing import Dict, Optional


class LessonAudioTracker:
    """
    Singleton service to track lessons currently undergoing audio generation.
    Used to prevent duplicate background tasks for the same lesson.
    """

    _instance: Optional["LessonAudioTracker"] = None
    _in_progress: Dict[int, int] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LessonAudioTracker, cls).__new__(cls)
        return cls._instance

    def start_tracking(self, lesson_id: int, user_id: int) -> bool:
        """
        Mark a lesson as having audio generation in progress for a user.
        Returns True if it was added, False if it was already in progress.
        """
        if lesson_id in self._in_progress:
            return False
        self._in_progress[lesson_id] = user_id
        return True

    def stop_tracking(self, lesson_id: int) -> Optional[int]:
        """
        Remove a lesson from the tracking dict and return the user_id.
        """
        return self._in_progress.pop(lesson_id, None)

    def is_in_progress(self, lesson_id: int) -> bool:
        """
        Check if audio generation is in progress for a lesson.
        """
        return lesson_id in self._in_progress


# Global singleton instance
audio_tracker = LessonAudioTracker()
