################### Ring, ring, ring, ring, ring, ring, ring, 🍌  ☎️ ###################
# Banana phone: a surprisingly useful relay API for LM Studio and other LLM platforms

################### IMPORTS ###################
import asyncio
import os, sys, io
import httpx
import re, json, csv
import logging
import tempfile
import time
import traceback
import pytz
import math
import shutil
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Header, Depends, Query, Response
from fastapi.responses import Response, StreamingResponse, FileResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict 
from starlette.requests import Request
from uuid import uuid4
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from httpx import HTTPStatusError, Timeout
from datetime import datetime
from subprocess import run, PIPE
from typing import Optional, List, Dict


################### ENVIRONMENT VARIABLES ##################
load_dotenv(dotenv_path='.env')

# Pull in our environment variables as configured in the .env, and define defaults in case that fails. The values here are simply fallback defaults, and not the appropriate place to enter custom values. 
api_url = os.getenv("DESTINATION_API", "http://localhost:1234") 
endpoint_completions = os.getenv("ENDPOINT_COMPLETIONS", "/v1/chat/completions")
endpoint_models = os.getenv("ENDPOINT_MODELS", "/v1/models")
api_key = os.getenv('API_KEYS').split(',') 
system_msg = os.getenv("SYSTEM_MSG", "You are a helpful assistant.")
system_override = os.getenv("SYSTEM_OVERRIDE", False)
autostyle = os.getenv("AUTOSTYLE", True)


################### INITIALIZATIONS ###################
api = FastAPI()
timeout = Timeout(connect=30, read=600, write=120, pool=5)
ALLOWED_IPS = ["127.0.0.1"]  # Include 127.0.0.1 for localhost

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# Load models.json for model auto-configurations
with open('models.json') as f:
    model_config_data = json.load(f)

# Extract all model names from the configuration data, compile regex pattern for matching them
all_models = [model for sublist in [config['models'] for config in model_config_data.values() if 'models' in config] for model in sublist]
pattern = "|".join(re.escape(model) for model in all_models)  # re.escape to escape any special characters
regex_pattern = re.compile(pattern)

# CLASSES
class UnexpectedEndpointError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)

class CompletionsRequest(BaseModel):
    prompt: str
    max_tokens: int


################### MIDDLEWARE ###################
@api.middleware("http")
async def api_key_verification_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    if api_key:  # Proceed only if API key(s) are set
        authorization: str = request.headers.get("Authorization")
        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer' and parts[1] in api_key:
                return await call_next(request)
            else:
                logger.warning(f"Invalid or missing API key. Received: {authorization}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "unauthorized",
                            "message": "Invalid or missing API key."
                        }
                    },
                )
        else:
            logger.warning("No API key provided in the request header.")
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "No API key provided. You must provide a valid API key."
                    }
                },
            )

    return await call_next(request)


