"""CORS test endpoint."""
from flask_restx import Namespace, Resource

cors_ns = Namespace("cors-test", description="CORS test operations")


@cors_ns.route("")
class CORSTestResource(Resource):
    def get(self):
        """Test endpoint for CORS."""
        return {"message": "CORS test successful"}

    def options(self):
        """Handle OPTIONS requests for CORS preflight."""
        return "", 200
