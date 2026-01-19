"""
Test environment configuration functionality
"""
import os
import sys
import tempfile
from pathlib import Path
import yaml


def test_environment_loading():
    """Test loading environment configuration"""
    # Prevent orbs from being imported which would create the singleton
    # Import only what we need
    original_path = sys.path.copy()
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        env_dir = Path(tmpdir) / "environments"
        env_dir.mkdir()
        
        # Create test environment files
        default_config = {
            "url": "https://default.com",
            "username": "default_user",
            "custom_config": {
                "feature_flag": True,
                "timeout": 30
            }
        }
        
        dev_config = {
            "url": "https://dev.com",
            "username": "dev_user",
            "custom_config": {
                "feature_flag": False,
                "timeout": 60
            }
        }
        
        with open(env_dir / "default.yml", "w") as f:
            yaml.dump(default_config, f)
        
        with open(env_dir / "dev.yml", "w") as f:
            yaml.dump(dev_config, f)
        
        # Create settings dir
        settings_dir = Path(tmpdir) / "settings"
        settings_dir.mkdir()
        
        # Direct import to avoid singleton creation
        import importlib.util
        spec = importlib.util.spec_from_file_location("config_module", "orbs/config.py")
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        # Test default environment
        os.environ.pop("ORBS_ENV", None)
        cfg = config_module.Config(properties_dir=str(settings_dir), environments_dir=str(env_dir))
        
        assert cfg.target("url") == "https://default.com"
        assert cfg.target("username") == "default_user"
        assert cfg.target("custom_config.feature_flag") is True
        assert cfg.target("custom_config.timeout") == 30
        print("✅ Default environment test passed!")
        
        # Test dev environment
        os.environ["ORBS_ENV"] = "dev"
        cfg = config_module.Config(properties_dir=str(settings_dir), environments_dir=str(env_dir))
        
        assert cfg.target("url") == "https://dev.com"
        assert cfg.target("username") == "dev_user"
        assert cfg.target("custom_config.feature_flag") is False
        assert cfg.target("custom_config.timeout") == 60
        print("✅ Dev environment test passed!")
        
        # Test default value
        assert cfg.target("non_existent", "default_value") == "default_value"
        print("✅ Default value test passed!")
        
        # Cleanup
        os.environ.pop("ORBS_ENV", None)
    
    sys.path = original_path


def test_environment_variable_replacement():
    """Test environment variable placeholder replacement"""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_dir = Path(tmpdir) / "environments"
        env_dir.mkdir()
        
        # Create config with env var placeholders
        config_data = {
            "username": "${TEST_USERNAME}",
            "password": "${TEST_PASSWORD}",
            "url": "https://${TEST_DOMAIN}/api"
        }
        
        with open(env_dir / "default.yml", "w") as f:
            yaml.dump(config_data, f)
        
        # Create settings dir
        settings_dir = Path(tmpdir) / "settings"
        settings_dir.mkdir()
        
        # Set environment variables
        os.environ["TEST_USERNAME"] = "admin"
        os.environ["TEST_PASSWORD"] = "secret123"
        os.environ["TEST_DOMAIN"] = "example.com"
        
        # Direct import to avoid singleton
        import importlib.util
        spec = importlib.util.spec_from_file_location("config_module", "orbs/config.py")
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        cfg = config_module.Config(properties_dir=str(settings_dir), environments_dir=str(env_dir))
        
        assert cfg.target("username") == "admin"
        assert cfg.target("password") == "secret123"
        assert cfg.target("url") == "https://example.com/api"
        print("✅ Environment variable replacement test passed!")
        
        # Cleanup
        os.environ.pop("TEST_USERNAME", None)
        os.environ.pop("TEST_PASSWORD", None)
        os.environ.pop("TEST_DOMAIN", None)


if __name__ == "__main__":
    test_environment_loading()
    test_environment_variable_replacement()
    print("\n🎉 All environment tests passed!")

