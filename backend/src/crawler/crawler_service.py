"""Unified crawler service for lottery data.

This is a backward-compatibility re-export module. All real implementations
have been moved to:
- crawler.collectors  — HK/Macau data collection
- crawler.tasks       — scheduler task management
- crawler.scheduler   — CrawlerScheduler, auto-prediction, draw checks
"""

from crawler.scheduler import *  # noqa: F401, F403
