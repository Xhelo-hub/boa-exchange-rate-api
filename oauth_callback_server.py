"""
Simple HTTP server to receive QuickBooks OAuth callback
This bypasses the need for FastAPI/pydantic
"""
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import webbrowser

PORT = 8000

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the callback URL
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/v1/callback':
            # Extract query parameters
            params = parse_qs(parsed_url.query)
            
            code = params.get('code', [''])[0]
            realm_id = params.get('realmId', [''])[0]
            state = params.get('state', [''])[0]
            
            # Send response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <html>
            <head><title>QuickBooks Authorization</title></head>
            <body style="font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto;">
                <h1 style="color: #2ca01c;">✓ Authorization Successful!</h1>
                <p>You can close this window and return to VS Code.</p>
                <hr>
                <h2>OAuth Credentials Received:</h2>
                <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; font-family: monospace;">
                    <p><strong>Authorization Code:</strong><br>{code}</p>
                    <p><strong>Company ID (Realm ID):</strong><br>{realm_id}</p>
                    <p><strong>State:</strong><br>{state}</p>
                </div>
                <hr>
                <p style="color: #666;">The credentials have been displayed in your terminal. Please check VS Code.</p>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode())
            
            # Print credentials to console
            print("\n" + "="*80)
            print("QUICKBOOKS OAUTH CREDENTIALS RECEIVED")
            print("="*80)
            print(f"\nAuthorization Code: {code}")
            print(f"Company ID (Realm ID): {realm_id}")
            print(f"State: {state}")
            print("\n" + "="*80)
            print("\nNext: Exchange the authorization code for access tokens")
            print("="*80 + "\n")
            
            # Server will continue running; user can Ctrl+C to stop it
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging for cleaner output
        pass

if __name__ == "__main__":
    print("Starting OAuth Callback Server...")
    print(f"Listening on http://localhost:{PORT}/api/v1/callback")
    print("\nReady to receive QuickBooks authorization callback.")
    print("Press Ctrl+C to stop the server.\n")
    
    with socketserver.TCPServer(("", PORT), OAuthCallbackHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
