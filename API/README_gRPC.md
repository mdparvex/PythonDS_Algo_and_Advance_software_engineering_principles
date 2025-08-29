# Technical Documentation: gRPC (Google Remote Procedure Call)

## 1\. Introduction

As applications evolved into **distributed systems and microservices**, traditional APIs like REST and SOAP started showing limitations in terms of **speed, payload size, and streaming**. To solve this, **Google developed gRPC in 2015**, an open-source, high-performance **RPC (Remote Procedure Call) framework**.

gRPC is built on **HTTP/2** and uses **Protocol Buffers (protobuf)** for data serialization. It’s designed for **fast, efficient, and scalable communication** between services, making it a popular choice in **microservice architectures**.

## 2\. What is gRPC?

**gRPC** is a modern, high-performance, open-source RPC framework. It allows clients to directly call methods on a server application as if they were local functions, using strongly typed contracts defined with **Protocol Buffers**.

### Key Principles of gRPC

1. **HTTP/2 by Default** → Enables multiplexing, header compression, and low-latency streaming.
2. **Protocol Buffers (Protobuf)** → Efficient binary serialization format.
3. **Strongly Typed Contracts** → Services and messages defined in .proto files.
4. **Cross-Platform** → Works with multiple programming languages (C++, Python, Java, Go, etc.).
5. **Streaming Support** → Supports client streaming, server streaming, and bi-directional streaming.
6. **High Performance** → Binary transport reduces payload size and increases speed.

## 3\. gRPC API Example

Imagine the **Bookstore API** in gRPC.

### Proto File (bookstore.proto)

```proto
syntax = "proto3";

service BookService {
  rpc GetBook (BookRequest) returns (BookResponse);
}

message BookRequest {
  int32 id = 1;
}

message BookResponse {
  int32 id = 1;
  string title = 2;
  string author = 3;
  int32 published_year = 4;
}
```
### Usage

- **Client calls** GetBook( BookRequest { id: 1 })
- **Server responds** with BookResponse { id:1, title:"The Pragmatic Programmer", author:"Andrew Hunt", published_year:1999 }

👉 Unlike REST/GraphQL, **gRPC generates client/server code** from the .proto file, ensuring type safety.

## 4\. Why Use gRPC?

### Advantages

- **High Performance** → Binary payload (Protobuf) is faster and smaller than JSON/XML.
- **Streaming Support** → Real-time communication with bi-directional streaming.
- **Cross-Language Support** → Supports multiple programming languages natively.
- **Strong Typing** → Schema ensures consistency and reduces runtime errors.
- **Built for Microservices** → Efficient service-to-service communication at scale.
- **HTTP/2 Benefits** → Multiplexing, flow control, header compression.

## 5\. gRPC vs Other API Technologies

### 5.1 gRPC vs REST

| **Feature** | **gRPC** | **REST** |
| --- | --- | --- |
| Data Format | Protocol Buffers (binary) | JSON, XML, etc. |
| Transport | HTTP/2 | HTTP/1.1 (mostly) |
| Streaming | Full (client, server, bi-dir) | Limited (server push) |
| Performance | Very high (low latency) | Good but heavier |
| Tooling | Requires .proto files | Easy (URLs, JSON) |
| Use Case | Microservices, internal APIs | Web/mobile applications |

👉 Example:

- **REST** → ```url GET /books/1 ``` → JSON response.
- **gRPC** → ```url GetBook(BookRequest{id:1}) ``` → Binary response (protobuf).

### 5.2 gRPC vs GraphQL

| **Feature** | **gRPC** | **GraphQL** |
| --- | --- | --- |
| Data Format | Protobuf (binary, compact) | JSON (text-based) |
| Endpoints | RPC methods defined in proto | Single endpoint /graphql |
| Flexibility | Low (fixed contracts) | High (client defines query) |
| Streaming | Strong (bi-directional) | Limited (subscriptions) |
| Performance | Excellent | Good, but JSON overhead |
| Use Case | Internal service-to-service | Client-to-server with flexible queries |

### 5.3 gRPC vs SOAP

| **Feature** | **gRPC** | **SOAP** |
| --- | --- | --- |
| Data Format | Binary (Protobuf) | XML |
| Protocol | HTTP/2 | HTTP, SMTP, TCP |
| Performance | Very fast | Slow (XML parsing) |
| Security | TLS (default) | WS-Security (enterprise-level) |
| Contracts | .proto definitions | WSDL |
| Use Case | Modern microservices | Enterprise legacy systems |

## 6\. When to Choose gRPC?

You should choose **gRPC** when:

- Building **microservices** that need fast, efficient communication.
- You need **bi-directional streaming** (e.g., chat apps, IoT).
- Services are **internal**, not exposed to public clients.
- You require **multi-language support** across teams (e.g., Python backend, Go microservice).
- Performance and bandwidth efficiency are **critical**.

## 7\. Conclusion

gRPC is a **modern, high-performance API framework** built for the world of **microservices and distributed systems**. With **Protobuf serialization, HTTP/2 transport, and streaming support**, it far outperforms REST and SOAP in terms of speed and efficiency.

However, gRPC is **not always the best fit** for public APIs due to its complexity and binary format (less human-readable). For internal service-to-service communication, **gRPC is often the best choice**.

