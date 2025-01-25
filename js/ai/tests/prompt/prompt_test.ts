/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { Document } from '../../lib/document';
import { GenerateOptions } from '../../lib/index';
import { Session } from '../../lib/session';
import { ModelAction, defineModel } from '../../src/model.ts';
import {
  PromptConfig,
  PromptGenerateOptions,
  definePrompt,
} from '../../src/prompt.ts';
import { defineTool } from '../../src/tool.ts';

describe('prompt', () => {
  let registry;

  beforeEach(() => {
    registry = new Registry();

    defineEchoModel(registry);
    defineTool(
      registry,
      {
        name: 'toolA',
        description: 'toolA descr',
      },
      async () => 'a'
    );
  });

  let basicTests: {
    name: string;
    prompt: PromptConfig;
    input?: any;
    inputOptions?: PromptGenerateOptions;
    wantTextOutput?: string;
    wantRendered?: GenerateOptions;
    state?: any;
    only?: boolean;
  }[] = [
    {
      name: 'renders user prompt',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: 'hello {{name}} ({{@state.name}})',
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'user' }],
        model: 'echoModel',
      },
    },
    {
      name: 'renders user prompt with explicit messages override',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: 'hello {{name}} ({{@state.name}})',
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: {
        config: { temperature: 11 },
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
          {
            role: 'model',
            content: [{ text: 'bye' }],
          },
        ],
      },
      wantTextOutput:
        'Echo: hi,bye,hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { role: 'user', content: [{ text: 'hi' }] },
          { content: [{ text: 'bye' }], role: 'model' },
          { content: [{ text: 'hello foo (bar)' }], role: 'user' },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'renders messages prompt with explicit messages override',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        messages: 'hello {{name}} ({{@state.name}})',
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: {
        config: { temperature: 11 },
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
          {
            role: 'model',
            content: [{ text: 'bye' }],
          },
        ],
      },
      wantTextOutput:
        'Echo: hi,bye,hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { role: 'user', content: [{ text: 'hi' }] },
          { content: [{ text: 'bye' }], role: 'model' },
          { content: [{ text: 'hello foo (bar)' }], role: 'user' },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'renders messages {{history}} prompt with explicit messages override',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        messages: 'hello {{name}} ({{@state.name}}){{history}}',
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: {
        config: { temperature: 11 },
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
          {
            role: 'model',
            content: [{ text: 'bye' }],
          },
        ],
      },
      wantTextOutput:
        'Echo: hello foo (bar),hi,bye; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { content: [{ text: 'hello foo (bar)' }], role: 'user' },
          {
            role: 'user',
            content: [{ text: 'hi' }],
            metadata: { purpose: 'history' },
          },
          {
            content: [{ text: 'bye' }],
            role: 'model',
            metadata: { purpose: 'history' },
          },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'renders user prompt from function',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: async (input, { state }) => {
          return `hello ${input.name} (${state.name})`;
        },
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'user' }],
        model: 'echoModel',
      },
    },
    {
      name: 'renders system prompt',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        system: 'hello {{name}} ({{@state.name}})',
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: system: hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'system' }],
        model: 'echoModel',
      },
    },
    {
      name: 'renders system prompt from a function',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        system: async (input, { state }) => {
          return `hello ${input.name} (${state.name})`;
        },
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: system: hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'system' }],
        model: 'echoModel',
      },
    },
    {
      name: 'renders messages from template',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        messages:
          '{{role "system"}}system {{name}}{{role "user"}}user {{@state.name}}',
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: system: system foo,user bar; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { role: 'system', content: [{ text: 'system foo' }] },
          { role: 'user', content: [{ text: 'user bar' }] },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'renders messages',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        messages: [
          { role: 'system', content: [{ text: 'system instructions' }] },
          { role: 'user', content: [{ text: 'user instructions' }] },
        ],
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: system: system instructions,user instructions; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { role: 'system', content: [{ text: 'system instructions' }] },
          { role: 'user', content: [{ text: 'user instructions' }] },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'renders messages from function',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        messages: async (input, { state }) => [
          { role: 'system', content: [{ text: `system ${input.name}` }] },
          { role: 'user', content: [{ text: `user ${state.name}` }] },
        ],
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: system: system foo,user bar; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { role: 'system', content: [{ text: 'system foo' }] },
          { role: 'user', content: [{ text: 'user bar' }] },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'renders system, message and prompt in the same order',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: 'hi {{@state.name}}',
        system: 'hi {{name}}',
        messages: [
          { role: 'user', content: [{ text: `hi` }] },
          { role: 'model', content: [{ text: `bye` }] },
        ],
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: system: hi foo,hi,bye,hi bar; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [
          { role: 'system', content: [{ text: 'hi foo' }] },
          { role: 'user', content: [{ text: 'hi' }] },
          { role: 'model', content: [{ text: 'bye' }] },
          { role: 'user', content: [{ text: 'hi bar' }] },
        ],
        model: 'echoModel',
      },
    },
    {
      name: 'includes docs',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: 'hello {{name}} ({{@state.name}})',
        docs: [Document.fromText('doc a'), Document.fromText('doc b')],
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: hello foo (bar),\n' +
        '\n' +
        'Use the following information to complete your task:\n' +
        '\n' +
        '- [0]: doc a\n' +
        '- [1]: doc b\n' +
        '\n' +
        '; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'user' }],
        model: 'echoModel',
        docs: [Document.fromText('doc a'), Document.fromText('doc b')],
      },
    },
    {
      name: 'includes docs from function',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: 'hello {{name}} ({{@state.name}})',
        docs: async (input, { state }) => [
          Document.fromText(`doc ${input.name}`),
          Document.fromText(`doc ${state.name}`),
        ],
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: hello foo (bar),\n' +
        '\n' +
        'Use the following information to complete your task:\n' +
        '\n' +
        '- [0]: doc foo\n' +
        '- [1]: doc bar\n' +
        '\n' +
        '; config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'user' }],
        model: 'echoModel',
        docs: [Document.fromText('doc foo'), Document.fromText('doc bar')],
      },
    },
    {
      name: 'includes tools',
      prompt: {
        model: 'echoModel',
        name: 'prompt1',
        config: { banana: 'ripe' },
        input: { schema: z.object({ name: z.string() }) },
        prompt: 'hello {{name}} ({{@state.name}})',
        tools: ['toolA'],
      },
      input: { name: 'foo' },
      state: { name: 'bar' },
      inputOptions: { config: { temperature: 11 } },
      wantTextOutput:
        'Echo: hello foo (bar); config: {"banana":"ripe","temperature":11}',
      wantRendered: {
        config: {
          banana: 'ripe',
          temperature: 11,
        },
        messages: [{ content: [{ text: 'hello foo (bar)' }], role: 'user' }],
        model: 'echoModel',
        tools: ['toolA'],
      },
    },
  ];

  basicTests = basicTests.find((t) => t.only)
    ? basicTests.filter((t) => t.only)
    : basicTests;

  for (const test of basicTests) {
    it(test.name, async () => {
      let session: Session | undefined;
      if (test.state) {
        session = new Session(registry, {
          id: '123',
          sessionData: { id: '123', state: test.state },
        });
      }
      const p = definePrompt(registry, test.prompt);

      const { text } = await (session
        ? session.run(() => p(test.input, test.inputOptions))
        : p(test.input, test.inputOptions));

      assert.strictEqual(text, test.wantTextOutput);
      assert.deepStrictEqual(
        stripUndefined(
          await (session
            ? session.run(() => p.render(test.input, test.inputOptions))
            : p.render(test.input, test.inputOptions))
        ),
        test.wantRendered
      );
    });
  }

  it.skip('respects output schema in the definition', async () => {
    const schema1 = z.object({
      puppyName: z.string({ description: 'A cute name for a puppy' }),
    });
    const prompt1 = definePrompt(registry, {
      name: 'prompt1',
      input: { schema: z.string({ description: 'Dog breed' }) },
      output: {
        format: 'json',
        schema: schema1,
      },
      messages: (breed) => {
        return [
          {
            role: 'user',
            content: [{ text: `Pick a name for a ${breed} puppy` }],
          },
        ];
      },
    });
    const generateRequest = await prompt1.render('poodle', {
      model: 'geminiPro',
    });
    assert.equal(generateRequest.output?.schema, schema1);
  });
});

