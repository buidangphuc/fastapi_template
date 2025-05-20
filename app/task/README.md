## Task Introduction

The current task implementation uses Celery. For implementation details, please refer to [#225](https://github.com/fastapi-practices/fastapi_best_architecture/discussions/225)

## Adding Tasks

> [!IMPORTANT]
> Due to Celery's task scanning rules, which impose strict requirements on the directory structure of tasks, you must add tasks in the celery_task directory

### Simple Tasks

You can write your task code directly in the `tasks.py` file

### Hierarchical Tasks

If you want to organize tasks in a directory hierarchy to make the task structure clearer, you can create any directory, but you must note that:

1. After creating a new directory, be sure to update the task configuration `CELERY_TASKS_PACKAGES` by adding the new directory to this list
2. In the new directory, you must add a `tasks.py` file and write your task code in this file

## Message Broker

You can control the message broker selection through `CELERY_BROKER`, which supports redis and rabbitmq

For local debugging, redis is recommended

For production environments, rabbitmq is required
