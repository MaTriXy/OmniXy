from typing import Dict, List, Optional, Any, Type, Set
import json
from pathlib import Path
import inspect

from pydantic import BaseModel

from src.core.request import MCPRequest, Message
from src.core.response import MCPResponse, MCPPartialResponse
from src.core.mcp_layer import ServerConfig
from src.client import ClientConfig
from src.drivers.driver_factory import (
    BaseDriverConfig,
    OpenAIDriverConfig,
    CohereDriverConfig,
    GeminiDriverConfig,
    LocalLLMDriverConfig,
)
from src.workflow.workflow_manager import (
    WorkflowModel,
    WorkflowStepModel,
    WorkflowResultModel,
)
from src.plugin.plugin_manager import PluginModel
from src.core.settings import Settings, APISettings, ServerSettings, LoggingSettings


def generate_schema(
    model_class: Type[BaseModel], output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Generate JSON schema for a Pydantic model.

    Args:
        model_class: The Pydantic model class
        output_dir: Directory to save the schema file

    Returns:
        The JSON schema as a dictionary
    """
    schema = model_class.model_json_schema()

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        schema_file = output_dir / f"{model_class.__name__}.json"
        with open(schema_file, "w") as f:
            json.dump(schema, f, indent=2)

    return schema


def generate_all_schemas(
    output_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Generate JSON schemas for all Pydantic models in the project.

    Args:
        output_dir: Directory to save the schema files

    Returns:
        Dictionary mapping model names to their schemas
    """
    # List of all model classes to generate schemas for
    model_classes = [
        # Core models
        MCPRequest,
        Message,
        MCPResponse,
        MCPPartialResponse,
        ServerConfig,
        ClientConfig,
        # Driver configs
        BaseDriverConfig,
        OpenAIDriverConfig,
        CohereDriverConfig,
        GeminiDriverConfig,
        LocalLLMDriverConfig,
        # Workflow models
        WorkflowModel,
        WorkflowStepModel,
        WorkflowResultModel,
        # Plugin models
        PluginModel,
        # Settings models
        Settings,
        APISettings,
        ServerSettings,
        LoggingSettings,
    ]

    schemas = {}

    for model_class in model_classes:
        schema = generate_schema(model_class, output_dir)
        schemas[model_class.__name__] = schema

    # Generate an index file if output_dir is provided
    if output_dir:
        index_file = output_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump(
                {
                    "schemas": list(schemas.keys()),
                    "generated_at": str(import_time.now()),
                    "version": "1.0.0",
                },
                f,
                indent=2,
            )

    return schemas


def discover_pydantic_models(package_dir: Path) -> List[Type[BaseModel]]:
    """Discover all Pydantic models in the package.

    Args:
        package_dir: Directory containing the package

    Returns:
        List of discovered Pydantic model classes
    """
    import importlib
    import pkgutil

    models = []
    visited_modules = set()

    def _import_submodules(package_name: str) -> None:
        """Recursively import all submodules of a package."""
        if package_name in visited_modules:
            return

        visited_modules.add(package_name)

        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return

        for _, name, is_pkg in pkgutil.iter_modules(
            package.__path__, package.__name__ + "."
        ):
            if is_pkg:
                _import_submodules(name)
            else:
                try:
                    module = importlib.import_module(name)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            inspect.isclass(attr)
                            and issubclass(attr, BaseModel)
                            and attr != BaseModel
                            and not attr_name.startswith("_")
                        ):
                            models.append(attr)
                except ImportError:
                    continue

    # Start importing from the src package
    _import_submodules("src")

    return models


if __name__ == "__main__":
    import datetime as import_time

    # Generate schemas for all models
    output_dir = Path(__file__).parent.parent.parent / "docs" / "schemas"
    schemas = generate_all_schemas(output_dir)

    print(f"Generated schemas for {len(schemas)} models in {output_dir}")

    # Discover and generate schemas for all models in the package
    discovered_models = discover_pydantic_models(Path(__file__).parent.parent)

    discovered_output_dir = output_dir / "discovered"
    discovered_output_dir.mkdir(parents=True, exist_ok=True)

    discovered_schemas = {}
    for model in discovered_models:
        schema = generate_schema(model, discovered_output_dir)
        discovered_schemas[model.__name__] = schema

    print(
        f"Discovered and generated schemas for {len(discovered_schemas)} models in {discovered_output_dir}"
    )

    # Generate an index file for discovered schemas
    index_file = discovered_output_dir / "index.json"
    with open(index_file, "w") as f:
        json.dump(
            {
                "schemas": list(discovered_schemas.keys()),
                "generated_at": str(import_time.datetime.now()),
                "version": "1.0.0",
            },
            f,
            indent=2,
        )
