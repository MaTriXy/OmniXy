from typing import Dict, Optional, Any, Union, Callable
from pydantic import BaseModel, Field


class PluginModel(BaseModel):
    """Pydantic model for plugin configuration."""

    name: str = Field(..., description="Name of the plugin")
    version: str = Field(..., description="Version of the plugin")
    description: Optional[str] = Field(None, description="Description of the plugin")
    enabled: bool = Field(True, description="Whether the plugin is enabled")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration for the plugin"
    )


class PluginInterface:
    """Interface that all plugins must implement."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        raise NotImplementedError("Plugin must implement name property")

    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        raise NotImplementedError("Plugin must implement version property")

    def initialize(self) -> bool:
        """Initialize the plugin.

        Returns:
            True if initialization was successful
        """
        return True

    def shutdown(self) -> bool:
        """Shutdown the plugin.

        Returns:
            True if shutdown was successful
        """
        return True

    def process_step(self, data: Any) -> Any:
        """Process a step with the plugin.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        raise NotImplementedError("Plugin must implement process_step method")


class PluginManager:
    """Manager for registering and executing plugins."""

    def __init__(self):
        """Initialize the plugin manager."""
        self.plugins: Dict[str, Any] = {}

    def register_plugin(self, plugin: Union[PluginInterface, Callable]) -> bool:
        """Register a plugin object with the manager.

        Args:
            plugin: A plugin object with name and version attributes or a callable function

        Returns:
            True if registration was successful

        Raises:
            ValueError: If plugin is None or invalid
        """
        if plugin is None:
            raise ValueError("Cannot register None as a plugin")

        # Handle function-based plugins
        if callable(plugin) and not hasattr(plugin, "name"):
            # For function-based plugins, use the function name as the plugin name
            plugin_name = plugin.__name__
            self.plugins[plugin_name] = plugin
            return True

        # Validate plugin has required attributes
        if not hasattr(plugin, "name"):
            raise ValueError("Plugin must have a 'name' attribute")

        self.plugins[plugin.name] = plugin
        return True

    def get_plugins(self) -> Dict[str, Any]:
        """Get all registered plugins.

        Returns:
            Dictionary of registered plugins
        """
        return self.plugins

    def get_plugin(self, plugin_name: str) -> Any:
        """Get a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to retrieve

        Returns:
            The plugin object

        Raises:
            KeyError: If plugin is not found
        """
        if plugin_name not in self.plugins:
            raise KeyError(f"Plugin {plugin_name} not registered")
        return self.plugins[plugin_name]

    def initialize_plugin(self, plugin_name: str) -> bool:
        """Initialize a plugin.

        Args:
            plugin_name: Name of the plugin to initialize

        Returns:
            True if initialization was successful

        Raises:
            KeyError: If plugin is not found
            AttributeError: If plugin doesn't support initialization
        """
        plugin = self.get_plugin(plugin_name)

        # Handle function-based plugins
        if callable(plugin) and not hasattr(plugin, "initialize"):
            return True

        return plugin.initialize()

    def shutdown_plugin(self, plugin_name: str) -> bool:
        """Shutdown a plugin.

        Args:
            plugin_name: Name of the plugin to shutdown

        Returns:
            True if shutdown was successful

        Raises:
            KeyError: If plugin is not found
            AttributeError: If plugin doesn't support shutdown
        """
        plugin = self.get_plugin(plugin_name)

        # Handle function-based plugins
        if callable(plugin) and not hasattr(plugin, "shutdown"):
            return True

        return plugin.shutdown()

    def execute_plugin(self, plugin_name: str, data: Any) -> Any:
        """Execute a plugin with the given data.

        Args:
            plugin_name: Name of the plugin to execute
            data: Data to pass to the plugin

        Returns:
            Result from the plugin execution

        Raises:
            KeyError: If plugin is not registered
        """
        plugin = self.get_plugin(plugin_name)

        # Handle function-based plugins
        if callable(plugin) and not hasattr(plugin, "process_step"):
            return plugin(data)

        return plugin.process_step(data)

    def register_plugin_from_model(
        self, model: PluginModel, implementation: Any
    ) -> bool:
        """Register a plugin from a Pydantic model and implementation.

        Args:
            model: Pydantic model with plugin configuration
            implementation: Implementation of the plugin functionality

        Returns:
            True if registration was successful
        """
        # Set attributes on the implementation based on the model
        implementation.name = model.name
        implementation.version = model.version

        if hasattr(implementation, "config"):
            implementation.config = model.config

        return self.register_plugin(implementation)
