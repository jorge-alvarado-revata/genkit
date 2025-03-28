# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Genkit maintains a registry of all actions.

An **action** is a remote callable function that uses typed-JSON RPC over HTTP
to allow the framework and users to define custom AI functionality.  There are
several kinds of action defined by [ActionKind][genkit.core.action.ActionKind]:

| Kind          | Description |
|---------------|-------------|
| `'chat-llm'`  | Chat LLM    |
| `'custom'`    | Custom      |
| `'embedder'`  | Embedder    |
| `'evaluator'` | Evaluator   |
| `'flow'`      | Flow        |
| `'indexer'`   | Indexer     |
| `'model'`     | Model       |
| `'prompt'`    | Prompt      |
| `'retriever'` | Retriever   |
| `'text-llm'`  | Text LLM    |
| `'tool'`      | Tool        |
| `'util'`      | Utility     |

## Operations

It defines the following methods:

| Category         | Method                                                                       | Description                          |
|------------------|------------------------------------------------------------------------------|--------------------------------------|
| **Registration** | [`define_embedder()`][genkit.veneer.registry.GenkitRegistry.define_embedder] | Defines and registers an embedder.   |
|                  | [`define_format()`][genkit.veneer.registry.GenkitRegistry.define_format]     | Defines and registers a format.      |
|                  | [`define_model()`][genkit.veneer.registry.GenkitRegistry.define_model]       | Defines and registers a model.       |
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from functools import wraps
from typing import Any

from genkit.ai.embedding import EmbedderFn
from genkit.ai.formats.types import FormatDef
from genkit.ai.model import ModelFn, ModelMiddleware
from genkit.ai.prompt import define_prompt
from genkit.ai.retriever import RetrieverFn
from genkit.core.action import Action, ActionKind
from genkit.core.codec import dump_dict
from genkit.core.registry import Registry
from genkit.core.schema import to_json_schema
from genkit.core.typing import (
    GenerationCommonConfig,
    Message,
    ModelInfo,
    Part,
    ToolChoice,
)
from pydantic import BaseModel


