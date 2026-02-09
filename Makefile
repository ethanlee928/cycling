.PHONY: style check_code_quality

export PYTHONPATH = .
check_dirs := .

export LOCAL_CACHE_DIR?=${PWD}/app/cache

style:
	uv run ruff format $(check_dirs)

check_code_quality:
	make style
	uv run ruff check $(check_dirs) --select=E9,F63,F7,F82 --statistics
	uv run ruff check $(check_dirs) --line-length=88 --exit-zero --ignore=D --extend-ignore=E203,E501,E402 --statistics

build:
	docker build -t cycling . --target prod --build-arg USERNAME=$(USER) --build-arg USER_ID=$(shell id -u) --build-arg GROUP_ID=$(shell id -g)

run:
	mkdir -p ${LOCAL_CACHE_DIR} && \
	docker run -d --name cycling-app -p 8501:8501 -v ${LOCAL_CACHE_DIR}:/home/$(USER)/app/cache cycling

stop:
	docker stop cycling-app && docker rm cycling-app
