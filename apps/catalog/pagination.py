from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"  # client can ask ?page_size=24
    max_page_size = 100                  # but never more than 100