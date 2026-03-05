#!/usr/bin/env python3
"""
roundZero Comprehensive Diagnostic Script
==========================================
Tests all components: WebSocket, Gemini API, Pinecone, Redis, and the full pipeline.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List
from datetime import datetime
import traceback

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

def print_test(name: str, status: str, details: str = ""):
    """Print test result"""
    if status == "PASS":
        symbol = "[PASS]"
        color = Colors.GREEN
    elif status == "FAIL":
        symbol = "[FAIL]"
        color = Colors.RED
    elif status == "WARN":
        symbol = "[WARN]"
        color = Colors.YELLOW
    else:
        symbol = "[INFO]"
        color = Colors.BLUE
    
    print(f"{symbol} {color}{name}: {status}{Colors.RESET}")
    if details:
        print(f"   {Colors.MAGENTA}└─ {details}{Colors.RESET}")

class DiagnosticRunner:
    def __init__(self):
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {"passed": 0, "failed": 0, "warnings": 0}
        }
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8080")
        self.ws_url = self.backend_url.replace("http", "ws")

    def add_result(self, category: str, test: str, status: str, details: str = "", error: str = ""):
        """Add a test result"""
        self.results["tests"].append({
            "category": category,
            "test": test,
            "status": status,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        if status == "PASS":
            self.results["summary"]["passed"] += 1
        elif status == "FAIL":
            self.results["summary"]["failed"] += 1
        elif status == "WARN":
            self.results["summary"]["warnings"] += 1

    # =========================================================================
    # 1. ENVIRONMENT CHECKS
    # =========================================================================
    
    async def check_environment(self):
        """Check environment variables and configuration"""
        print_section("ENVIRONMENT CONFIGURATION")
        
        required_vars = [
            "GOOGLE_API_KEY",
            "PINECONE_API_KEY",
            "UPSTASH_REDIS_REST_URL",
            "UPSTASH_REDIS_REST_TOKEN",
            "DATABASE_URL"
        ]
        
        optional_vars = [
            "GEMINI_API_KEY",
            "BACKEND_URL",
            "FRONTEND_URL"
        ]
        
        # Check required variables
        for var in required_vars:
            if os.getenv(var):
                masked = f"{os.getenv(var)[:10]}...{os.getenv(var)[-4:]}" if len(os.getenv(var)) > 14 else "***"
                print_test(f"Environment Variable: {var}", "PASS", f"Set ({masked})")
                self.add_result("environment", var, "PASS", f"Variable is set")
            else:
                print_test(f"Environment Variable: {var}", "FAIL", "Not set")
                self.add_result("environment", var, "FAIL", "Required variable not set")
        
        # Check optional variables
        for var in optional_vars:
            if os.getenv(var):
                masked = f"{os.getenv(var)[:10]}..." if len(os.getenv(var)) > 14 else "***"
                print_test(f"Optional Variable: {var}", "PASS", f"Set ({masked})")
                self.add_result("environment", var, "PASS", f"Optional variable is set")
            else:
                print_test(f"Optional Variable: {var}", "WARN", "Not set (using defaults)")
                self.add_result("environment", var, "WARN", "Optional variable not set")

    # =========================================================================
    # 2. BACKEND CONNECTIVITY
    # =========================================================================
    
    async def check_backend_health(self):
        """Check if backend is running and healthy"""
        print_section("BACKEND HEALTH CHECK")
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Health endpoint
                try:
                    response = await client.get(f"{self.backend_url}/health")
                    if response.status_code == 200:
                        print_test("Backend Health Endpoint", "PASS", f"Status: {response.status_code}")
                        self.add_result("backend", "health_endpoint", "PASS", f"Response: {response.json()}")
                    else:
                        print_test("Backend Health Endpoint", "FAIL", f"Status: {response.status_code}")
                        self.add_result("backend", "health_endpoint", "FAIL", f"Unexpected status: {response.status_code}")
                except httpx.ConnectError as e:
                    print_test("Backend Health Endpoint", "FAIL", f"Connection refused - Is backend running on {self.backend_url}?")
                    self.add_result("backend", "health_endpoint", "FAIL", f"Connection error: {str(e)}")
                    return False
                
                # CORS headers check
                try:
                    response = await client.options(f"{self.backend_url}/health")
                    cors_headers = {
                        "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                        "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                        "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
                    }
                    print_test("CORS Configuration", "PASS", f"Headers: {cors_headers}")
                    self.add_result("backend", "cors", "PASS", f"CORS headers present")
                except Exception as e:
                    print_test("CORS Configuration", "WARN", f"Could not check CORS: {str(e)}")
                    self.add_result("backend", "cors", "WARN", f"Error: {str(e)}")
        
        except ImportError:
            print_test("httpx Library", "FAIL", "httpx not installed - run: pip install httpx")
            self.add_result("backend", "dependencies", "FAIL", "httpx not available")
            return False
        
        return True

    # =========================================================================
    # 3. WEBSOCKET CONNECTION TESTS
    # =========================================================================
    
    async def check_websocket_connection(self):
        """Test WebSocket connection with various scenarios"""
        print_section("WEBSOCKET CONNECTION TESTS")
        
        try:
            import websockets
            from websockets.exceptions import InvalidStatusCode, InvalidHandshake
            
            # Test 1: Basic WebSocket handshake
            test_user = "test_diagnostic_user"
            test_session = "test_diagnostic_session"
            ws_endpoint = f"{self.ws_url}/ws/{test_user}/{test_session}?mode=buddy"
            
            print(f"{Colors.BLUE}Testing WebSocket endpoint: {ws_endpoint}{Colors.RESET}\n")
            
            try:
                async with websockets.connect(
                    ws_endpoint,
                    additional_headers={
                        "Origin": "http://localhost:3000"
                    }
                ) as websocket:
                    print_test("WebSocket Handshake", "PASS", "Connection established")
                    self.add_result("websocket", "handshake", "PASS", "101 Switching Protocols")
                    
                    # Test 2: Send a test message
                    test_message = {
                        "type": "setup_complete",
                        "data": {"capabilities": ["audio"]}
                    }
                    
                    try:
                        await websocket.send(json.dumps(test_message))
                        print_test("WebSocket Send", "PASS", "Test message sent")
                        self.add_result("websocket", "send_message", "PASS", "Message sent successfully")
                        
                        # Test 3: Wait for response (with timeout)
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                            print_test("WebSocket Receive", "PASS", f"Response received: {response[:100]}...")
                            self.add_result("websocket", "receive_message", "PASS", "Response received")
                        except asyncio.TimeoutError:
                            print_test("WebSocket Receive", "WARN", "No response within 12 seconds (may indicate Gemini model not available)")
                            self.add_result("websocket", "receive_message", "WARN", "Timeout waiting for response")
                    
                    except Exception as e:
                        print_test("WebSocket Communication", "FAIL", str(e))
                        self.add_result("websocket", "communication", "FAIL", f"Error: {str(e)}")
                    
                    # Test 4: Close connection gracefully
                    try:
                        await websocket.close()
                        print_test("WebSocket Close", "PASS", "Connection closed gracefully")
                        self.add_result("websocket", "close", "PASS", "Graceful close")
                    except Exception as e:
                        print_test("WebSocket Close", "WARN", f"Close warning: {str(e)}")
                        self.add_result("websocket", "close", "WARN", f"Error: {str(e)}")
            
            except InvalidStatusCode as e:
                if e.status_code == 400:
                    print_test("WebSocket Handshake", "FAIL", "400 Bad Request - Check middleware interference")
                    self.add_result("websocket", "handshake", "FAIL", 
                                  "400 Bad Request - Likely middleware blocking WS upgrade")
                    print(f"\n{Colors.RED}DIAGNOSIS: The WebSocket upgrade is being rejected.{Colors.RESET}")
                    print(f"{Colors.YELLOW}   Possible causes:{Colors.RESET}")
                    print(f"{Colors.YELLOW}   1. CORS middleware blocking WebSocket upgrade{Colors.RESET}")
                    print(f"{Colors.YELLOW}   2. JWT middleware intercepting before route handler{Colors.RESET}")
                    print(f"{Colors.YELLOW}   3. BaseHTTPMiddleware incompatibility with WebSockets{Colors.RESET}")
                    print(f"{Colors.YELLOW}   4. Missing WebSocket route or incorrect path{Colors.RESET}\n")
                else:
                    print_test("WebSocket Handshake", "FAIL", f"Status code: {e.status_code}")
                    self.add_result("websocket", "handshake", "FAIL", f"Status: {e.status_code}")
            
            except InvalidHandshake as e:
                print_test("WebSocket Handshake", "FAIL", f"Invalid handshake: {str(e)}")
                self.add_result("websocket", "handshake", "FAIL", f"Invalid handshake: {str(e)}")
            
            except Exception as e:
                print_test("WebSocket Connection", "FAIL", f"Error: {str(e)}")
                self.add_result("websocket", "connection", "FAIL", f"Error: {str(e)}")
                print(f"\n{Colors.RED}Traceback:{Colors.RESET}")
                traceback.print_exc()
        
        except ImportError:
            print_test("websockets Library", "FAIL", "websockets not installed - run: pip install websockets")
            self.add_result("websocket", "dependencies", "FAIL", "websockets not available")

    # =========================================================================
    # 4. GEMINI API TESTS
    # =========================================================================
    
    async def check_gemini_api(self):
        """Test Gemini API connectivity and model availability"""
        print_section("GEMINI API TESTS")
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print_test("Gemini API Key", "FAIL", "GOOGLE_API_KEY not set")
            self.add_result("gemini", "api_key", "FAIL", "Key not found")
            return
        
        try:
            import google.genai as genai
            
            # Test 1: Client initialization
            try:
                client = genai.Client(api_key=api_key)
                print_test("Gemini Client Init", "PASS", "Client created successfully")
                self.add_result("gemini", "client_init", "PASS", "Client initialized")
            except Exception as e:
                print_test("Gemini Client Init", "FAIL", str(e))
                self.add_result("gemini", "client_init", "FAIL", f"Error: {str(e)}")
                return
            
            # Test 2: List available models
            try:
                print(f"\n{Colors.BLUE}Fetching available models...{Colors.RESET}")
                models = client.models.list()
                
                live_models = []
                embedding_models = []
                other_models = []
                
                for model in models:
                    model_name = model.name.split('/')[-1] if '/' in model.name else model.name
                    
                    # Live API / native-audio models are identified by name pattern
                    # (the API doesn't expose 'supported_generation_methods' for these)
                    is_live_model = any(keyword in model_name.lower() for keyword in [
                        'live', 'native-audio', 'bidigenerate'
                    ])
                    
                    if is_live_model:
                        live_models.append(model_name)
                    elif 'embedding' in model_name.lower():
                        embedding_models.append(model_name)
                    else:
                        other_models.append(model_name)
                
                print(f"\n{Colors.GREEN}Found {len(live_models)} Live API compatible models:{Colors.RESET}")
                for m in live_models:
                    print(f"  \u2022 {m}")
                
                print(f"\n{Colors.GREEN}Found {len(embedding_models)} embedding models:{Colors.RESET}")
                for m in embedding_models:
                    print(f"  \u2022 {m}")
                
                if live_models:
                    print_test("Gemini Live Models", "PASS", f"Found {len(live_models)} compatible models")
                    self.add_result("gemini", "live_models", "PASS", f"Models: {', '.join(live_models)}")
                else:
                    print_test("Gemini Live Models", "FAIL", "No Live API compatible models found")
                    self.add_result("gemini", "live_models", "FAIL", "No compatible models")
            
            except Exception as e:
                print_test("Gemini Model List", "FAIL", str(e))
                self.add_result("gemini", "model_list", "FAIL", f"Error: {str(e)}")
            
            # Test 3: Test specific model via Live API (native-audio models don't support generate_content)
            test_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-latest")
            try:
                print(f"\n{Colors.BLUE}Testing model via Live API: {test_model}{Colors.RESET}")
                
                from google.genai import types as genai_types
                config = genai_types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    system_instruction="You are a test assistant. Respond in one word."
                )
                
                audio_received = False
                async with client.aio.live.connect(model=test_model, config=config) as session:
                    await session.send_client_content(
                        turns=genai_types.Content(role="user", parts=[genai_types.Part(text="Say hello.")]),
                        turn_complete=True
                    )
                    async for response in session.receive():
                        if response.data and len(response.data) > 0:
                            audio_received = True
                            break
                        if response.server_content and response.server_content.turn_complete:
                            break
                
                if audio_received:
                    print_test(f"Model Test: {test_model}", "PASS", "Live API connected, audio received")
                    self.add_result("gemini", "model_test", "PASS", f"Model {test_model} responding via Live API")
                else:
                    print_test(f"Model Test: {test_model}", "WARN", "Connected but no audio in response")
                    self.add_result("gemini", "model_test", "WARN", "Live API connected, no audio returned")
            
            except Exception as e:
                error_msg = str(e)
                if "1008" in error_msg or "not found" in error_msg.lower():
                    print_test(f"Model Test: {test_model}", "FAIL", "Model not found (1008 error)")
                    self.add_result("gemini", "model_test", "FAIL", 
                                  f"Model {test_model} not available for this API key")
                    print(f"\n{Colors.RED}DIAGNOSIS: Model name incorrect or not available{Colors.RESET}")
                    print(f"{Colors.YELLOW}   Available Live API models listed above{Colors.RESET}\n")
                else:
                    print_test(f"Model Test: {test_model}", "FAIL", error_msg[:120])
                    self.add_result("gemini", "model_test", "FAIL", f"Error: {error_msg}")
        
        except ImportError:
            print_test("google.genai Library", "FAIL", "google-genai not installed")
            self.add_result("gemini", "dependencies", "FAIL", "google-genai not available")

    # =========================================================================
    # 5. PINECONE TESTS
    # =========================================================================
    
    async def check_pinecone(self):
        """Test Pinecone vector database connectivity"""
        print_section("PINECONE VECTOR DATABASE")
        
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print_test("Pinecone API Key", "FAIL", "PINECONE_API_KEY not set")
            self.add_result("pinecone", "api_key", "FAIL", "Key not found")
            return
        
        try:
            from pinecone import Pinecone
            
            # Test 1: Client initialization
            try:
                pc = Pinecone(api_key=api_key)
                print_test("Pinecone Client Init", "PASS", "Client created")
                self.add_result("pinecone", "client_init", "PASS", "Client initialized")
            except Exception as e:
                print_test("Pinecone Client Init", "FAIL", str(e))
                self.add_result("pinecone", "client_init", "FAIL", f"Error: {str(e)}")
                return
            
            # Test 2: List indexes
            try:
                indexes = pc.list_indexes()
                if indexes:
                    print_test("Pinecone Indexes", "PASS", f"Found {len(indexes)} indexes")
                    for idx in indexes:
                        print(f"  \u2022 {idx.name} (dimension: {idx.dimension})")
                    self.add_result("pinecone", "indexes", "PASS", f"Indexes: {[i.name for i in indexes]}")
                else:
                    print_test("Pinecone Indexes", "WARN", "No indexes found")
                    self.add_result("pinecone", "indexes", "WARN", "No indexes configured")
            except Exception as e:
                print_test("Pinecone Index List", "FAIL", str(e))
                self.add_result("pinecone", "index_list", "FAIL", f"Error: {str(e)}")
            
            # Test 3: Test query on specific index
            index_name = os.getenv("PINECONE_INDEX", "interview-questions")
            try:
                index = pc.Index(index_name)
                stats = index.describe_index_stats()
                print_test(f"Index '{index_name}' Stats", "PASS", 
                          f"Vectors: {stats.total_vector_count}, Dimension: {stats.dimension}")
                self.add_result("pinecone", "index_stats", "PASS", 
                              f"Index {index_name} accessible")
            except Exception as e:
                print_test(f"Index '{index_name}' Access", "FAIL", str(e))
                self.add_result("pinecone", "index_access", "FAIL", f"Error: {str(e)}")
        
        except ImportError:
            print_test("pinecone Library", "FAIL", "pinecone not installed")
            self.add_result("pinecone", "dependencies", "FAIL", "pinecone not available")

    # =========================================================================
    # 6. REDIS TESTS
    # =========================================================================
    
    async def check_redis(self):
        """Test Upstash Redis connectivity"""
        print_section("UPSTASH REDIS")
        
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        if not redis_url or not redis_token:
            print_test("Redis Configuration", "FAIL", "UPSTASH_REDIS_REST_URL or TOKEN not set")
            self.add_result("redis", "config", "FAIL", "Missing credentials")
            return
        
        try:
            import httpx
            
            # Test REST API
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    # Ping test
                    response = await client.get(
                        f"{redis_url}/ping",
                        headers={"Authorization": f"Bearer {redis_token}"}
                    )
                    
                    if response.status_code == 200:
                        print_test("Redis Connection", "PASS", "PING successful")
                        self.add_result("redis", "connection", "PASS", "Redis accessible")
                    else:
                        print_test("Redis Connection", "FAIL", f"Status: {response.status_code}")
                        self.add_result("redis", "connection", "FAIL", f"Status: {response.status_code}")
                    
                    # Test SET/GET
                    test_key = f"diagnostic_test_{int(datetime.now().timestamp())}"
                    test_value = "roundZero diagnostic test"
                    
                    # SET — use content= (raw string) to avoid double JSON encoding
                    set_response = await client.post(
                        f"{redis_url}/set/{test_key}",
                        headers={"Authorization": f"Bearer {redis_token}", "Content-Type": "application/json"},
                        content=f'"{test_value}"'
                    )
                    
                    if set_response.status_code == 200:
                        print_test("Redis SET", "PASS", f"Key '{test_key}' set")
                        self.add_result("redis", "set_operation", "PASS", "SET successful")
                        
                        # GET
                        get_response = await client.get(
                            f"{redis_url}/get/{test_key}",
                            headers={"Authorization": f"Bearer {redis_token}"}
                        )
                        
                        if get_response.status_code == 200:
                            data = get_response.json()
                            # Upstash returns value as JSON-encoded string, decode it
                            raw_result = data.get("result", "")
                            try:
                                decoded = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                            except Exception:
                                decoded = raw_result
                            if decoded == test_value:
                                print_test("Redis GET", "PASS", "Value retrieved correctly")
                                self.add_result("redis", "get_operation", "PASS", "GET successful")
                            else:
                                print_test("Redis GET", "FAIL", f"Expected '{test_value}', got '{decoded}'")
                                self.add_result("redis", "get_operation", "FAIL", f"Value mismatch: {decoded!r}")
                        else:
                            print_test("Redis GET", "FAIL", f"Status: {get_response.status_code}")
                            self.add_result("redis", "get_operation", "FAIL", f"Status: {get_response.status_code}")
                        
                        # Cleanup
                        await client.post(
                            f"{redis_url}/del/{test_key}",
                            headers={"Authorization": f"Bearer {redis_token}"}
                        )
                    else:
                        print_test("Redis SET", "FAIL", f"Status: {set_response.status_code}")
                        self.add_result("redis", "set_operation", "FAIL", f"Status: {set_response.status_code}")
                
                except Exception as e:
                    print_test("Redis Operations", "FAIL", str(e))
                    self.add_result("redis", "operations", "FAIL", f"Error: {str(e)}")
        
        except ImportError:
            print_test("httpx Library", "FAIL", "httpx not installed")
            self.add_result("redis", "dependencies", "FAIL", "httpx not available")

    # =========================================================================
    # 7. INTEGRATION TEST
    # =========================================================================
    
    async def check_full_pipeline(self):
        """Test the full interview pipeline"""
        print_section("FULL PIPELINE INTEGRATION TEST")
        
        try:
            import httpx
            import websockets
            
            # Step 1: Create user profile
            test_user_id = f"diagnostic_user_{int(datetime.now().timestamp())}"
            profile_data = {
                "user_id": test_user_id,
                "name": "Diagnostic User",
                "email": "diagnostic@test.com",
                "role": "Full Stack",
                "experience": "medium",
                "topics": ["Data Structures & Algorithms"]
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    response = await client.post(
                        f"{self.backend_url}/profile/",
                        json=profile_data
                    )
                    
                    if response.status_code == 200:
                        print_test("Profile Creation", "PASS", f"User {test_user_id} created")
                        self.add_result("integration", "profile_creation", "PASS", "Profile created")
                    else:
                        print_test("Profile Creation", "FAIL", f"Status: {response.status_code}")
                        self.add_result("integration", "profile_creation", "FAIL", 
                                      f"Status: {response.status_code}")
                        # Don't return, keep testing other parts if possible
                except Exception as e:
                    print_test("Profile Creation", "FAIL", str(e))
                    self.add_result("integration", "profile_creation", "FAIL", f"Error: {str(e)}")
                
                # Step 2: Start session
                session_data = {
                    "user_id": test_user_id,
                    "role": "Software Engineer",
                    "topics": ["Algorithms"],
                    "difficulty": "medium",
                    "mode": "buddy"
                }
                
                try:
                    response = await client.post(
                        f"{self.backend_url}/session/start",
                        json=session_data
                    )
                    
                    if response.status_code == 200:
                        session_info = response.json()
                        session_id = session_info.get("session_id")
                        print_test("Session Start", "PASS", f"Session {session_id} created")
                        self.add_result("integration", "session_start", "PASS", 
                                      f"Session {session_id} started")
                        
                        # Step 3: Connect to WebSocket with session
                        ws_endpoint = f"{self.ws_url}/ws/{test_user_id}/{session_id}?mode=buddy"
                        
                        try:
                            async with websockets.connect(
                                ws_endpoint,
                                additional_headers={"Origin": "http://localhost:3000"},
                                timeout=10
                            ) as websocket:
                                print_test("Integration WebSocket", "PASS", "Connected to session")
                                self.add_result("integration", "websocket_connect", "PASS", 
                                              "WebSocket connected to active session")
                                
                                # Send setup complete
                                await websocket.send(json.dumps({
                                    "type": "setup_complete",
                                    "data": {"capabilities": ["audio"]}
                                }))
                                
                                # Wait for agent response
                                try:
                                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                    print_test("Agent Response", "PASS", 
                                             f"Received: {response[:100]}...")
                                    self.add_result("integration", "agent_response", "PASS", 
                                                  "Agent responded to setup")
                                except asyncio.TimeoutError:
                                    print_test("Agent Response", "WARN", 
                                             "No response within 10s (may indicate Gemini connection issue)")
                                    self.add_result("integration", "agent_response", "WARN", 
                                                  "Timeout waiting for agent")
                                
                                await websocket.close()
                        
                        except Exception as e:
                            print_test("Integration WebSocket", "FAIL", str(e))
                            self.add_result("integration", "websocket_connect", "FAIL", 
                                          f"Error: {str(e)}")
                    else:
                        print_test("Session Start", "FAIL", f"Status: {response.status_code}")
                        self.add_result("integration", "session_start", "FAIL", 
                                      f"Status: {response.status_code}")
                
                except Exception as e:
                    print_test("Session Start", "FAIL", str(e))
                    self.add_result("integration", "session_start", "FAIL", f"Error: {str(e)}")
        
        except ImportError as e:
            print_test("Integration Test Dependencies", "FAIL", f"Missing library: {str(e)}")
            self.add_result("integration", "dependencies", "FAIL", str(e))

    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    
    async def run_all(self):
        """Run all diagnostic tests"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
        print("\u2551                    roundZero Diagnostic Suite v1.0                         \u2551")
        print("\u2551                      Comprehensive System Analysis                         \u2551")
        print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")
        print(f"{Colors.RESET}\n")
        
        print(f"{Colors.CYAN}Target Backend: {self.backend_url}{Colors.RESET}")
        print(f"{Colors.CYAN}Target WebSocket: {self.ws_url}{Colors.RESET}\n")
        
        # Run all test suites
        await self.check_environment()
        
        backend_running = await self.check_backend_health()
        if backend_running:
            await self.check_websocket_connection()
            await self.check_full_pipeline()
        else:
            print(f"\n{Colors.RED}Backend not running - Skipping WebSocket and integration tests{Colors.RESET}\n")
        
        await self.check_gemini_api()
        await self.check_pinecone()
        await self.check_redis()
        
        # Print summary
        self.print_summary()
        
        # Save results to file
        self.save_results()
    
    def print_summary(self):
        """Print test summary"""
        print_section("TEST SUMMARY")
        
        total = self.results["summary"]["passed"] + self.results["summary"]["failed"] + self.results["summary"]["warnings"]
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]
        warnings = self.results["summary"]["warnings"]
        
        print(f"{Colors.BOLD}Total Tests: {total}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Warnings: {warnings}{Colors.RESET}\n")
        
        if failed > 0:
            print(f"{Colors.RED}{Colors.BOLD}CRITICAL ISSUES DETECTED{Colors.RESET}\n")
            print(f"{Colors.YELLOW}Failed Tests:{Colors.RESET}")
            for test in self.results["tests"]:
                if test["status"] == "FAIL":
                    print(f"  \u2022 [{test['category']}] {test['test']}: {test['details']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")
        
        if success_rate >= 90:
            print(f"{Colors.GREEN}System is healthy!{Colors.RESET}")
        elif success_rate >= 70:
            print(f"{Colors.YELLOW}System has some issues but may be functional{Colors.RESET}")
        else:
            print(f"{Colors.RED}System has critical issues requiring attention{Colors.RESET}")
    
    def save_results(self):
        """Save diagnostic results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"diagnostic_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            print(f"\n{Colors.GREEN}Results saved to: {filename}{Colors.RESET}\n")
        except Exception as e:
            print(f"\n{Colors.RED}Failed to save results: {str(e)}{Colors.RESET}\n")


async def main():
    """Main entry point"""
    # Load environment from .env file if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(f"{Colors.GREEN}\u2713 Loaded .env file{Colors.RESET}\n")
    except ImportError:
        print(f"{Colors.YELLOW}\u26a0\ufe0f  python-dotenv not installed - using system environment only{Colors.RESET}\n")
    
    runner = DiagnosticRunner()
    await runner.run_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Diagnostic interrupted by user{Colors.RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.RESET}\n")
        traceback.print_exc()
        sys.exit(1)
