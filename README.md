# Image Moderation Platform

This platform goal is to give the ability to categorize and find certain attributes of images.
The system is designed for both manual work and automation of processes.

## Development

### VSCode devcontainer

To use VScode devcontainer from docker-compose.yml you must provide .env file with the structure:

```env
MONGO_INITDB_ROOT_USERNAME=
MONGO_INITDB_ROOT_PASSWORD=

MONGO_EXPRESS_USERNAME=
MONGO_EXPRESS_PASSWORD=

OBJS_ACCESS_KEY=
OBJS_SECRET_KEY=
```

#### Dev resources

| Resource      | URL                         | Description  |
| -------       | -------                     | -------   |
| mongo-express | http://localhost:8081       | mongodb admin app |
| imp-api       | http://localhost:17001/docs | imp api swagger |
| minio         | http://localhost:9001       | minio admin app |


