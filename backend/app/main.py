from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import search
from .config import settings

#