class GenkitRegistry:
    """User-facing API for interacting with Genkit registry."""

    def __init__(self):
        self.registry = Registry()

    def flow(self, name: str | None = None) -> Callable[[Callable], Callable]:
        """Decorator to register a function as a flow.

        Args:
            name: Optional name for the flow. If not provided, uses the
                function name.
        Returns:
            A decorator function that registers the flow.
        """

        def wrapper(func: Callable) -> Callable:
            """Register the decorated function as a flow.

            Args:
                func: The function to register as a flow.

            Returns:
                The wrapped function that executes the flow.
            """
            flow_name = name if name is not None else func.__name__
            action = self.registry.register_action(
                name=flow_name,
                kind=ActionKind.FLOW,
                fn=func,
                span_metadata={'genkit:metadata:flow:name': flow_name},
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Asynchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """Synchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                return action.run(*args, **kwargs).response

            return FlowWrapper(
                fn=async_wrapper if action.is_async else sync_wrapper,
                action=action,
            )

        return wrapper

    def tool(
        self, description: str, name: str | None = None
    ) -> Callable[[Callable], Callable]:
        """Decorator to register a function as a tool.

        Args:
            description: Description for the tool to be passed to the model.
            name: Optional name for the flow. If not provided, uses the function name.
        Returns:
            A decorator function that registers the tool.
        """

        def wrapper(func: Callable) -> Callable:
            """Register the decorated function as a tool.

            Args:
                func: The function to register as a tool.

            Returns:
                The wrapped function that executes the tool.
            """
            tool_name = name if name is not None else func.__name__
            action = self.registry.register_action(
                name=tool_name,
                kind=ActionKind.TOOL,
                description=description,
                fn=func,
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Asynchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """Synchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return action.run(*args, **kwargs).response

            return async_wrapper if action.is_async else sync_wrapper

        return wrapper

    def define_retriever(
        self,
        name: str,
        fn: RetrieverFn,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Callable[[Callable], Callable]:
        """Define a retriever action.

        Args:
            name: Name of the retriever.
            fn: Function implementing the retriever behavior.
            config_schema: Optional schema for retriever configuration.
            metadata: Optional metadata for the retriever.
        """
        retriever_meta = metadata if metadata else {}
        if 'retriever' not in retriever_meta:
            retriever_meta['retriever'] = {}
        if (
            'label' not in retriever_meta['retriever']
            or not retriever_meta['retriever']['label']
        ):
            retriever_meta['retriever']['label'] = name
        if config_schema:
            retriever_meta['retriever']['customOptions'] = to_json_schema(
                config_schema
            )
        return self.registry.register_action(
            name=name,
            kind=ActionKind.RETRIEVER,
            fn=fn,
            metadata=retriever_meta,
        )

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        info: ModelInfo | None = None,
    ) -> Action:
        """Define a custom model action.

        Args:
            name: Name of the model.
            fn: Function implementing the model behavior.
            config_schema: Optional schema for model configuration.
            metadata: Optional metadata for the model.
            info: Optional ModelInfo for the model.
        """
        model_meta = metadata if metadata else {}
        if info:
            model_meta['model'] = dump_dict(info)
        if 'model' not in model_meta:
            model_meta['model'] = {}
        if (
            'label' not in model_meta['model']
            or not model_meta['model']['label']
        ):
            model_meta['model']['label'] = name

        if config_schema:
            model_meta['model']['customOptions'] = to_json_schema(config_schema)

        return self.registry.register_action(
            name=name,
            kind=ActionKind.MODEL,
            fn=fn,
            metadata=model_meta,
        )

    def define_embedder(
        self,
        name: str,
        fn: EmbedderFn,
        metadata: dict[str, Any] | None = None,
    ) -> Action:
        """Define a custom embedder action.

        Args:
            name: Name of the model.
            fn: Function implementing the embedder behavior.
            metadata: Optional metadata for the model.
        """
        return self.registry.register_action(
            name=name,
            kind=ActionKind.EMBEDDER,
            fn=fn,
            metadata=metadata,
        )

    def define_format(self, format: FormatDef):
        """Registers a custom format in the registry."""
        self.registry.register_value('format', format.name, format)

    def define_prompt(
        self,
        variant: str | None = None,
        model: str | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        description: str | None = None,
        input_schema: type | dict[str, Any] | None = None,
        system: str | Part | list[Part] | None = None,
        prompt: str | Part | list[Part] | None = None,
        messages: str | list[Message] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, Any] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        # TODO:
        #  docs: list[Document]
    ):
        """Define a prompt.

        Args:
            variant: Optional variant name for the prompt.
            model: Optional model name to use for the prompt.
            config: Optional configuration for the model.
            description: Optional description for the prompt.
            input_schema: Optional schema for the input to the prompt.
            system: Optional system message for the prompt.
            prompt: Optional prompt for the model.
            messages: Optional messages for the model.
            output_format: Optional output format for the prompt.
            output_content_type: Optional output content type for the prompt.
            output_instructions: Optional output instructions for the prompt.
            output_schema: Optional schema for the output from the prompt.
            output_constrained: Optional flag indicating whether the output should be constrained.
            max_turns: Optional maximum number of turns for the prompt.
            return_tool_requests: Optional flag indicating whether tool requests should be returned.
            metadata: Optional metadata for the prompt.
            tools: Optional list of tools to use for the prompt.
            tool_choice: Optional tool choice for the prompt.
            use: Optional list of model middlewares to use for the prompt.
        """
        return define_prompt(
            self.registry,
            variant=variant,
            model=model,
            config=config,
            description=description,
            input_schema=input_schema,
            system=system,
            prompt=prompt,
            messages=messages,
            output_format=output_format,
            output_content_type=output_content_type,
            output_instructions=output_instructions,
            output_schema=output_schema,
            output_constrained=output_constrained,
            max_turns=max_turns,
            return_tool_requests=return_tool_requests,
            metadata=metadata,
            tools=tools,
            tool_choice=tool_choice,
            use=use,
        )


class FlowWrapper:
    """A wapper for flow functions to add `stream` method."""

    def __init__(self, fn, action: Action):
        self._fn = fn
        self._action = action

    def __call__(self, *args, **kwds):
        return self._fn(*args, **kwds)

    def stream(
        self,
        input: Any = None,
        context: dict[str, Any] | None = None,
        telemetry_labels: dict[str, Any] | None = None,
    ) -> tuple[
        AsyncIterator,
        asyncio.Future,
    ]:
        """Run the flow and return an async iterator of the results.

        Args:
            input: The input to the action.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.

        Returns:
            A tuple containing:
            - An AsyncIterator of the chunks from the action.
            - An asyncio.Future that resolves to the final result of the action.
        """
        return self._action.stream(
            input=input, context=context, telemetry_labels=telemetry_labels
        )
