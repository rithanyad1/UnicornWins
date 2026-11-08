import os

# Keep the suite hermetic: environment variables take precedence over backend/.env,
# so real database or AI credentials there are never used by tests.
os.environ["SPACETIMEDB_DATABASE"] = ""
os.environ["SPACETIMEDB_TOKEN"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["APP_ENV"] = "development"

# A copied backend/.env tunes thresholds for the hardware and turns the simulator off;
# pin the defaults the tests assume.
os.environ.update({
    "HIGH_TEMP_THRESHOLD": "35", "CRITICAL_TEMP_THRESHOLD": "40", "RECOVERY_TEMP_THRESHOLD": "32",
    "HIGH_HUMIDITY_THRESHOLD": "70", "VIBRATION_THRESHOLD": "0.7", "SIMULATION_ENABLED": "true",
})
