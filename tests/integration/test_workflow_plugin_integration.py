"""Integration tests for workflow and plugin interaction."""
import pytest
from src.workflow.workflow_manager import WorkflowManager
from src.plugin.plugin_manager import PluginManager

class TestPlugin:
    name = "test_plugin"
    version = "1.0.0"
    
    def process_step(self, step_data):
        return {"status": "success", "result": f"Processed {step_data}"}

@pytest.fixture
def setup_managers():
    """Set up workflow and plugin managers for testing."""
    workflow_manager = WorkflowManager()
    plugin_manager = PluginManager()
    plugin_manager.register_plugin(TestPlugin())
    return workflow_manager, plugin_manager

def test_workflow_with_plugin(setup_managers):
    """Test workflow execution with plugin integration."""
    workflow_manager, plugin_manager = setup_managers
    
    # Create workflow
    workflow = workflow_manager.create_workflow("test_integration")
    
    # Add step that uses plugin
    workflow.add_step({
        "name": "plugin_step",
        "action": "test_plugin.process_step",
        "parameters": {"data": "test_data"}
    })
    
    # Execute workflow
    result = workflow.execute(plugin_manager=plugin_manager)
    
    assert result.status == "completed"
    assert "Processed" in result.step_results[0]["result"]

def test_multiple_plugin_steps(setup_managers):
    """Test workflow with multiple plugin steps."""
    workflow_manager, plugin_manager = setup_managers
    
    workflow = workflow_manager.create_workflow("multi_step")
    
    # Add multiple steps
    workflow.add_step({
        "name": "step1",
        "action": "test_plugin.process_step",
        "parameters": {"data": "step1_data"}
    })
    
    workflow.add_step({
        "name": "step2",
        "action": "test_plugin.process_step",
        "parameters": {"data": "step2_data"}
    })
    
    result = workflow.execute(plugin_manager=plugin_manager)
    
    assert result.status == "completed"
    assert len(result.step_results) == 2
    assert all("Processed" in step["result"] for step in result.step_results)
