from .base import *

DEBUG = False

# віддає статику (адмінка, restframework, swagger ui, ...) на проді, альтернатива nginx
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
