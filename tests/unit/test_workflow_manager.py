"""Unit tests for the workflow manager."""
import pytest
from src.workflow.workflow_manager import WorkflowManager

def test_workflow_creation():
    """Test creating a new workflow."""
    manager = WorkflowManager()
    workflow = manager.create_workflow("test_workflow")
    assert workflow.id is not None
    assert workflow.name == "test_workflow"

def test_workflow_step_addition():
    """Test adding steps to a workflow."""
    manager = WorkflowManager()
    workflow = manager.create_workflow("test_workflow")
    
    step = workflow.add_step({
        "name": "test_step",
        "action": "prompt",
        "parameters": {"text": "test prompt"}
    })
    
    assert len(workflow.steps) == 1
    assert workflow.steps[0].name == "test_step"

def test_workflow_execution():
    """Test workflow execution."""
    manager = WorkflowManager()
    workflow = manager.create_workflow("test_workflow")
    
    workflow.add_step({
        "name": "step1",
        "action": "prompt",
        "parameters": {"text": "test prompt"}
    })
    
    result = workflow.execute()
    assert result.status == "completed"
    assert len(result.step_results) == 1

def test_workflow_validation():
    """Test workflow validation."""
    manager = WorkflowManager()
    workflow = manager.create_workflow("test_workflow")
    
    with pytest.raises(ValueError):
        workflow.add_step({
            "invalid": "step"
        })
