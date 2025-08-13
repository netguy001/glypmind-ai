"""
Configuration Manager for GlyphMind AI
Handles all configuration loading, validation, and management
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class APIConfig(BaseModel):
    """API configuration model"""
    google_search_api_key: Optional[str] = None
    google_search_engine_id: Optional[str] = None
    youtube_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

class ServerConfig(BaseModel):
    """Server configuration model"""
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    workers: int = 1
    log_level: str = "info"

class UIConfig(BaseModel):
    """UI configuration model"""
    title: str = "🧠 GlyphMind AI"
    theme: str = "default"
    share: bool = False
    server_name: Optional[str] = None
    server_port: Optional[int] = 7860

class DatabaseConfig(BaseModel):
    """Database configuration model"""
    knowledge_base_path: str = "knowledge_base/kb.sqlite"
    ledger_path: str = "ledger/ledger.sqlite"
    cache_path: str = "cache/"
    
class EvolutionConfig(BaseModel):
    """Evolution engine configuration"""
    background_learning_enabled: bool = True
    learning_interval_minutes: int = 30
    max_concurrent_searches: int = 5
    auto_update_knowledge: bool = True

class GlyphMindConfig(BaseModel):
    """Main configuration model for GlyphMind AI"""
    api: APIConfig = Field(default_factory=APIConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    evolution: EvolutionConfig = Field(default_factory=EvolutionConfig)
    
class ConfigManager:
    """Manages configuration for GlyphMind AI"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.settings_file = self.config_dir / "settings.json"
        self.api_keys_file = self.config_dir / "api_keys.json"
        self.scheduler_file = self.config_dir / "scheduler.json"
        
        self._config: Optional[GlyphMindConfig] = None
        
    def load_config(self) -> GlyphMindConfig:
        """Load configuration from files"""
        if self._config is not None:
            return self._config
            
        # Load main settings
        settings_data = self._load_json_file(self.settings_file, {})
        
        # Load API keys
        api_keys_data = self._load_json_file(self.api_keys_file, {})
        
        # Load scheduler config
        scheduler_data = self._load_json_file(self.scheduler_file, {})
        
        # Merge configurations
        config_data = {
            **settings_data,
            "api": api_keys_data,
        }
        
        # Update evolution config with scheduler data
        if "evolution" not in config_data:
            config_data["evolution"] = {}
        config_data["evolution"].update(scheduler_data)
        
        try:
            self._config = GlyphMindConfig(**config_data)
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._config = GlyphMindConfig()  # Use defaults
            
        return self._config
        
    def save_config(self, config: GlyphMindConfig) -> None:
        """Save configuration to files"""
        try:
            # Save main settings (excluding API keys)
            settings_data = {
                "server": config.server.dict(),
                "ui": config.ui.dict(),
                "database": config.database.dict(),
            }
            self._save_json_file(self.settings_file, settings_data)
            
            # Save API keys separately
            self._save_json_file(self.api_keys_file, config.api.dict())
            
            # Save scheduler config
            self._save_json_file(self.scheduler_file, config.evolution.dict())
            
            self._config = config
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            
    def get_config(self) -> GlyphMindConfig:
        """Get current configuration"""
        if self._config is None:
            return self.load_config()
        return self._config
        
    def update_api_key(self, service: str, key: str) -> None:
        """Update a specific API key"""
        config = self.get_config()
        if hasattr(config.api, f"{service}_api_key"):
            setattr(config.api, f"{service}_api_key", key)
            self.save_config(config)
        else:
            raise ValueError(f"Unknown API service: {service}")
            
    def _load_json_file(self, file_path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        """Load JSON file with fallback to default"""
        if not file_path.exists():
            self._save_json_file(file_path, default)
            return default
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading {file_path}: {e}, using defaults")
            return default
            
    def _save_json_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# Global config manager instance
config_manager = ConfigManager()

def get_config() -> GlyphMindConfig:
    """Get the global configuration"""
    return config_manager.get_config()
