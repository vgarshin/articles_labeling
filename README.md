# Articles labeling service
Experimental AI service for articles classification with respect to SDG or [Sustainable Development Goals](https://sdgs.un.org/goals).

## Goal

Build an AI service to classify arbitary text and find SDG that can be found in that text.

## Tools

[Transformers](https://huggingface.co/docs/transformers/index) framework to train classification models, [Hugging Face hub](https://huggingface.co/models) to get the pre-trained language models for fine-tuning, [Streamlit](https://streamlit.io/) for the interface of the application, [Flask](https://flask-docs.readthedocs.io/en/latest/) for the backend, [Docker](https://www.docker.com/) to run a services.

## Prerequisites

About 1000+ articles were manually labeled by selected 5 goals (multilabel problem).

[Object Storage](https://yandex.cloud/en/docs/storage/quickstart) bucket for the course data, [Yandex Managed Service for OpenSearch](https://cloud.yandex.com/en/docs/managed-opensearch/) instance as a database. [Virtual machine](https://cloud.yandex.com/en/docs/compute/quickstart/) with Docker installed.

Credentials to access object storage bucket, database and YandexGPT API in a form of JSON files `configs/config_SAMPLE.json` and `configs/credentials_SAMPLE.json`.

## Manual

Build an image to run all services, image is based on image for Data Science environment at the platform [GSOM JupyterHub](https://github.com/vgarshin/gsom_jhub_deploy). Command to build:

```bash
sudo docker build -t mibadsaitel dockerfiledsaitel
```

Start service for AI course assistant with `docker compose` to run all applications at once:

```bash
docker compose up
```
