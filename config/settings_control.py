
from .settings_test import *

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_PAGINATION_CLASS": None,
    "PAGE_SIZE": None,
}
