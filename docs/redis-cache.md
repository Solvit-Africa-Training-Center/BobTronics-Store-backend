# Redis cache configuration

Django uses Redis as the shared cache for authentication throttling and failed-login lockout state. Set `REDIS_URL` in the local `.env` file or deployment environment. All application processes must use the same Redis endpoint and database.

The default local URL is `redis://127.0.0.1:6379/1`. For a local Redis server, one option is:

```powershell
docker run --detach --name bobtronics-redis --publish 127.0.0.1:6379:6379 redis:8
```

For a hosted Redis instance, use its supplied URL, for example `rediss://username:password@redis.example.com:6379/1` when TLS is required. Keep credentials in `.env` or the deployment secret store, and URL-encode reserved characters in credentials.

Install the base and Redis dependencies:

```powershell
pip install -r requirements.txt -r requirements-redis.txt
```

Verify the connection with:

```powershell
python manage.py shell -c "from django.core.cache import cache; cache.set('redis-check', 'ok', 10); print(cache.get('redis-check'))"
```

The login tests override the cache with Django's local-memory backend, so running the test suite does not require a Redis service.
