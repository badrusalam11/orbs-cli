"""
Test case-insensitive configuration retrieval
"""
import os
import tempfile
from pathlib import Path


def test_case_insensitive_env_vars():
    """Test that config.get() is case-insensitive for environment variables"""
    # Set environment variables with different cases
    os.environ["ORBS_ENV"] = "production"
    os.environ["my_key"] = "lowercase_value"
    os.environ["ANOTHER_KEY"] = "uppercase_value"
    
    from orbs.config import Config
    
    # Create temp settings dir
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_dir = Path(tmpdir) / "settings"
        settings_dir.mkdir()
        
        config = Config(properties_dir=str(settings_dir))
        
        # Test uppercase env var can be retrieved with any case
        assert config.get("ORBS_ENV") == "production"
        assert config.get("orbs_env") == "production"
        assert config.get("Orbs_Env") == "production"
        
        # Test lowercase env var can be retrieved with uppercase
        assert config.get("MY_KEY") == "lowercase_value"
        assert config.get("my_key") == "lowercase_value"
        
        # Test uppercase env var
        assert config.get("ANOTHER_KEY") == "uppercase_value"
        assert config.get("another_key") == "uppercase_value"
    
    # Cleanup
    os.environ.pop("ORBS_ENV", None)
    os.environ.pop("my_key", None)
    os.environ.pop("ANOTHER_KEY", None)
    
    print("✅ Case-insensitive environment variable test passed!")


def test_case_insensitive_properties():
    """Test that config.get() is case-insensitive for properties files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_dir = Path(tmpdir) / "settings"
        settings_dir.mkdir()
        
        # Create a properties file with mixed case keys
        props_file = settings_dir / "test.properties"
        with open(props_file, "w") as f:
            f.write("DATABASE_URL=postgres://localhost\n")
            f.write("api_key=secret123\n")
            f.write("TimeOut=30\n")
        
        from orbs.config import Config
        config = Config(properties_dir=str(settings_dir))
        
        # Test uppercase property can be retrieved with any case
        assert config.get("DATABASE_URL") == "postgres://localhost"
        assert config.get("database_url") == "postgres://localhost"
        assert config.get("Database_Url") == "postgres://localhost"
        
        # Test lowercase property can be retrieved with uppercase
        assert config.get("API_KEY") == "secret123"
        assert config.get("api_key") == "secret123"
        
        # Test mixed case property
        assert config.get("TIMEOUT") == "30"
        assert config.get("timeout") == "30"
        assert config.get("TimeOut") == "30"
    
    print("✅ Case-insensitive properties file test passed!")


def test_env_file_case_insensitive():
    """Test that .env file variables work case-insensitively"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .env file with different cases
        env_file = Path(tmpdir) / ".env"
        with open(env_file, "w") as f:
            f.write("ORBS_ENV=dev\n")
            f.write("test_mode=true\n")
            f.write("Max_Retry=5\n")
        
        settings_dir = Path(tmpdir) / "settings"
        settings_dir.mkdir()
        
        from orbs.config import Config
        config = Config(env_file=str(env_file), properties_dir=str(settings_dir))
        
        # Test all cases
        assert config.get("ORBS_ENV") == "dev"
        assert config.get("orbs_env") == "dev"
        
        assert config.get("TEST_MODE") == "true"
        assert config.get("test_mode") == "true"
        
        assert config.get("MAX_RETRY") == "5"
        assert config.get("max_retry") == "5"
        assert config.get("Max_Retry") == "5"
    
    print("✅ Case-insensitive .env file test passed!")


if __name__ == "__main__":
    test_case_insensitive_env_vars()
    test_case_insensitive_properties()
    test_env_file_case_insensitive()
    print("\n🎉 All case-insensitive tests passed!")
