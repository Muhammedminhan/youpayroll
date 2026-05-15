from decouple import config
from .base import *

DEBUG = config('DEBUG', cast=bool, default=True)
