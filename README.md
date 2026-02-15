# Ask-Your-PDF

This repository contains the implementation of a Retrieval-Augmented Generation (RAG) system specifically designed to answer contract-based legal questions within the German Civil Code (Bürgerliches Gesetzbuch - BGB).

## Requirements

- Python 3.10 or later

#### Install Python using MiniConda

1) Download and install MiniConda from [here] ( https://www.anaconda.com/docs/getting-started/miniconda/main#quick-command-line-install )
2) create Environment using the Following command:
```bash
$ conda create -n ask-your-pdf python= 3.10
```
3) activate the environment:
```bash
$ conda activate ask-your-pdf
```


### (Optional) To write your commands in a new line:
```bash
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "
```


## Installation

### Install the required packages

```bash
$ pip install -r requirements.txt
```

### Setup the environment variables
```bash
cp .env.example .env
```

set your environment variables in `.env` file like Your llm key.

## Run FastAPI server
```bash
$ uvicorn main:app --reload --host 0.0.0.0 --port 5000
```