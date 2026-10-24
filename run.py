import os
from app import create_app, init_db

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    init_db(app)
    app.run(host="127.0.0.1", port=5000, debug=True)
