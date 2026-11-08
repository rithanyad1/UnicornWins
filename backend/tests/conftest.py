import os

# Keep the suite hermetic: environment variables take precedence over backend/.env,
# so real database or AI credentials there are never used by tests.
os.environ["SPACETIMEDB_DATABASE"] = ""
os.environ["SPACETIMEDB_TOKEN"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["APP_ENV"] = "development"
