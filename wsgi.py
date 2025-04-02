import os
from typing import Any, Dict, List, Optional, Union

from app import create_app

app = create_app("production")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
