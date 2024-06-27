# Articles labeling service
Experimental AI service for articles classification with respect to SDG or [Sustainable Development Goals](https://sdgs.un.org/goals).

## Goal

Build an AI service to classify arbitary text and find SDG in that text.

## Tools

[Transformers](https://huggingface.co/docs/transformers/index) framework to train classification models, [Hugging Face hub](https://huggingface.co/models) to get the pre-trained language models for fine-tuning, [Streamlit](https://streamlit.io/) for the interface of the application, [Flask](https://flask-docs.readthedocs.io/en/latest/) for the backend, [Docker](https://www.docker.com/) to run a services.

## Prerequisites

About 1000+ articles were manually labeled by selected 5 goals (multilabel problem).

[Object Storage](https://yandex.cloud/en/docs/storage/quickstart) bucket to store data and trained models, [JupyterHub SimBA platform](https://jhas01.gsom.spbu.ru) to process data and train models (GPU required). [Virtual machine](https://cloud.yandex.com/en/docs/compute/quickstart/) with Docker installed to run service.

Configuration parameters and credentials to access object storage bucket are JSON files `configs/config.json` and `configs/access_bucket.json`.

## Manual

### Part 1. Train a model

Notebooks for models fine-tuning are in `notebooks/` folder.

### Part 2. Run a service

Build an image to run all services, image is based on image for Data Science environment at the platform [GSOM JupyterHub](https://github.com/vgarshin/gsom_jhub_deploy). Command to build:

```bash
sudo docker build -t mibadsailbl dockerfiledsailbl
```

Start service for AI course assistant with `docker compose` to run all applications at once:

```bash
docker compose up
```
