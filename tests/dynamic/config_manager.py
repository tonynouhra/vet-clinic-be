"""
Version Configuration Manager for Dynamic API Testing Framework.

Manages version-specific configurations and capabilities loaded from YAML files.
Provides a centralized way to access version differences, features, and schema definitions.
"""

import os
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class VersionConfigManager:
    """Manages version-specific configurations and capabilities."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        if config_path is None:
            # Default to tests/config/version_config.yaml relative to this file
            current_dir = Path(__file__).parent
            config_path = current_dir.parent / "config" / "version_config.yaml"
        
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration file: {e}")
        
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration structure."""
        if not self._config:
            raise ConfigurationError("Configuration is empty")
        
        if "versions" not in self._config:
            raise ConfigurationError("Configuration must contain 'versions' section")
        
        versions = self._config["versions"]
        if not isinstance(versions, dict) or not versions:
            raise ConfigurationError("'versions' section must be a non-empty dictionary")
        
        # Validate each version configuration
        for version_name, version_config in versions.items():
            self._validate_version_config(version_name, version_config)
    
    def _validate_version_config(self, version_name: str, config: Dict[str, Any]) -> None:
        """Validate a single version configuration."""
        required_sections = ["base_url", "features", "endpoints", "schema_fields"]
        
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(
                    f"Version '{version_name}' missing required section: {section}"
                )
        
        # Validate base_url
        if not isinstance(config["base_url"], str) or not config["base_url"]:
            raise ConfigurationError(
                f"Version '{version_name}' base_url must be a non-empty string"
            )
        
        # Validate features
        if not isinstance(config["features"], dict):
            raise ConfigurationError(
                f"Version '{version_name}' features must be a dictionary"
            )
        
        # Validate endpoints
        if not isinstance(config["endpoints"], dict):
            raise ConfigurationError(
                f"Version '{version_name}' endpoints must be a dictionary"
            )
        
        # Validate schema_fields
        if not isinstance(config["schema_fields"], dict):
            raise ConfigurationError(
                f"Version '{version_name}' schema_fields must be a dictionary"
            )
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    def get_version_config(self, version: str) -> Dict[str, Any]:
        """
        Get complete configuration for a specific version.
        
        Args:
            version: Version identifier (e.g., 'v1', 'v2')
            
        Returns:
            Dictionary containing version configuration
            
        Raises:
            ConfigurationError: If version is not found
        """
        if not self._config or "versions" not in self._config:
            raise ConfigurationError("Configuration not loaded")
        
        if version not in self._config["versions"]:
            available_versions = list(self._config["versions"].keys())
            raise ConfigurationError(
                f"Version '{version}' not found. Available versions: {available_versions}"
            )
        
        return self._config["versions"][version].copy()
    
    def get_supported_versions(self) -> List[str]:
        """
        Get list of all supported API versions.
        
        Returns:
            List of version identifiers
        """
        if not self._config or "versions" not in self._config:
            return []
        
        return list(self._config["versions"].keys())
    
    def get_feature_availability(self, version: str, feature: str) -> bool:
        """
        Check if a feature is available in the specified version.
        
        Args:
            version: Version identifier
            feature: Feature name
            
        Returns:
            True if feature is available, False otherwise
        """
        try:
            version_config = self.get_version_config(version)
            return version_config.get("features", {}).get(feature, False)
        except ConfigurationError:
            return False
    
    def get_endpoint_url(self, version: str, resource: str, **kwargs) -> str:
        """
        Get endpoint URL for a specific version and resource.
        
        Args:
            version: Version identifier
            resource: Resource name (e.g., 'pets', 'users')
            **kwargs: Additional parameters for URL formatting (e.g., pet_id)
            
        Returns:
            Complete endpoint URL
            
        Raises:
            ConfigurationError: If version or resource is not found
        """
        version_config = self.get_version_config(version)
        endpoints = version_config.get("endpoints", {})
        
        if resource not in endpoints:
            available_resources = list(endpoints.keys())
            raise ConfigurationError(
                f"Resource '{resource}' not found in version '{version}'. "
                f"Available resources: {available_resources}"
            )
        
        endpoint_template = endpoints[resource]
        
        # Format the endpoint with any provided parameters
        try:
            return endpoint_template.format(**kwargs)
        except KeyError as e:
            raise ConfigurationError(
                f"Missing required parameter for endpoint '{resource}': {e}"
            )
    
    def get_schema_fields(self, version: str, schema_type: str) -> List[str]:
        """
        Get schema fields for a specific version and schema type.
        
        Args:
            version: Version identifier
            schema_type: Schema type (e.g., 'pet_create', 'user_response')
            
        Returns:
            List of field names
            
        Raises:
            ConfigurationError: If version or schema type is not found
        """
        version_config = self.get_version_config(version)
        schema_fields = version_config.get("schema_fields", {})
        
        if schema_type not in schema_fields:
            available_schemas = list(schema_fields.keys())
            raise ConfigurationError(
                f"Schema type '{schema_type}' not found in version '{version}'. "
                f"Available schemas: {available_schemas}"
            )
        
        return schema_fields[schema_type].copy()
    
    def get_required_fields(self, version: str, schema_type: str) -> List[str]:
        """
        Get required fields for a specific version and schema type.
        
        Args:
            version: Version identifier
            schema_type: Schema type (e.g., 'pet_create', 'user_create')
            
        Returns:
            List of required field names
        """
        version_config = self.get_version_config(version)
        required_fields = version_config.get("required_fields", {})
        return required_fields.get(schema_type, []).copy()
    
    def get_optional_fields(self, version: str, schema_type: str) -> List[str]:
        """
        Get optional fields for a specific version and schema type.
        
        Args:
            version: Version identifier
            schema_type: Schema type (e.g., 'pet_create', 'user_create')
            
        Returns:
            List of optional field names
        """
        version_config = self.get_version_config(version)
        optional_fields = version_config.get("optional_fields", {})
        return optional_fields.get(schema_type, []).copy()
    
    def get_default_values(self, version: str, schema_type: str) -> Dict[str, Any]:
        """
        Get default values for a specific version and schema type.
        
        Args:
            version: Version identifier
            schema_type: Schema type (e.g., 'pet_create', 'user_create')
            
        Returns:
            Dictionary of default field values
        """
        version_config = self.get_version_config(version)
        default_values = version_config.get("default_values", {})
        return default_values.get(schema_type, {}).copy()
    
    def get_base_url(self, version: str) -> str:
        """
        Get base URL for a specific version.
        
        Args:
            version: Version identifier
            
        Returns:
            Base URL string
        """
        version_config = self.get_version_config(version)
        return version_config["base_url"]
    
    def get_global_settings(self) -> Dict[str, Any]:
        """
        Get global configuration settings.
        
        Returns:
            Dictionary of global settings
        """
        if not self._config:
            return {}
        
        return self._config.get("global_settings", {}).copy()
    
    def has_schema_type(self, version: str, schema_type: str) -> bool:
        """
        Check if a schema type exists for a specific version.
        
        Args:
            version: Version identifier
            schema_type: Schema type to check
            
        Returns:
            True if schema type exists, False otherwise
        """
        try:
            version_config = self.get_version_config(version)
            schema_fields = version_config.get("schema_fields", {})
            return schema_type in schema_fields
        except ConfigurationError:
            return False
    
    def get_features_for_version(self, version: str) -> Dict[str, bool]:
        """
        Get all features and their availability for a specific version.
        
        Args:
            version: Version identifier
            
        Returns:
            Dictionary mapping feature names to availability
        """
        version_config = self.get_version_config(version)
        return version_config.get("features", {}).copy()
    
    def get_versions_supporting_feature(self, feature: str) -> List[str]:
        """
        Get list of versions that support a specific feature.
        
        Args:
            feature: Feature name
            
        Returns:
            List of version identifiers that support the feature
        """
        supporting_versions = []
        
        for version in self.get_supported_versions():
            if self.get_feature_availability(version, feature):
                supporting_versions.append(version)
        
        return supporting_versions


# Global instance for easy access
_config_manager: Optional[VersionConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> VersionConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_path: Path to configuration file (only used on first call)
        
    Returns:
        VersionConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = VersionConfigManager(config_path)
    
    return _config_manager


def reset_config_manager() -> None:
    """Reset the global configuration manager (useful for testing)."""
    global _config_manager
    _config_manager = None