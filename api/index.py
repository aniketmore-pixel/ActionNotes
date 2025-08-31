from werkzeug.middleware.proxy_fix import ProxyFix
from mangum import Mangum  # Converts Flask to serverless
from app import app, init_db

# Fix proxy headers for Vercel
app.wsgi_app = ProxyFix(app.wsgi_app)

# Initialize DB (optional if your app handles it)
init_db()

# The handler Vercel calls for every request
handler = Mangum(app)
