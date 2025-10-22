class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # For preflight requests
        if request.method == 'OPTIONS':
            response['Access-Control-Allow-Origin'] = 'https://68f9507ec44019af70178a2e--dapper-cannoli-407389.netlify.app'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
        else:
            response['Access-Control-Allow-Origin'] = 'https://68f9507ec44019af70178a2e--dapper-cannoli-407389.netlify.app'
            response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
