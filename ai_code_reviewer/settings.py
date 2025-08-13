# ai_code_reviewer/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This tells Pydantic to load variables from a .env file
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    GITHUB_APP_ID: str
    GITHUB_WEBHOOK_SECRET: str

# Create a single, reusable instance of the settings
settings = Settings()

# print(settings.GITHUB_APP_ID)  # For debugging purposes, can be removed later
# print(settings.GITHUB_WEBHOOK_SECRET)  # For debugging purposes, can be removed later