# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A hello world sample that just calls some flows."""

import asyncio
from typing import Any

from genkit.ai.document import Document
from genkit.ai.generate import generate_action
from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateActionOptions,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Media,
    MediaPart,
    Message,
    RetrieverRequest,
    RetrieverResponse,
    Role,
    TextPart,
)
from genkit.plugins.vertex_ai import (
    EmbeddingModels,
    EmbeddingsTaskType,
    GeminiVersion,
    VertexAI,
    vertexai_name,
)
from genkit.veneer.veneer import Genkit
from pydantic import BaseModel, Field

ai = Genkit(
    plugins=[VertexAI()],
    model=vertexai_name(GeminiVersion.GEMINI_1_5_FLASH),
)


class MyInput(BaseModel):
    """Input model for the sum_two_numbers2 function.

    Attributes:
        a: First number to add.
        b: Second number to add.
    """

    a: int = Field(description='a field')
    b: int = Field(description='b field')


def hi_fn(hi_input) -> GenerateRequest:
    """Generate a request to greet a user.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    return GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=f'Say hi to {hi_input}'),
                ],
            ),
        ],
    )


@ai.flow()
async def say_hi(name: str):
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    return await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'Say hi to {name}')],
            ),
        ],
    )


@ai.flow()
async def embed_docs(docs: list[str]):
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embedding.
    """
    options = {'task': EmbeddingsTaskType.CLUSTERING}
    return await ai.embed(
        model=vertexai_name(EmbeddingModels.TEXT_EMBEDDING_004_ENG),
        documents=[Document.from_text(doc) for doc in docs],
        options=options,
    )


@ai.flow()
async def simple_generate_action_flow(name: str) -> Any:
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='vertexai/gemini-1.5-flash',
            messages=[
                Message(
                    role=Role.USER,
                    content=[TextPart(text=f'Say hi to {name}')],
                ),
            ],
        ),
    )
    return response.text()


class GablorkenInput(BaseModel):
    value: int = Field(description='value to calculate gablorken for')


@ai.tool('calculates a gablorken')
def gablorkenTool(input: GablorkenInput):
    return input.value * 3 - 5


@ai.flow()
async def simple_generate_action_with_tools_flow(value: int) -> Any:
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='vertexai/gemini-1.5-flash',
            messages=[
                Message(
                    role=Role.USER,
                    content=[TextPart(text=f'what is a gablorken of {value}')],
                ),
            ],
            tools=['gablorkenTool'],
        ),
    )
    return response.text


@ai.flow()
def sum_two_numbers2(my_input: MyInput) -> Any:
    """Add two numbers together.

    Args:
        my_input: A MyInput object containing the two numbers to add.

    Returns:
        The sum of the two numbers.
    """
    return my_input.a + my_input.b


@ai.flow()
def streaming_sync_flow(inp: str, ctx: ActionRunContext):
    """Example of sync flow."""
    ctx.send_chunk(1)
    ctx.send_chunk({'chunk': 'blah'})
    ctx.send_chunk(3)
    return 'streamingSyncFlow 4'


@ai.flow()
async def streaming_async_flow(inp: str, ctx: ActionRunContext):
    """Example of async flow."""
    ctx.send_chunk(1)
    ctx.send_chunk({'chunk': 'blah'})
    ctx.send_chunk(3)
    return 'streamingAsyncFlow 4'


async def main() -> None:
    """Main entry point for the hello sample.

    This function demonstrates the usage of the AI flow by generating
    greetings and performing simple arithmetic operations.
    """
    print(await say_hi('John Doe'))
    print(sum_two_numbers2(MyInput(a=1, b=3)))
    print(
        await embed_docs(['banana muffins? ', 'banana bread? banana muffins?'])
    )


def my_model(request: GenerateRequest, ctx: ActionRunContext):
    if ctx.is_streaming:
        ctx.send_chunk(
            GenerateResponseChunk(role=Role.MODEL, content=[TextPart(text='1')])
        )
        ctx.send_chunk(
            GenerateResponseChunk(role=Role.MODEL, content=[TextPart(text='2')])
        )
        ctx.send_chunk(
            GenerateResponseChunk(role=Role.MODEL, content=[TextPart(text='3')])
        )

    return GenerateResponse(
        message=Message(
            role=Role.MODEL,
            content=[TextPart(text='hello')],
        )
    )


ai.define_model(name='my_model', fn=my_model)


def my_retriever(request: RetrieverRequest, ctx: ActionRunContext):
    return RetrieverResponse(
        documents=[Document.from_text('Hello'), Document.from_text('World')]
    )


ai.define_retriever(name='my_retriever', fn=my_retriever)


@ai.flow()
async def streaming_model_tester(_: str, ctx: ActionRunContext):
    stream, res = ai.generate_stream(
        prompt='tell me a long joke',
        model=vertexai_name(GeminiVersion.GEMINI_1_5_PRO),
    )

    async for chunk in stream:
        print(chunk.text)
        ctx.send_chunk(f'chunk: {chunk.text}')

    return (await res).text


@ai.flow()
async def describe_picture(url: str):
    return await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='What is shown in this image?'),
                    MediaPart(media=Media(contentType='image/jpg', url=url)),
                ],
            ),
        ],
    )


myprompt = ai.define_prompt(model='my_model', prompt='tell me a long dad joke')


@ai.flow()
async def call_a_prompt(_: str):
    return (await myprompt()).text


@ai.flow()
async def stream_a_prompt(_: str, ctx: ActionRunContext):
    stream, res = myprompt.stream()

    async for chunk in stream:
        ctx.send_chunk(f'chunk: {chunk.text}')

    return (await res).text


@ai.flow()
def throwy(_: str):
    raise Exception('oops')


@ai.flow()
async def async_throwy(_: str):
    raise Exception('oops')


@ai.flow()
def streamy_throwy(inp: str, ctx: ActionRunContext):
    ctx.send_chunk(1)
    ctx.send_chunk({'chunk': 'blah'})
    ctx.send_chunk(3)
    raise Exception('oops')


@ai.flow()
async def async_streamy_throwy(inp: str, ctx: ActionRunContext):
    ctx.send_chunk(1)
    ctx.send_chunk({'chunk': 'blah'})
    ctx.send_chunk(3)
    raise Exception('oops')
