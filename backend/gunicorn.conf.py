import gunicorn

# Hide server version from response headers
gunicorn.SERVER = ""
