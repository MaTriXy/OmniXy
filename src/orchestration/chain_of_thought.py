import redis  # For persistent context storage


class ChainOfThoughtOrchestrator:
    def __init__(self, client, redis_host="localhost", redis_port=6379):
        self.redis = redis.Redis(host=redis_host, port=redis_port)
        self.client = client
        self.context = {}
        self.steps = []

    def process_request(self, mcp_request):
        # Initialize or update context for the session
        session_id = mcp_request.metadata.get("session_id", "default")
        if session_id not in self.context:
            self.context[session_id] = []

        # Add the current request to the context
        self.context[session_id].append(mcp_request)

        # Perform multi-step reasoning
        if len(self.context[session_id]) > 1:
            # Combine previous steps into the current request
            combined_messages = []
            for req in self.context[session_id]:
                combined_messages.extend(req.messages)
            mcp_request.messages = combined_messages

            # Ensure combined messages do not exceed the token limit
            token_limit = mcp_request.parameters.get("max_tokens", 4096)
            while self._calculate_tokens(mcp_request.messages) > token_limit:
                self.context[session_id].pop(0)  # Remove the oldest request
                combined_messages = []
                for req in self.context[session_id]:
                    combined_messages.extend(req.messages)
                mcp_request.messages = combined_messages

        # Save context to Redis for persistence
        self.redis.set(f"context:{session_id}", str(self.context[session_id]))

        # Return the processed request
        return mcp_request

    def clear_context(self, session_id="default"):
        """Clear the context for a specific session."""
        if session_id in self.context:
            del self.context[session_id]
        self.redis.delete(f"context:{session_id}")

    def _calculate_tokens(self, messages):
        """Estimate the total number of tokens in the messages."""
        return sum(len(msg["content"].split()) for msg in messages)

    def add_step(self, step_config):
        """Add a step to the chain.

        Args:
            step_config (dict): Configuration for the step
        """
        if not isinstance(step_config, dict):
            raise ValueError("Step config must be a dictionary")
        prompt = step_config.get("prompt", "")
        if not prompt or not str(prompt).strip():
            raise ValueError("Prompt cannot be empty")
        if "name" not in step_config:
            raise ValueError("Step config must contain name")
        self.steps.append(step_config)

    def add_parallel_steps(self, steps_config):
        """Add parallel steps to the chain.

        Args:
            steps_config (list): List of step configurations
        """
        if not isinstance(steps_config, list):
            raise ValueError("Steps config must be a list")
        self.steps.extend(steps_config)

    def solve(self):
        """Execute the chain of thought.

        Returns:
            list: List of step results
        """
        results = []
        for step in self.steps:
            # Format with context and previous results
            format_args = {**self.context}

            # Add previous step responses to format args
            for res in results:
                format_args[f"{res['name']}_response"] = res["response"]["choices"][0][
                    "text"
                ]

            # Format the prompt with context and previous results
            try:
                formatted_prompt = step["prompt"].format(**format_args)
            except KeyError:
                # If formatting fails, use the original prompt
                formatted_prompt = step["prompt"]

            # Send request to the client
            response = self.client.complete(
                messages=[{"role": "user", "content": formatted_prompt}]
            )

            # Store the result
            results.append(
                {"name": step["name"], "prompt": formatted_prompt, "response": response}
            )
        return results

    def set_context(self, context):
        """Set context for the chain.

        Args:
            context (dict): Context dictionary
        """
        self.context = context
