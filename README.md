# Build RAG with Azure AI Search & Azure OpenAI

This repository provides a way to build [RAG solution](https://learn.microsoft.com/azure/search/tutorial-rag-build-solution) on your data powered by Azure AI Search & Azure OpenAI
 
## Architecture Diagram

![RAG Architecture](https://github.com/aggarwalsmicrosoft/azure-index-and-chat/blob/main/Images/Architecture.png)

## Steps to install

Step 1 : Run through the python notebook "index-and-chat.ipynb" to set up the Azure Blob Storage , Azure AI Search , Azure OpenAI & Azure AI Services multiservices account

Step 2 : Set up the Gradio App with Python FastAPI to deploy to Azure App service

- In the Azure portal , create an [Azure App service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-arm-template?pivots=platform-linux) resource

  - Sign in to the Azure portal, type app services in the search bar at the top of the portal. Choose the option called App Services under the Services heading on the menu that shows up below the search bar.
  - On the Create Web App page, fill out the form as follows.

    Resource Group → Select Create new and use your RG name.

    Name → you-app-name. This name must be unique across Azure.

    Runtime stack → Python 3.12.

    Region → Azure region where you hosted other services.

    App Service Plan → Under Pricing plan, select Explore pricing plans to select a different App Service plan.

    ![ ](https://github.com/aggarwalsmicrosoft/azure-index-and-chat/blob/main/Images/Img1.png)

    ![ ](https://github.com/aggarwalsmicrosoft/azure-index-and-chat/blob/main/Images/Img2.png)

- Make a new folder called "Deploy" and open it in VSCode. Paste the .env , app.py and requirements.txt files in this folder.

- Create a virtual environment in Visual Studio Code - Create a virtual environment so that you can install the dependencies in isolation.

  - In Visual Studio Code, open the folder containing index-and-chat.ipynb
  - Press Ctrl-shift-P to open the command palette, search for "Python: Create Environment", and then select `Venv` to create a virtual environment in the current workspace.
  - Select requirements.txt for the dependencies.

   It takes several minutes to create the environment. When the environment is ready, continue to the next step.

- Install the required python packages and freeze the requirements.txt file

```bash
pip install gradio
pip install fastapi
pip install gunicorn 

pip freeze > requirements.txt
```

- Now in VSCode sign to Azure using the command palette (Ctrl + Shift + P)

![ ](https://github.com/aggarwalsmicrosoft/azure-index-and-chat/blob/main/Images/Img3.png)

- Now go to Azure extension and your Web App resource that you made earlier > Right Click > Deploy to Web App

![ ](https://github.com/aggarwalsmicrosoft/azure-index-and-chat/blob/main/Images/Img4.png)

- After the deployment is finished, go to the Azure portal, search for the Web Service, select the Settings > Environment Variables and input environment variables. Type the secret name and value as they appear in your local settings in VSCode.

- To finish, go to Settings > Configuration > Startup Command and type in this command

```bash
uvicorn app:app --host 0.0.0.0 --port 8000

or 

python -m gunicorn app:app -k uvicorn.workers.UvicornWorker
```

## Documentation

- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)

  - [Retrieval Augmented Generation (RAG) in Azure AI Search](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview)
  - [Vector search overview](https://learn.microsoft.com/azure/search/vector-search-overview)
  - [Hybrid search overview](https://learn.microsoft.com/azure/search/hybrid-search-overview)
  - [Create a vector index](https://learn.microsoft.com/azure/search/vector-search-how-to-create-index)
  - [Query a vector index](https://learn.microsoft.com/azure/search/vector-search-how-to-query)
  - [Vector search algorithms](https://learn.microsoft.com/azure/search/vector-search-ranking)
  - [REST API reference](https://learn.microsoft.com/rest/api/searchservice/)

- [Azure OpenAI Service Documentation](https://learn.microsoft.com/azure/cognitive-services/openai/)

## Reference
- [Azure Search Vector Samples](https://github.com/Azure/azure-search-vector-samples/tree/main)
- [Azure Search Vector Samples-Python](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-python/code/indexers) by [Matt Gotteiner](https://github.com/mattgotteiner) 
- [Azure Search OpenAI Demo](https://github.com/Azure-Samples/azure-search-openai-demo)
- [Retrieval Augmented Generation (RAG)](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)
- [Step-by-Step guide for deploying Gradio App with FastAPI](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/deploy-a-gradio-web-app-on-azure-with-azure-app-service-a-step-by-step-guide/4121127)