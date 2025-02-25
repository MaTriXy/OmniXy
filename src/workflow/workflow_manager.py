import uuid
from typing import Dict, List, Optional, Any, Union, Callable
from pydantic import BaseModel, Field


class WorkflowStepModel(BaseModel):
    """Pydantic model for a workflow step configuration."""

    name: str = Field(..., description="Name of the step")
    action: str = Field(..., description="Action to perform in this step")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the step"
    )


class WorkflowStep:
    """Represents a step in a workflow."""

    def __init__(
        self, name: str, action: str, parameters: Optional[Dict[str, Any]] = None
    ):
        """Initialize a workflow step.

        Args:
            name: Name of the step
            action: Action to perform in this step
            parameters: Parameters for the step
        """
        self.name = name
        self.action = action
        self.parameters = parameters or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary.

        Returns:
            Dictionary representation of the step
        """
        return {"name": self.name, "action": self.action, "parameters": self.parameters}

    @classmethod
    def from_model(cls, model: WorkflowStepModel) -> "WorkflowStep":
        """Create a WorkflowStep from a Pydantic model.

        Args:
            model: Pydantic model of the step

        Returns:
            WorkflowStep instance
        """
        return cls(name=model.name, action=model.action, parameters=model.parameters)


class WorkflowResultModel(BaseModel):
    """Pydantic model for workflow execution results."""

    status: str = Field(..., description="Status of the workflow execution")
    step_results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Results from each step"
    )


class WorkflowResult:
    """Represents the result of a workflow execution."""

    def __init__(self, status: str, step_results: List[Any]):
        """Initialize a workflow result.

        Args:
            status: Status of the workflow execution
            step_results: Results from each step
        """
        self.status = status
        self.step_results = step_results

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation of the result
        """
        return {"status": self.status, "step_results": self.step_results}

    @classmethod
    def from_model(cls, model: WorkflowResultModel) -> "WorkflowResult":
        """Create a WorkflowResult from a Pydantic model.

        Args:
            model: Pydantic model of the result

        Returns:
            WorkflowResult instance
        """
        return cls(status=model.status, step_results=model.step_results)


class WorkflowModel(BaseModel):
    """Pydantic model for a workflow configuration."""

    name: str = Field(..., description="Name of the workflow")
    steps: List[WorkflowStepModel] = Field(
        default_factory=list, description="Steps in the workflow"
    )


class Workflow:
    """Represents a workflow with steps that can be executed."""

    def __init__(self, name: str):
        """Initialize a workflow.

        Args:
            name: Name of the workflow
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.steps: List[WorkflowStep] = []

    def add_step(
        self, step_config: Union[Dict[str, Any], WorkflowStepModel]
    ) -> WorkflowStep:
        """Add a step to the workflow.

        Args:
            step_config: Configuration for the step

        Returns:
            The created workflow step

        Raises:
            ValueError: If step configuration is invalid
        """
        # Convert to Pydantic model for validation if it's a dict
        if isinstance(step_config, dict):
            try:
                step_model = WorkflowStepModel(**step_config)
            except Exception as e:
                raise ValueError(f"Invalid step configuration: {str(e)}")
        else:
            step_model = step_config

        step = WorkflowStep.from_model(step_model)
        self.steps.append(step)
        return step

    def execute(
        self, plugin_manager=None, context: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """Execute the workflow.

        Args:
            plugin_manager: Plugin manager for executing plugin steps
            context: Context data for the workflow

        Returns:
            Result of the workflow execution

        Raises:
            ValueError: If plugin manager is required but not provided
        """
        context = context or {}
        step_results = []

        for step in self.steps:
            # Check if this is a plugin step
            if "." in step.action:
                if not plugin_manager:
                    raise ValueError("Plugin manager required for plugin steps")

                plugin_name, method = step.action.split(".", 1)

                result = plugin_manager.execute_plugin(plugin_name, step.parameters)
                step_results.append(result)
            else:
                # Handle regular workflow steps
                result = self._execute_step(step, context)
                step_results.append(result)

        return WorkflowResult("completed", step_results)

    def _execute_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step.

        Args:
            step: Step to execute
            context: Context data

        Returns:
            Result of the step execution
        """
        # Simple implementation for now
        return {"step": step.name, "result": f"Executed {step.name}"}

    def to_model(self) -> WorkflowModel:
        """Convert to Pydantic model.

        Returns:
            Pydantic model of the workflow
        """
        return WorkflowModel(
            name=self.name,
            steps=[WorkflowStepModel(**step.to_dict()) for step in self.steps],
        )

    @classmethod
    def from_model(cls, model: WorkflowModel) -> "Workflow":
        """Create a Workflow from a Pydantic model.

        Args:
            model: Pydantic model of the workflow

        Returns:
            Workflow instance
        """
        workflow = cls(name=model.name)
        for step_model in model.steps:
            workflow.add_step(step_model)
        return workflow


class WorkflowManager:
    """Manager for creating and executing workflows."""

    def __init__(self):
        """Initialize the workflow manager."""
        self.workflows: Dict[str, Union[Workflow, Callable]] = {}

    def create_workflow(self, workflow_name: str) -> Workflow:
        """Create a new workflow.

        Args:
            workflow_name: Name of the workflow

        Returns:
            The created workflow
        """
        workflow = Workflow(workflow_name)
        self.workflows[workflow_name] = workflow
        return workflow

    def register_workflow(
        self, workflow_name: str, workflow_func: Union[Workflow, Callable]
    ) -> None:
        """Register a workflow function or instance.

        Args:
            workflow_name: Name of the workflow
            workflow_func: Function or Workflow instance that implements the workflow
        """
        self.workflows[workflow_name] = workflow_func

    def process_workflow(self, workflow_name: str, data: Any) -> Any:
        """Process a workflow with the given data.

        Args:
            workflow_name: Name of the workflow to process
            data: Data to pass to the workflow

        Returns:
            Result from the workflow processing

        Raises:
            ValueError: If workflow is not registered
        """
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow {workflow_name} not registered")

        if isinstance(workflow, Workflow):
            return workflow.execute(context=data)
        else:
            # Legacy support for function-based workflows
            return workflow(data)
