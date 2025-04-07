from typing import Optional
from fastapi import FastAPI
import gradio as gr
from openai import AsyncAzureOpenAI, AzureOpenAI, OpenAI
import os
from dotenv import load_dotenv
import openai
from openai.types.chat import ChatCompletion, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionMessage, ChatCompletionMessageParam
from pydantic import BaseModel, Field, ValidationError
from openai import pydantic_function_tool
from typing import List
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizableTextQuery

load_dotenv()

# Variables not used here do not need to be updated in your .env file

endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_ADMIN_KEY")) if os.getenv("AZURE_SEARCH_ADMIN_KEY") else DefaultAzureCredential()
index_namespace = os.getenv("AZURE_SEARCH_INDEX_NAMESPACE", "index-and-chat")
blob_connection_string = os.environ["BLOB_CONNECTION_STRING"]

# search blob datasource connection string is optional - defaults to blob connection string

# This field is only necessary if you are using MI to connect to the data source

# https://learn.microsoft.com/azure/search/search-howto-indexing-azure-blob-storage#supported-credentials-and-connection-strings

search_blob_connection_string = os.getenv("SEARCH_BLOB_DATASOURCE_CONNECTION_STRING", blob_connection_string)
blob_container_name = os.getenv("BLOB_CONTAINER_NAME", "index-and-chat")
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
azure_openai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]
azure_openai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
azure_openai_model_name = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")
azure_openai_model_dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 3072))
azure_openai_chat_deployment = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
azure_ai_services_endpoint = os.environ["AZURE_AI_SERVICES_ENDPOINT"]
# This field is only necessary if you want to authenticate using a key to Azure AI Services
azure_ai_services_key = os.getenv("AZURE_AI_SERVICES_KEY", "")
# Deepest nesting level in markdown that should be considered. See https://learn.microsoft.com/azure/search/cognitive-search-skill-document-intelligence-layout to learn more
document_layout_depth = os.getenv("LAYOUT_MARKDOWN_HEADER_DEPTH", "h3")
azure_openai_chat_deployment = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
parent_index_client = SearchClient(endpoint=endpoint, index_name=f"{index_namespace}-parent", credential=credential)
child_index_client = SearchClient(endpoint=endpoint, index_name=f"{index_namespace}-child", credential=credential)
assistant_system_message = "You are a helpful assistant that answers queries. You do not have access to the internet, but you can use documents in the chat history to answer the question. If the documents do not contain the answer, say 'I don't know'. You must cite your answer with the titles of the documents used. If you are unsure, say 'I don't know'."

app = FastAPI()

# Initialize client

client = AsyncAzureOpenAI(
    api_version=azure_openai_api_version,
    azure_endpoint=azure_openai_endpoint,
    api_key=azure_openai_key,
    azure_ad_token_provider=token_provider if not azure_openai_key else None
)

class ExtractTitles(BaseModel):
    """Extracts titles from a query to use in a search filter."""
    titles: Optional[List[str]] = Field(..., description="List of titles extracted from the query. Complete file names are considered titles. If there are no titles in the query, provide an empty list. For example, in the query 'Find the report on sales and the summary of the meeting using 'myreport.pdf', the titles would be ['myreport.pdf']. If no titles are found, return an empty list.")

async def extract_titles(query: str) -> List[str]:
   response: ChatCompletion = await client.chat.completions.create(
      model=azure_openai_chat_deployment,
      messages=[
         ChatCompletionSystemMessageParam(role="system", content="You are a helpful assistant that extracts titles from user queries."),
         ChatCompletionUserMessageParam(role="user", content=f"Extract the titles from the following query: '{query}'"),
      ],

      tools=[openai.pydantic_function_tool(ExtractTitles)]

   )

   if response.choices[0].message.tool_calls:
      arguments = response.choices[0].message.tool_calls[0].function.arguments
      try:
         # Load the tool call arguments into the pydantic model ExtractTitles
         extraction = ExtractTitles.model_validate_json(arguments)
         return extraction.titles or []
      except ValidationError:
         return []
   return []

async def chat(message, history=[]):
    formatted_results = ""
    titles = []
    #Get it from func params
    include_full_documents = True
    if include_full_documents:
      # Step 1: Extract titles from the query
      titles = await extract_titles(message)
      # Step 2: If we found titles, include them in the query of the parent index
      if titles:
         results = await parent_index_client.search(
            filter=" or ".join([f"title eq '{title}'" for title in titles]),  # Filter by titles, must be exact match
            top=len(titles),  # Limit to top results
            select=["title", "content"])
         formatted_results = "\n".join([f"{result['title']}\n{result['content']}" async for result in results])

    if len(formatted_results) == 0:
      # If no titles were found or no results were returned, search the child index with a vectorized query
      results = await child_index_client.search(
         search_text=message,
         vector_queries=[VectorizableTextQuery(text=message, k_nearest_neighbors=50, fields="vector")],  # Use vector search with k nearest neighbors
         query_type="semantic",
         semantic_configuration_name="my-semantic-config",  # Use the semantic configuration created earlier
         top=5,  # Limit to top 5 results
         select=["title", "chunk"]
      )

      formatted_results = "\n".join([f"{result['title']}\n{result['chunk']}" async for result in results])
    
    query_message = f"Answer the following query: {message}\nRelevant documents: {formatted_results}"

    history = history + [ ChatCompletionUserMessageParam(role="user", content=query_message) ] if history else [
        ChatCompletionSystemMessageParam(role="system", content=assistant_system_message),
        ChatCompletionUserMessageParam(role="user", content=query_message),
    ] 

    response: ChatCompletion = await client.chat.completions.create(
      model=azure_openai_chat_deployment,
      messages=history
    ) 

    bot_reply: ChatCompletionMessage = response.choices[0].message
    if titles:
      bot_reply.content += f"\nTitles used for the answer: {', '.join(titles)}"
    return bot_reply.content

CSS="""
    .gradio-container { height: 100vh; width: 100vw; } /* Set the height and width of the container */
    .gradio-chatbot { height: 100%; width: 100%; } /* Set the height and width of the chatbot */
    .gradio-chatbot .message { max-width: 80%; } /* Set the max width of the messages */
    .gradio-chatbot .message.user { background-color: #4CAF50; color: white; } /* User message color */
    footer { visibility: hidden} /* Hide the footer */"""

with gr.Blocks(css=CSS) as gr_app:  # Apply style to the container

    gr.Markdown("<h1 style='font-size: 50px; text-align: center; color: grey ;'>Ask a Question</h1>")
    gr.Markdown("<br>")
    gr.Markdown("<br>")

    with gr.Row():
       gr.ChatInterface(
        chat,
        type="messages",
        theme="ocean",
        save_history=True,
        css=CSS  # Apply CSS to the ChatInterface\
    )


app = gr.mount_gradio_app(app, gr_app, path="/")

 