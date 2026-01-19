"""Debug properties case sensitivity"""
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmpdir:
    settings_dir = Path(tmpdir) / "settings"
    settings_dir.mkdir()
    
    # Create a properties file
    props_file = settings_dir / "test.properties"
    with open(props_file, "w") as f:
        f.write("DATABASE_URL=postgres://localhost\n")
        f.write("api_key=secret123\n")
    
    from orbs.config import Config
    config = Config(properties_dir=str(settings_dir))
    
    print("Properties loaded:", config.properties)
    print()
    print("Get DATABASE_URL:", config.get("DATABASE_URL"))
    print("Get database_url:", config.get("database_url"))
    print("Get Database_Url:", config.get("Database_Url"))
