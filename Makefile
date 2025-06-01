.PHONY: style check_code_quality

export PYTHONPATH = .
check_dirs := .

style:
	black --config black.toml $(check_dirs)
	isort --profile black $(check_dirs)

check_code_quality:
	make style
	# stop the build if there are Python syntax errors or undefined names
	flake8 $(check_dirs) --count --select=E9,F63,F7,F82 --show-source --statistics
	# exit-zero treats all errors as warnings. E203 for black, E501 for docstring, W503 for line breaks before logical operators 
	flake8 $(check_dirs) --count --max-line-length=88 --exit-zero  --ignore=D --extend-ignore=E203,E501,E402,W503  --statistics

build:
	docker build -t cycling . --target prod

run:
	docker run -d --name cycling-app -p 8501:8501 cycling

stop:
	docker stop cycling-app && docker rm cycling-app