# Custom function to forward headers and include API key
async def forward_request_with_api_key(url, method, data, headers):
    headers_to_forward = {key: value for key, value in headers.items() if key.lower() in ['content-type']}
    if api_key:
        headers_to_forward["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, json=data, headers=headers_to_forward, timeout=timeout)
        return response


################### CORE ENDPOINTS ###################
# The main attraction.
@api.post("/v1/chat/completions")
async def chat_completions(data: dict, request: Request):
    try:
        logger.info(f"Request for {data}")

        # Forward relevant headers
        headers_to_forward = {key: value for key, value in request.headers.items() if key.lower() in ['content-type', 'authorization']}
        modified_data = data.copy()  # Create a shallow copy of data to avoid modifying the original data object

        is_streaming = modified_data.get("stream", False)
        modified_data.setdefault('temperature', 0.7)

        modified_data = replace_instructions_content_system(modified_data)

       # Check for empty messages and replace with a period
        logger.info("Checking and modifying empty messages")
        messages = modified_data.get('messages', [])
        for message in messages:
            if 'content' in message and message['content'].strip() == '':
                message['content'] = '.'
        logger.info(f"Modified messages: {messages}")


        # Autostyle and format messages if enabled
        if autostyle:
            modified_data['messages'] = await format_messages(modified_data.get('messages', []))

            model_config = model_config_data.get(await fetch_active_model())
            if model_config:
                stops = model_config.get('stops', [])
                modified_data['stop'] = stops
            else:
                logger.error(f"No configuration found for model: {await fetch_active_model()}")
                raise HTTPException(status_code=400, detail=f"No configuration found for model: {await fetch_active_model()}")

        # Create an HTTP client
        client = httpx.AsyncClient()
        logger.info(f"Sending data to destination API: {modified_data}")

        try:
            if is_streaming:
               # Define a generator function to stream content from the destination API
                async def content_generator():
                   # Send the POST request to the destination API and stream the response
                    async with client.stream('POST', f'{api_url}{endpoint_completions}', json=modified_data, headers=headers_to_forward, timeout=timeout) as response:
                        logger.info(f"Received response from destination API: {response.status_code}")
                       # Handle non-200 status codes
                        if response.status_code != 200:
                            await response.aread()  # read the response before accessing content
                            yield f"Error: {response.content}".encode()
                            return
                       # Asynchronously iterate over the response text in chunks
                        async for chunk in response.aiter_text():
                            try:
                               # Check for special 'data: [DONE]' chunk
                                if chunk.strip() == 'data: [DONE]':
                                    logger.info("Chunk stream completed.")
                                    yield chunk.encode()
                                    return

                                json_data = json.loads(chunk.split('data: ', 1)[1])
                                content_value = json_data.get('choices', [{}])[0].get('delta', {}).get('content', None)
                                if content_value is not None:
                                #   print(f"{json.dumps(json_data)}\n\n")
                                    print(f"Received chunk from destination API, with this choices:delta:content: {content_value}")
                                else:
                                    print("Content key not found in the chunk.")
       
                                # Extract the JSON part from the chunk, assuming "data: " prefix is present
                                json_str = chunk.split("data: ", 1)[1]
                                # Parse the JSON string into a Python object
                                chunk_dict = json.loads(json_str)
                                # Remove folder paths and .bin from the "model" field
                                chunk_dict['model'] = re.sub(r'.*\/([^/]+)\.bin$', r'\1', chunk_dict['model'])
                                # Combine the "data: " prefix with the transformed JSON string
                                transformed_chunk = "data: " + json.dumps(chunk_dict)

                               # Yield each chunk to stream it to the client
                                yield transformed_chunk.encode()

                            except GeneratorExit:
                               # Handle client disconnection
                                logger.info("Client disconnected, closing stream.")
                                return

               # Return a StreamingResponse to stream the content to the client in real-time
                return StreamingResponse(content_generator(), media_type="text/plain")

            else:
                response = await forward_request_with_api_key(f'{api_url}{endpoint_completions}', 'POST', modified_data, request.headers)
                
                # Check for an error within the response content
                response_json = response.json()
                if 'error' in response_json:
                    return {"error": response_json['error']}
                
               # Return the JSON response directly
                return response_json

        except asyncio.TimeoutError:
           # Handle request timeouts
            logger.error("The request to the destination API timed out.")
            return {"error": "The request timed out."}
            
        except Exception as e:
           # Handle other exceptions
            logger.error(f"Exception occurred: {e}")
            return {"error": str(e)}

    except Exception as exc:
        logger.error(f"Error processing request: {exc}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(exc))


# Send messages out to the destination API / LM Studio
async def send_request(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    response = await client.request(method, url, **kwargs)
    content = response.json()

    if 'error' in content and 'Unexpected endpoint' in content['error']:
        raise UnexpectedEndpointError(content['error'])

    return Response(content=json.dumps(content), media_type=response.headers.get('content-type'), status_code=response.status_code)

# Check which model is running, then applies the relevant formatting for that model
async def format_messages(messages: list) -> list:
    model_config = model_config_data.get(await fetch_active_model())
    if model_config:
        logger.info(f"Model configuration found: {model_config}")
        user_prefix = model_config['prefix']
        user_suffix = model_config['suffix']
        system_prefix = model_config.get('sysPrefix', '')
        system_suffix = model_config.get('sysSuffix', '')

        if messages:
            logger.info(f"Formatting {len(messages)} messages")

            for i, msg in enumerate(messages):
                if msg.get('role') == 'user':
                    user_message_content = msg['content']
                    modified_user_content = f"{user_prefix}{user_message_content}{user_suffix}"
                    messages[i]['content'] = modified_user_content
                elif msg.get('role') == 'system':
                    system_message_content = msg['content']
                    modified_system_content = f"{system_prefix}{system_message_content}{system_suffix}"
                    messages[i]['content'] = modified_system_content

        else:
            logger.warning("No messages provided for formatting")

        return messages
    else:
        error_message = f"No configuration found for model: {await fetch_active_model()}"
        logger.error(error_message)
        raise HTTPException(status_code=400, detail=error_message)

@api.options("/v1/chat/completions")
async def relay_options_for_chat_completions(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{api_url}/v1/chat/completions",
            headers=request.headers
        )
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

# This is included for legacy compatibility with older clients. 
@api.post("/v1/completions")
async def completions(request_model: CompletionsRequest, request: Request):
    print(request_model)
   # Reformatting the request payload to match the /v1/chat/completions endpoint
    chat_completions_payload = {
        "messages": [
            {
                "role": "user",
                "content": request_model.prompt
            }
        ],
        "max_tokens": request_model.max_tokens if request_model.max_tokens > 0 else -1,
        "stream": False
    }

    # Directly call the existing /v1/chat/completions endpoint function
    chat_response = await chat_completions(chat_completions_payload, request)#

    # Extracting and reformatting the relevant data
    formatted_response = {
        "id": chat_response['id'].replace('chatcmpl', 'cmpl'),
        "object": "text_completion",
        "created": chat_response['created'],
        "model": chat_response['model'].split('/')[-1].split('.')[0], # Extract model name from path
        "choices": [
            {
                "text": chat_response['choices'][0]['message']['content'],
                "index": chat_response['choices'][0]['index'],
                "logprobs": None,
                "finish_reason": chat_response['choices'][0]['finish_reason']
            }
        ],
        "usage": chat_response['usage']
    }

   # Returning the response to the requester
    return formatted_response


################### ACTIVE HELPERS ###################
# Add the relevant 'stop' commands to message payloads
def apply_stops(data: dict, stops: list) -> dict:
    if stops:
        data["stop"] = stops
    return data

# Replace the system message the system prompt
def replace_instructions_content_system(data: dict) -> dict:
    messages = data.get('messages', [])

    # if messages is empty, there's nothing to do
    if not messages:
        return data

    # if first message isn't a system message, we inject system_msg ahead of it
    elif messages[0].get('role') != 'system':
        messages.insert(0, {'role': 'system', 'name': 'instructions', 'content': system_msg})

    # even if the first message is already a system message, we will replace it if system_override is enabled
    elif system_override:
        messages[0] = {'role': 'system', 'name': 'instructions', 'content': system_msg}
    
    data['messages'] = messages  # Update the messages back into data
    return data


################### PASSIVE HELPERS ###################
# Dependency to verify the API key
async def verify_api_key(authorization: Optional[str] = Header(None)):
    # Check if an API key is set in the .env file
    if api_key:
        if authorization:
            scheme, _, token = authorization.partition(' ')
            if scheme.lower() == 'bearer' and token == api_key:
                return  # Correct API key provided
            else:
                # Incorrect API key provided
                detail_message = f"Incorrect API key provided: {token}" if token else "No API key provided"
                raise HTTPException(status_code=401, detail=detail_message)
        else:
            # No API key provided in the request header
            raise HTTPException(status_code=401, detail="No API key provided")
    else:
        # No API key required; allow the request to proceed
        return


# This active model is needed to for autostyle to function.
async def fetch_active_model():
    api_url_with_protocol = 'http://' + api_url if not api_url.startswith(('http://', 'https://')) else api_url
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'{api_url_with_protocol}/v1/models')
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx and 5xx)
            active_model_id = json.loads(response.content)["data"][0]["id"]
            logger.info(f"Active model ID fetched: {active_model_id}")
        except httpx.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            return "default"  # Return the default configuration key on error
        except KeyError as key_err:
            logger.error(f"Key error in parsing response: {key_err}")
            return "default"  # Return the default configuration key on error
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON decode error: {json_err}")
            return "default"  # Return the default configuration key on error
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "default"  # Return the default configuration key on error

        for config_name, config_data in model_config_data.items():
            for model_name in config_data.get('models', []):
                if model_name in active_model_id:
                    logger.info(f"Match found for model '{model_name}' under configuration '{config_name}'")
                    return config_name

        logger.warning(f"Model name {active_model_id} does not match any configuration. Using default.")
        return "default"  # Return the default configuration key if no match found


# Query the available models on the destination API. For LM Studio, it will only return the active model.
@api.get("/v1/models")
async def models():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'{api_url}{endpoint_models}', timeout=30.0)
           # Print the response content to debug the issue
            print("Response content:", response.content)
            
           # Update the "id" value in the response
            data = json.loads(response.content)
            data["data"][0]["id"] = re.sub(r'.*\/([^/]+)\.bin$', r'\1', data["data"][0]["id"])
            
           # Convert the updated data back to a JSON string
            modified_data = json.dumps(data)

            logger.debug(f"api_url: {api_url}")
            logger.debug(f"endpoint_models: {endpoint_models}")
            return json.loads(modified_data)

        except httpx.HTTPError:
            logger.error("Error retrieving models from destination API.")
            return {"error": "Failed to retrieve models from the destination API."}

        except Exception as e:
           # Handle exceptions or errors that may occur during the request
            print("Request error:", str(e))
            return {"error": f"Request error: {str(e)}"}


