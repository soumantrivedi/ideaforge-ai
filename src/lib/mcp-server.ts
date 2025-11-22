import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { supabase } from './supabase';

export class MCPServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'idea-scribe-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: [
        {
          uri: 'chat://history',
          name: 'Chat History',
          description: 'Access to chat conversation history',
          mimeType: 'application/json',
        },
        {
          uri: 'knowledge://documents',
          name: 'Knowledge Base',
          description: 'RAG knowledge base documents',
          mimeType: 'application/json',
        },
        {
          uri: 'projects://list',
          name: 'Projects',
          description: 'User projects and PRDs',
          mimeType: 'application/json',
        },
      ],
    }));

    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const uri = request.params.uri;

      if (uri === 'chat://history') {
        const { data, error } = await supabase
          .from('chat_messages')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(50);

        if (error) throw new Error(error.message);

        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      if (uri === 'knowledge://documents') {
        const { data, error } = await supabase
          .from('knowledge_base')
          .select('*')
          .order('created_at', { ascending: false });

        if (error) throw new Error(error.message);

        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      if (uri === 'projects://list') {
        const { data, error } = await supabase
          .from('projects')
          .select('*')
          .order('created_at', { ascending: false });

        if (error) throw new Error(error.message);

        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      throw new Error(`Unknown resource: ${uri}`);
    });

    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'search_knowledge_base',
          description: 'Search the RAG knowledge base for relevant information',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'The search query',
              },
              limit: {
                type: 'number',
                description: 'Maximum number of results',
                default: 5,
              },
            },
            required: ['query'],
          },
        },
        {
          name: 'save_to_knowledge_base',
          description: 'Save information to the knowledge base',
          inputSchema: {
            type: 'object',
            properties: {
              title: {
                type: 'string',
                description: 'Document title',
              },
              content: {
                type: 'string',
                description: 'Document content',
              },
              metadata: {
                type: 'object',
                description: 'Additional metadata',
              },
            },
            required: ['title', 'content'],
          },
        },
        {
          name: 'get_chat_context',
          description: 'Retrieve recent chat context for better responses',
          inputSchema: {
            type: 'object',
            properties: {
              conversationId: {
                type: 'string',
                description: 'Conversation ID',
              },
              limit: {
                type: 'number',
                description: 'Number of messages to retrieve',
                default: 10,
              },
            },
            required: ['conversationId'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      if (name === 'search_knowledge_base') {
        const { query, limit = 5 } = args as { query: string; limit?: number };

        const { data, error } = await supabase
          .from('knowledge_base')
          .select('*')
          .textSearch('content', query)
          .limit(limit);

        if (error) throw new Error(error.message);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      }

      if (name === 'save_to_knowledge_base') {
        const { title, content, metadata = {} } = args as {
          title: string;
          content: string;
          metadata?: Record<string, unknown>;
        };

        const { data, error } = await supabase
          .from('knowledge_base')
          .insert({
            title,
            content,
            metadata,
          })
          .select()
          .single();

        if (error) throw new Error(error.message);

        return {
          content: [
            {
              type: 'text',
              text: `Saved document: ${data.title}`,
            },
          ],
        };
      }

      if (name === 'get_chat_context') {
        const { conversationId, limit = 10 } = args as {
          conversationId: string;
          limit?: number;
        };

        const { data, error } = await supabase
          .from('chat_messages')
          .select('*')
          .eq('conversation_id', conversationId)
          .order('created_at', { ascending: false })
          .limit(limit);

        if (error) throw new Error(error.message);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(data.reverse(), null, 2),
            },
          ],
        };
      }

      throw new Error(`Unknown tool: ${name}`);
    });
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log('MCP Server started');
  }
}
