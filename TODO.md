
Not implemented right now / Ideas / TODOs
----------------------------------------

* Cassandra timeouts: backend should have a short timeout and few retries, frontend a larger timeout and many retries.

* Cleanup uses of `pylibmc` (now `python-memcached` is used)

* Create a Django middleware to log exceptions

* Failover on client (if one server doesn't respond, try another)

* Test and compare performance and disk space: StorageService vs StorageServiceUniqueMessagePlusReferences

* Document installation procedure

* Easy deploy using Gunicorn

* Add tests with Selenium / WebDriver Plus

* Move Daedalus client to separate project

* Add check of memcache on status page

* Accept messages even when lack some field(s)

* Filter by date

* TTL of messages / automatic disposal of old messages

* Live update of search results
  - a. Update the search results while new messages arrives

* Tagging of log messages

* Search by message text

* Autentication to save messages (backend) and/or to see the messages (frontend)