export function defineEchoModel(registry: Registry): ModelAction {
  const model = defineModel(
    registry,
    {
      name: 'echoModel',
    },
    async (request, streamingCallback) => {
      (model as any).__test__lastRequest = request;
      (model as any).__test__lastStreamingCallback = streamingCallback;
      if (streamingCallback) {
        streamingCallback({
          content: [
            {
              text: '3',
            },
          ],
        });
        streamingCallback({
          content: [
            {
              text: '2',
            },
          ],
        });
        streamingCallback({
          content: [
            {
              text: '1',
            },
          ],
        });
      }
      return {
        message: {
          role: 'model',
          content: [
            {
              text:
                'Echo: ' +
                request.messages
                  .map(
                    (m) =>
                      (m.role === 'user' || m.role === 'model'
                        ? ''
                        : `${m.role}: `) + m.content.map((c) => c.text).join()
                  )
                  .join(),
            },
            {
              text: '; config: ' + JSON.stringify(request.config),
            },
          ],
        },
        finishReason: 'stop',
      };
    }
  );
  return model;
}

function stripUndefined(input: any) {
  if (
    input === undefined ||
    Array.isArray(input) ||
    typeof input !== 'object'
  ) {
    return input;
  }
  const out = {};
  for (const key in input) {
    if (input[key] !== undefined) {
      out[key] = stripUndefined(input[key]);
    }
  }
  return out;
}