✅ **In short**:

- Use **gRPC** for **microservices, internal APIs, and high-performance systems**.
- Use **REST** for **web/mobile public APIs**.
- Use **GraphQL** when clients need **flexible queries**.
- Use **SOAP** for **enterprise systems with strict contracts and security**.


# 📘 gRPC: Complete Documentation & Best Practices Guide

## 🧠 What is gRPC?

**gRPC** (gRPC Remote Procedure Call) is a **high-performance, open-source universal RPC framework** developed by **Google**. It allows services to communicate with each other efficiently, using Protocol Buffers (Protobuf) as the interface definition language and message serialization format.

## 🚀 Why Use gRPC Instead of REST or GraphQL?

| **Feature** | **REST** | **GraphQL** | **gRPC** |
| --- | --- | --- | --- |
| Data Format | JSON | JSON | Protobuf (binary, compact) |
| Performance | Moderate | Good | **Excellent** |
| Streaming Support | No  | Limited (Subscriptions) | **Yes** (Bi-directional) |
| Contract-first Approach | No  | Yes (Schema-first) | **Yes** (Protobuf) |
| Code Generation | Manual or OpenAPI | Yes (Apollo, etc.) | **Yes (Built-in)** |
| Strong Typing | Weak | Strong | **Very Strong** |
| Browser-Friendly | Yes | Yes | No (best for microservices) |

**Choose gRPC when:**

- You need high-performance internal service communication.
- Your systems use multiple languages (gRPC supports many).
- You want automatic client/server code generation.
- You need streaming or real-time bidirectional communication.
- You’re building microservices or distributed systems.

## 🧱 Core Concepts of gRPC

1. **Protobuf (Protocol Buffers)**  
    Used to define the structure of your data and services.
2. **Service Definition (.proto)**  
    You define services and their methods inside .proto files.
3. **gRPC Server**  
    Implements the logic for the defined services.
4. **gRPC Client**  
    Calls methods defined in .proto as if they were local functions.

## 🔧 Installing gRPC

### Python

```bash
pip install grpcio grpcio-tools
```
### Other Languages

- Node.js: npm install @grpc/grpc-js
- Go: go get google.golang.org/grpc
- Java: Managed via Maven or Gradle

## 🛠 Example: Building a gRPC Service in Python

### 1. Define the .proto File

```proto
// greet.proto

syntax = "proto3";

package greet;

service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply);
}

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}

```
### 2. Generate Python Code from .proto

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. greet.proto
```
### 3. Implement the Server

```python
# greeter_server.py

from concurrent import futures
import grpc
import greet_pb2
import greet_pb2_grpc

class GreeterServicer(greet_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        return greet_pb2.HelloReply(message=f"Hello, {request.name}!")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    greet_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

```

### 4. Create the Client

```python
# greeter_client.py

import grpc
import greet_pb2
import greet_pb2_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = greet_pb2_grpc.GreeterStub(channel)
        response = stub.SayHello(greet_pb2.HelloRequest(name='Mamun'))
        print("Greeter received:", response.message)

if __name__ == '__main__':
    run()

```
## ⚙ Types of gRPC Methods

| **Type** | **Description** | **Example** |
| --- | --- | --- |
| Unary | Single request, single response | SayHello() |
| Server Streaming | Single request, multiple responses | ListOrders() |
| Client Streaming | Multiple requests, single response | UploadData() |
| Bi-directional Stream | Multiple requests and responses (stream) | Chat() |

## 📂 Project Structure Suggestion

```lua
grpc_project/
├── greet.proto
├── greet_pb2.py
├── greet_pb2_grpc.py
├── greeter_server.py
├── greeter_client.py
├── requirements.txt

```
## 🔄 Using gRPC with Docker

### Dockerfile

```dockerfile
FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install grpcio grpcio-tools

EXPOSE 50051

CMD ["python", "greeter_server.py"]

```
### docker-compose.yml

```yaml
version: '3'
services:
  grpc-server:
    build: .
    ports:
      - "50051:50051"

```

## 🧪 Testing and Debugging

- Use grpcurl to test gRPC endpoints (like curl for REST).
- Use reflection service to introspect APIs.
- Log request/response using interceptors.

## 🔒 Security

- gRPC supports TLS out-of-the-box.
- Authentication via tokens or mutual TLS.
- Use interceptors to enforce authentication/authorization.

## 📈 Best Practices

✅ Use .proto files as the single source of truth  
✅ Version your APIs (v1, v2, etc.)  
✅ Handle errors using grpc.StatusCode  
✅ Use interceptors for logging, monitoring, auth  
✅ Prefer deadline/timeouts in clients

## 📊 When Not to Use gRPC

🚫 When your consumer is a **browser**, unless you use a gRPC-web proxy  
🚫 If **JSON is required** (e.g., public APIs)  
🚫 When you want **ad-hoc querying** like GraphQL  
🚫 If you need **human-readable payloads** for debugging

## 🔚 Final Thoughts

gRPC is the **ideal choice for modern backend communication**, especially in:

- Microservice environments
- Cross-language systems
- Real-time streaming
- High-performance APIs

While REST and GraphQL are great for external/public APIs, gRPC shines for **internal service-to-service communication** with **efficiency, type-safety, and scalability**.