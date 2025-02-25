"""Unit tests for chain of thought orchestration."""

import pytest
from src.orchestration.chain_of_thought import ChainOfThoughtOrchestrator


class MockMCPClient:
    def complete(self, messages, **kwargs):
        return {
            "choices": [
                {
                    "text": f"Processed: {messages[-1]['content']}",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": None,
                }
            ],
            "usage": {"total_tokens": 10},
        }


@pytest.fixture
def chain():
    """Create a chain of thought instance with mock client."""
    client = MockMCPClient()
    return ChainOfThoughtOrchestrator(client)


def test_chain_initialization(chain):
    """Test chain of thought initialization."""
    assert chain is not None
    assert hasattr(chain, "solve")
    assert hasattr(chain, "add_step")


def test_chain_step_addition(chain):
    """Test adding steps to chain of thought."""
    chain.add_step({"name": "analyze", "prompt": "Analyze the data"})
    assert len(chain.steps) == 1
    assert chain.steps[0]["name"] == "analyze"


def test_chain_execution(chain):
    """Test chain of thought execution."""
    chain.add_step({"name": "analyze", "prompt": "Analyze the data"})
    chain.add_step({"name": "synthesize", "prompt": "Synthesize findings"})

    result = chain.solve()
    assert len(result) == 2
    assert all("Processed" in step["response"]["choices"][0]["text"] for step in result)


def test_chain_with_context(chain):
    """Test chain of thought with context."""
    context = {"data": "test data"}
    chain.set_context(context)

    chain.add_step({"name": "analyze", "prompt": "Analyze {data}"})

    result = chain.solve()
    assert "test data" in result[0]["prompt"]


def test_chain_validation(chain):
    """Test chain of thought validation."""
    with pytest.raises(ValueError):
        chain.add_step({"invalid": "step"})


def test_chain_memory(chain):
    """Test chain of thought memory handling."""
    chain.add_step({"name": "step1", "prompt": "Initial analysis"})
    chain.add_step(
        {"name": "step2", "prompt": "Use previous analysis: {step1_response}"}
    )

    result = chain.solve()
    assert len(result) == 2
    assert result[1]["prompt"] == "Use previous analysis: Processed: Initial analysis"


def test_chain_error_handling(chain):
    """Test chain of thought error handling."""
    with pytest.raises(ValueError):
        chain.add_step({"name": "error_step", "prompt": None})
        chain.solve()


def test_chain_parallel_execution(chain):
    """Test parallel step execution."""
    chain.add_parallel_steps(
        [
            {"name": "step1", "prompt": "Analysis 1"},
            {"name": "step2", "prompt": "Analysis 2"},
        ]
    )

    result = chain.solve()
    assert len(result) == 2
    assert all("Processed" in step["response"]["choices"][0]["text"] for step in result)
