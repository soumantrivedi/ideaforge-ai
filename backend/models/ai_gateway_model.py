"""
Agno-compatible model wrapper for AI Gateway.
This allows AI Gateway to be used with Agno agents seamlessly.
"""
from typing import Optional, List, Dict, Any, AsyncIterator, Iterator, Union, Type
import structlog
import asyncio
from backend.services.ai_gateway_client import AIGatewayClient

logger = structlog.get_logger()

# Import Agno Model base class and related types
try:
    from agno.models.base import Model
    from agno.models.message import Message
    from agno.models.response import ModelResponse
    AGNO_MODEL_AVAILABLE = True
except ImportError:
    # Fallback if Agno is not available
    Model = object
    Message = Any
    ModelResponse = Any
    AGNO_MODEL_AVAILABLE = False
    logger.warning("agno_models_base_not_available", message="AIGatewayModel will not be recognized as Agno model")


class AIGatewayModel(Model):
    """
    Agno-compatible model wrapper for AI Gateway.
    Implements the interface expected by Agno agents.
    """
    
    def __init__(
        self,
        id: str,
        client: AIGatewayClient,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize AI Gateway model.
        
        Args:
            id: Model identifier (e.g., 'gpt-4', 'claude-3-sonnet', 'gpt-5.1')
            client: AIGatewayClient instance
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate (for older models)
            max_completion_tokens: Maximum completion tokens (for GPT-5.1 models)
            **kwargs: Additional parameters
        """
        self.id = id
        self.model = id  # Alias for compatibility
        self.client = client
        self.temperature = temperature
        # GPT-5.1 models use max_completion_tokens, others use max_tokens
        if max_completion_tokens is not None:
            self.max_completion_tokens = max_completion_tokens
            self.max_tokens = None
        else:
            self.max_tokens = max_tokens or kwargs.get('max_tokens', 2000)
            self.max_completion_tokens = None
        self.kwargs = kwargs
        
        logger.info("ai_gateway_model_initialized", model_id=id, max_tokens=self.max_tokens, max_completion_tokens=self.max_completion_tokens)
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generate a response from the model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        try:
            # Merge instance parameters with call parameters
            temperature = kwargs.get('temperature', self.temperature)
            
            # Determine which token parameter to use based on model
            completion_params = {}
            if self.max_completion_tokens is not None or kwargs.get('max_completion_tokens'):
                # GPT-5.1 models use max_completion_tokens
                max_completion_tokens = kwargs.get('max_completion_tokens', self.max_completion_tokens)
                if max_completion_tokens:
                    completion_params['max_completion_tokens'] = max_completion_tokens
            else:
                # Other models use max_tokens
                max_tokens = kwargs.get('max_tokens', self.max_tokens)
                if max_tokens:
                    completion_params['max_tokens'] = max_tokens
            
            # Format messages for AI Gateway
            formatted_messages = self._format_messages(messages)
            
            response = await self.client.chat_completion(
                model=self.id,
                messages=formatted_messages,
                temperature=temperature,
                stream=False,
                **completion_params,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens', 'max_completion_tokens']}
            )
            
            # Extract response content
            if isinstance(response, dict):
                choices = response.get('choices', [])
                if choices and len(choices) > 0:
                    message = choices[0].get('message', {})
                    content = message.get('content', '')
                    return content
                else:
                    logger.warning("ai_gateway_no_choices", response=response)
                    return ""
            else:
                logger.warning("ai_gateway_unexpected_response", response_type=type(response))
                return str(response)
                
        except Exception as e:
            logger.error("ai_gateway_generate_error", model=self.id, error=str(e))
            raise
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream a response from the model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Yields:
            Text chunks as they are generated
        """
        try:
            # Merge instance parameters with call parameters
            temperature = kwargs.get('temperature', self.temperature)
            
            # Determine which token parameter to use based on model
            completion_params = {}
            if self.max_completion_tokens is not None or kwargs.get('max_completion_tokens'):
                # GPT-5.1 models use max_completion_tokens
                max_completion_tokens = kwargs.get('max_completion_tokens', self.max_completion_tokens)
                if max_completion_tokens:
                    completion_params['max_completion_tokens'] = max_completion_tokens
            else:
                # Other models use max_tokens
                max_tokens = kwargs.get('max_tokens', self.max_tokens)
                if max_tokens:
                    completion_params['max_tokens'] = max_tokens
            
            # Format messages for AI Gateway
            formatted_messages = self._format_messages(messages)
            
            # Note: AI Gateway client needs to support streaming
            # For now, we'll use non-streaming and yield the full response
            # TODO: Implement proper streaming when AI Gateway client supports it
            response = await self.client.chat_completion(
                model=self.id,
                messages=formatted_messages,
                temperature=temperature,
                stream=True,
                **completion_params,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens', 'max_completion_tokens']}
            )
            
            # Handle streaming response
            if hasattr(response, '__aiter__'):
                async for chunk in response:
                    if isinstance(chunk, dict):
                        choices = chunk.get('choices', [])
                        if choices:
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
            else:
                # Fallback: yield full response if streaming not supported
                full_response = await self.generate(messages, **kwargs)
                yield full_response
                
        except Exception as e:
            logger.error("ai_gateway_stream_error", model=self.id, error=str(e))
            raise
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Format messages for AI Gateway API.
        Converts Agno message format to AI Gateway format.
        """
        formatted = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Map roles to AI Gateway format
            if role == 'system':
                # System messages are typically handled separately
                # For AI Gateway, we'll include them as user messages with a prefix
                formatted.append({
                    'role': 'user',
                    'content': f"[System]: {content}"
                })
            elif role in ['user', 'assistant']:
                formatted.append({
                    'role': role,
                    'content': content
                })
            else:
                # Default to user role
                formatted.append({
                    'role': 'user',
                    'content': content
                })
        
        return formatted
    
    def _convert_agno_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        Convert Agno Message objects to dict format for AI Gateway API.
        
        Args:
            messages: List of Agno Message objects
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        formatted = []
        for msg in messages:
            # Agno Message objects have role and content attributes
            role = getattr(msg, 'role', 'user')
            content = getattr(msg, 'content', str(msg))
            
            # Map Agno roles to AI Gateway format
            if role == 'system':
                formatted.append({
                    'role': 'user',
                    'content': f"[System]: {content}"
                })
            elif role in ['user', 'assistant']:
                formatted.append({
                    'role': role,
                    'content': content
                })
            else:
                formatted.append({
                    'role': 'user',
                    'content': content
                })
        
        return formatted
    
    def _parse_provider_response(
        self,
        response: Dict[str, Any],
        response_format: Optional[Union[Dict, Type]] = None
    ) -> ModelResponse:
        """
        Parse AI Gateway response into Agno ModelResponse.
        
        Args:
            response: Response dict from AI Gateway API
            response_format: Optional response format (for structured output)
            
        Returns:
            Agno ModelResponse object
        """
        try:
            # Extract content from response
            choices = response.get('choices', [])
            if not choices:
                logger.warning("ai_gateway_no_choices_in_response", response=response)
                content = ""
            else:
                message = choices[0].get('message', {})
                content = message.get('content', '')
                
                # Handle tool calls if present
                tool_calls = message.get('tool_calls')
                if tool_calls:
                    # Tool calls are handled by Agno framework
                    pass
            
            # Extract usage information if available
            usage = response.get('usage', {})
            
            # Extract finish reason
            finish_reason = choices[0].get('finish_reason') if choices else None
            
            # Create ModelResponse with all available fields
            # ModelResponse accepts: content, role, parsed, response_usage, provider_data, etc.
            response_kwargs = {
                'content': content,
                'role': 'assistant',
            }
            
            # Add usage information as response_usage (Metrics object)
            if usage:
                try:
                    from agno.models.metrics import Metrics
                    response_kwargs['response_usage'] = Metrics(
                        prompt_tokens=usage.get('prompt_tokens', 0),
                        completion_tokens=usage.get('completion_tokens', 0),
                        total_tokens=usage.get('total_tokens', 0)
                    )
                except:
                    # Fallback: store in provider_data if Metrics not available
                    response_kwargs['provider_data'] = {
                        'usage': usage,
                        'model': self.id,
                        'finish_reason': finish_reason
                    }
            else:
                response_kwargs['provider_data'] = {
                    'model': self.id,
                    'finish_reason': finish_reason
                }
            
            return ModelResponse(**response_kwargs)
            
        except Exception as e:
            logger.error("ai_gateway_parse_response_error", error=str(e), response=response)
            # Return a basic ModelResponse even if parsing fails
            try:
                content = str(response.get('choices', [{}])[0].get('message', {}).get('content', ''))
            except:
                content = ""
            return ModelResponse(content=content, model=self.id)
    
    def _parse_provider_response_delta(
        self,
        response_delta: Dict[str, Any]
    ) -> ModelResponse:
        """
        Parse AI Gateway streaming delta chunk into Agno ModelResponse.
        
        Args:
            response_delta: Delta chunk dict from AI Gateway streaming API
            
        Returns:
            Agno ModelResponse object with delta content
        """
        try:
            choices = response_delta.get('choices', [])
            if not choices:
                content = ""
                finish_reason = None
            else:
                delta = choices[0].get('delta', {})
                content = delta.get('content', '')
                finish_reason = choices[0].get('finish_reason')
                
                # Handle tool call deltas if present
                tool_calls = delta.get('tool_calls')
                if tool_calls:
                    # Tool calls are handled by Agno framework
                    pass
            
            # Create ModelResponse for delta chunk
            response_kwargs = {
                'content': content,
                'role': 'assistant',
            }
            
            # Store metadata in provider_data
            response_kwargs['provider_data'] = {
                'model': self.id,
                'finish_reason': finish_reason,
                'delta': True
            }
            
            return ModelResponse(**response_kwargs)
            
        except Exception as e:
            logger.error("ai_gateway_parse_delta_error", error=str(e), delta=response_delta)
            return ModelResponse(content="", model=self.id)
    
    def invoke(
        self,
        messages: List[Message],
        assistant_message: Optional[Message] = None,
        response_format: Optional[Union[Dict, Type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[Any] = None,
        compress_tool_results: bool = False
    ) -> ModelResponse:
        """
        Synchronous invoke method for Agno compatibility.
        Note: This runs the async method in an event loop.
        
        Args:
            messages: List of Agno Message objects
            assistant_message: Optional assistant message (for continuation)
            response_format: Optional response format (for structured output)
            tools: Optional list of tools
            tool_choice: Optional tool choice configuration
            run_response: Optional run response context
            compress_tool_results: Whether to compress tool results
            
        Returns:
            Agno ModelResponse object
        """
        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.ainvoke(
                messages=messages,
                assistant_message=assistant_message,
                response_format=response_format,
                tools=tools,
                tool_choice=tool_choice,
                run_response=run_response,
                compress_tool_results=compress_tool_results
            )
        )
    
    async def ainvoke(
        self,
        messages: List[Message],
        assistant_message: Optional[Message] = None,
        response_format: Optional[Union[Dict, Type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[Any] = None,
        compress_tool_results: bool = False
    ) -> ModelResponse:
        """
        Async invoke method for Agno compatibility.
        
        Args:
            messages: List of Agno Message objects
            assistant_message: Optional assistant message (for continuation)
            response_format: Optional response format (for structured output)
            tools: Optional list of tools
            tool_choice: Optional tool choice configuration
            run_response: Optional run response context
            compress_tool_results: Whether to compress tool results
            
        Returns:
            Agno ModelResponse object
        """
        try:
            # Convert Agno messages to dict format
            formatted_messages = self._convert_agno_messages(messages)
            
            # Add assistant message if provided
            if assistant_message:
                assistant_dict = self._convert_agno_messages([assistant_message])
                formatted_messages.extend(assistant_dict)
            
            # Prepare completion parameters
            completion_params = {}
            if self.max_completion_tokens is not None:
                completion_params['max_completion_tokens'] = self.max_completion_tokens
            elif self.max_tokens is not None:
                completion_params['max_tokens'] = self.max_tokens
            
            # Add tools if provided
            if tools:
                completion_params['tools'] = tools
            if tool_choice:
                completion_params['tool_choice'] = tool_choice
            
            # Add response format if provided (for structured output)
            if response_format:
                completion_params['response_format'] = response_format
            
            # Call AI Gateway API
            response = await self.client.chat_completion(
                model=self.id,
                messages=formatted_messages,
                temperature=self.temperature,
                stream=False,
                **completion_params
            )
            
            # Parse response into ModelResponse
            return self._parse_provider_response(response, response_format)
            
        except Exception as e:
            logger.error("ai_gateway_ainvoke_error", model=self.id, error=str(e))
            raise
    
    def invoke_stream(
        self,
        messages: List[Message],
        assistant_message: Optional[Message] = None,
        response_format: Optional[Union[Dict, Type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[Any] = None,
        compress_tool_results: bool = False
    ) -> Iterator[ModelResponse]:
        """
        Synchronous streaming invoke method for Agno compatibility.
        Note: This runs the async method in an event loop.
        
        Args:
            messages: List of Agno Message objects
            assistant_message: Optional assistant message (for continuation)
            response_format: Optional response format (for structured output)
            tools: Optional list of tools
            tool_choice: Optional tool choice configuration
            run_response: Optional run response context
            compress_tool_results: Whether to compress tool results
            
        Yields:
            Agno ModelResponse objects (delta chunks)
        """
        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async_gen = self.ainvoke_stream(
            messages=messages,
            assistant_message=assistant_message,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            run_response=run_response,
            compress_tool_results=compress_tool_results
        )
        
        # Convert async generator to sync iterator
        while True:
            try:
                yield loop.run_until_complete(async_gen.__anext__())
            except StopAsyncIteration:
                break
    
    async def ainvoke_stream(
        self,
        messages: List[Message],
        assistant_message: Optional[Message] = None,
        response_format: Optional[Union[Dict, Type]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[Any] = None,
        compress_tool_results: bool = False
    ) -> AsyncIterator[ModelResponse]:
        """
        Async streaming invoke method for Agno compatibility.
        
        Args:
            messages: List of Agno Message objects
            assistant_message: Optional assistant message (for continuation)
            response_format: Optional response format (for structured output)
            tools: Optional list of tools
            tool_choice: Optional tool choice configuration
            run_response: Optional run response context
            compress_tool_results: Whether to compress tool results
            
        Yields:
            Agno ModelResponse objects (delta chunks)
        """
        try:
            # Convert Agno messages to dict format
            formatted_messages = self._convert_agno_messages(messages)
            
            # Add assistant message if provided
            if assistant_message:
                assistant_dict = self._convert_agno_messages([assistant_message])
                formatted_messages.extend(assistant_dict)
            
            # Prepare completion parameters
            completion_params = {}
            if self.max_completion_tokens is not None:
                completion_params['max_completion_tokens'] = self.max_completion_tokens
            elif self.max_tokens is not None:
                completion_params['max_tokens'] = self.max_tokens
            
            # Add tools if provided
            if tools:
                completion_params['tools'] = tools
            if tool_choice:
                completion_params['tool_choice'] = tool_choice
            
            # Add response format if provided
            if response_format:
                completion_params['response_format'] = response_format
            
            # Call AI Gateway API with streaming
            response_stream = await self.client.chat_completion(
                model=self.id,
                messages=formatted_messages,
                temperature=self.temperature,
                stream=True,
                **completion_params
            )
            
            # Handle streaming response
            if hasattr(response_stream, '__aiter__'):
                async for chunk in response_stream:
                    if isinstance(chunk, dict):
                        # Parse delta chunk into ModelResponse
                        delta_response = self._parse_provider_response_delta(chunk)
                        yield delta_response
                    else:
                        logger.warning("ai_gateway_unexpected_chunk_type", chunk_type=type(chunk))
            else:
                # Fallback: if streaming not supported, yield full response
                full_response = await self.ainvoke(
                    messages=messages,
                    assistant_message=assistant_message,
                    response_format=response_format,
                    tools=tools,
                    tool_choice=tool_choice,
                    run_response=run_response,
                    compress_tool_results=compress_tool_results
                )
                yield full_response
                
        except Exception as e:
            logger.error("ai_gateway_ainvoke_stream_error", model=self.id, error=str(e))
            raise
    
    def __str__(self) -> str:
        return f"AIGatewayModel(id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()

