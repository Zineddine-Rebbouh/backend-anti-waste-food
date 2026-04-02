"""
Pagination classes for SaveFood DZ API.
"""

from rest_framework.pagination import CursorPagination, PageNumberPagination


class CustomCursorPagination(CursorPagination):
    """
    Cursor-based pagination for mobile clients.
    Provides stable pagination even with frequently changing datasets.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"


class AdminPageNumberPagination(PageNumberPagination):
    """
    Offset-based pagination for admin interfaces and internal tooling.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"
