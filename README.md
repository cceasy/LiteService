#LiteService

## Rest services platform, easy to call each other and make endpoints

## before deploy:
- rename parent dir(LiteService) to docker (because docker-compose will create container with this prefix name)
- setup ~/data/storage ~/data/upload ~/data/mongo
- update volumes in docker-compose.yml
- mongorestore okapi
- set dkrt url (service needed)