@api.options("/v1/models")
async def relay_options_for_models():
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{api_url}/v1/chat/completions",
            headers=request.headers
        )
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )


@api.get("/favicon.ico")
async def favicon():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'{api_url}/favicon.ico', timeout=30.0)
           # Check if the response is not empty (you may need to adjust the condition depending on the API)
            if response.status_code == 200 and response.content:
                return Response(response.content, media_type=response.headers.get('content-type'), status_code=response.status_code)
        except httpx.HTTPError:
            logger.error("Error retrieving favicon from destination API. Using local fallback.")
    
    return FileResponse("favicon.ico")


@api.get("/v1/chat/completions")
async def get_completions (data: dict, request: Request):
    return request 


@api.head("/")
async def read_root():
    return {}


@api.get("/")
async def root():
    return {"message": "Ring, ring, ring, ring, ring, ring, ring. \n\n. Banana phone."}


@api.exception_handler(UnexpectedEndpointError)
async def unexpected_endpoint_error_handler(request: Request, exc: UnexpectedEndpointError):
    return Response(
        content=json.dumps({
            'error': {
                'message': exc.detail,
                'type': 'invalid_request_error',
                'param': None,
                'code': None
            }
        }),
        media_type="application/json",
        status_code=exc.status_code
    )


@api.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})