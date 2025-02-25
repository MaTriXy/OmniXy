"""Unit tests for the plugin manager."""
import pytest
from src.plugin.plugin_manager import PluginManager

def test_plugin_manager_initialization():
    """Test plugin manager initialization."""
    manager = PluginManager()
    assert manager is not None
    assert len(manager.get_plugins()) == 0

def test_plugin_registration():
    """Test plugin registration."""
    manager = PluginManager()
    
    class TestPlugin:
        name = "test_plugin"
        version = "1.0.0"
        
        def initialize(self):
            return True
    
    plugin = TestPlugin()
    manager.register_plugin(plugin)
    
    assert len(manager.get_plugins()) == 1
    assert manager.get_plugin("test_plugin") is not None

def test_plugin_lifecycle():
    """Test plugin lifecycle management."""
    manager = PluginManager()
    
    class TestPlugin:
        name = "test_plugin"
        version = "1.0.0"
        
        def initialize(self):
            return True
            
        def shutdown(self):
            return True
    
    plugin = TestPlugin()
    manager.register_plugin(plugin)
    
    assert manager.initialize_plugin("test_plugin") is True
    assert manager.shutdown_plugin("test_plugin") is True

def test_invalid_plugin():
    """Test handling of invalid plugins."""
    manager = PluginManager()
    
    with pytest.raises(ValueError):
        manager.register_plugin(None)
    
    with pytest.raises(KeyError):
        manager.get_plugin("non_existent")
