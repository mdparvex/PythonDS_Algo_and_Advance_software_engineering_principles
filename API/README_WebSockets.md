# WebSockets: A Practical Guide for Backend Engineers

> A structured technical guide to understanding the WebSocket protocol,
> its connection lifecycle, Django implementation, real-time
> architecture, scaling, security, reliability, and production
> deployment.

## Table of Contents

1.  [What Are WebSockets?](#1-what-are-websockets)
2.  [Why WebSockets Exist](#2-why-websockets-exist)
3.  [How the WebSocket Protocol
    Works](#3-how-the-websocket-protocol-works)
4.  [WebSocket Connection Lifecycle](#4-websocket-connection-lifecycle)
5.  [WebSockets vs HTTP Polling vs
    SSE](#5-websockets-vs-http-polling-vs-sse)
6.  [A Minimal Python WebSocket
    Server](#6-a-minimal-python-websocket-server)
7.  [Browser Client Implementation](#7-browser-client-implementation)
8.  [Django WebSockets with Django
    Channels](#8-django-websockets-with-django-channels)
9.  [A Real-Time Chat Example](#9-a-real-time-chat-example)
10. [Groups, Channels, and Redis](#10-groups-channels-and-redis)
11. [Scaling WebSockets Across Multiple
    Instances](#11-scaling-websockets-across-multiple-instances)
12. [Reliability, Reconnection, and Message
    Delivery](#12-reliability-reconnection-and-message-delivery)
13. [Authentication and
    Authorization](#13-authentication-and-authorization)
14. [Production Deployment](#14-production-deployment)
15. [Testing and Debugging](#15-testing-and-debugging)
16. [Common Problems](#16-common-problems)
17. [When to Use WebSockets](#17-when-to-use-websockets)
18. [Key Takeaways](#18-key-takeaways)

------------------------------------------------------------------------

## 1. What Are WebSockets?

**WebSocket** is a communication protocol that provides a persistent,
full-duplex connection between a client and a server over a single TCP
connection.

Full-duplex means both sides can send messages independently at any
time:

-   The browser can send a message to the server.
-   The server can send a message to the browser.
-   Neither side needs to wait for the other side to initiate a new HTTP
    request.

This makes WebSockets useful for applications where both sides need
frequent, low-latency communication.

### Example: A chat application

Imagine two users are chatting.

1.  User A sends a message.
2.  The browser sends the message to the WebSocket server.
3.  The server processes the message.
4.  The server sends it to User B.
5.  User B's browser displays it immediately.
6.  User B can reply over the same connection.

The connection stays open while the chat session is active.

``` text
User A browser                  WebSocket server                User B browser
     |                                |                               |
     |-------- "Hello" -------------->|                               |
     |                                |-------- "Hello" ------------->|
     |                                |                               |
     |                                |<------- "Hi!" ----------------|
     |<------- "Hi!" -----------------|                               |
     |                                |                               |
     |------ "How are you?" --------->|                               |
     |                                |------ "How are you?" -------->|
```

The server is not limited to responding only when the browser sends a
request. It can send a message whenever an event occurs.

------------------------------------------------------------------------

## 2. Why WebSockets Exist

Traditional HTTP follows a request-response model.

``` text
Client                         Server
  |                              |
  |------ HTTP request -------->|
  |                              |
  |<----- HTTP response ---------|
  |                              |
  |       Request completes      |
```

For a traditional request, the client initiates communication. If the
server has new information later, it cannot simply write a new response
to the completed request.

A common workaround is polling:

``` javascript
setInterval(async () => {
  const response = await fetch("/api/messages/");
  const messages = await response.json();

  console.log(messages);
}, 3000);
```

This creates repeated HTTP requests, including when there are no new
messages.

WebSockets solve this by upgrading an initial HTTP connection to a
persistent, bidirectional connection.

``` text
Client                         Server
  |                              |
  |------ Connect -------------->|
  |<----- Connection accepted ---|
  |                              |
  |<==== Persistent channel ====>|
  |                              |
  |------ Message -------------->|
  |<----- Message ---------------|
  |<----- Server event ----------|
  |------ Client event ---------->|
  |                              |
```

### What does full-duplex mean?

Consider a telephone call:

-   You can speak while the other person listens.
-   The other person can speak while you listen.
-   Both can speak independently.

That is a useful mental model for a WebSocket connection.

By contrast, SSE is more like a radio broadcast: the server sends
updates to the client, while the client uses a separate HTTP request to
send information.

------------------------------------------------------------------------

## 3. How the WebSocket Protocol Works

WebSockets typically begin with an HTTP handshake and then switch
protocols.

### 3.1 Step 1: Client initiates a handshake

The browser creates a WebSocket connection:

``` javascript
const socket = new WebSocket("ws://localhost:8000/ws/chat/");
```

The browser initially sends an HTTP upgrade request similar to:

``` http
GET /ws/chat/ HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <random-value>
Sec-WebSocket-Version: 13
Origin: http://localhost:3000
```

Important headers:

  Header                    Purpose
  ------------------------- ----------------------------------------------
  `Upgrade: websocket`      Requests switching to the WebSocket protocol
  `Connection: Upgrade`     Indicates a protocol upgrade
  `Sec-WebSocket-Key`       Random value used in handshake validation
  `Sec-WebSocket-Version`   WebSocket protocol version
  `Origin`                  Identifies the browser origin

### 3.2 Step 2: Server accepts the handshake

If the server accepts the upgrade, it responds with:

``` http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: <computed-value>
```

The status code `101 Switching Protocols` indicates that the protocol
upgrade succeeded.

### 3.3 Step 3: Communication switches to WebSocket frames

After the handshake, the connection is no longer an ordinary HTTP
request-response exchange.

Both parties exchange WebSocket frames over the established connection.

Conceptually:

``` text
Browser                         Server
   |                               |
   |---- WebSocket frame --------->|
   |<--- WebSocket frame ----------|
   |<--- WebSocket frame ----------|
   |---- WebSocket frame --------->|
   |                               |
```

The protocol supports text frames, binary frames, control frames, and
fragmentation.

### 3.4 Step 4: Connection closes

Either side can initiate a closing handshake.

The browser can call:

``` javascript
socket.close(1000, "User left chat");
```

The server can also close the connection. The peers exchange close
frames, and the underlying connection is eventually closed.

### 3.5 `ws://` vs `wss://`

  Scheme     Meaning
  ---------- ----------------------------
  `ws://`    WebSocket without TLS
  `wss://`   WebSocket protected by TLS

Use `wss://` in production. It provides transport encryption in the same
way HTTPS protects HTTP traffic.

------------------------------------------------------------------------

## 4. WebSocket Connection Lifecycle

The browser's WebSocket API exposes four ready states:

  State            Numeric value Meaning
  -------------- --------------- --------------------------------------------------
  `CONNECTING`                 0 Connection is being established
  `OPEN`                       1 Connection is ready for communication
  `CLOSING`                    2 Closing handshake has started
  `CLOSED`                     3 Connection is closed or could not be established

Typical lifecycle:

``` text
             Create WebSocket
                    |
                    v
                CONNECTING
                    |
             Handshake succeeds
                    |
                    v
                  OPEN
                    |
          Send and receive messages
                    |
             Close / network loss
                    |
                    v
                 CLOSING
                    |
                    v
                  CLOSED
```

A WebSocket connection is not automatically restored by the browser's
native WebSocket API after a network failure. If the application needs
reconnection, it must implement it.

------------------------------------------------------------------------

## 5. WebSockets vs HTTP Polling vs SSE

These three approaches solve related but different problems.

  -------------------------------------------------------------------------------
  Feature           HTTP polling          SSE               WebSockets
  ----------------- --------------------- ----------------- ---------------------
  Communication     Repeated              Server to client  Client and server
  model             request-response                        

  Connection        Repeated HTTP         Persistent HTTP   Persistent WebSocket
                    requests              response          connection

  Direction         Client initiates each Server sends      Both sides send
                    request               events            messages

  Browser API       `fetch()`             `EventSource`     `WebSocket`

  Reconnection      Application-managed   Built into        Application-managed
                                          `EventSource`     

  Data              HTTP response formats UTF-8 text event  Text and binary
                                          stream            

  Complexity        Low                   Moderate          Higher

  Typical use       Infrequent refresh    Notifications,    Chat, collaboration,
                                          progress, feeds   interactive apps
  -------------------------------------------------------------------------------

### Choose based on communication needs

**Polling:** Use it when updates are infrequent and a small delay is
acceptable.

**SSE:** Use it when the server primarily pushes updates to the browser.

**WebSockets:** Use them when both client and server need to send
frequent messages over one persistent connection.

WebSockets are not automatically faster or better for every real-time
requirement. They introduce connection lifecycle, scaling,
authentication, and delivery concerns that simpler approaches may avoid.

------------------------------------------------------------------------

## 6. A Minimal Python WebSocket Server

Before introducing Django Channels, it helps to understand the protocol
with a small standalone server.

Install the `websockets` package:

``` bash
pip install websockets
```

Create `server.py`:

``` python
import asyncio
import websockets


async def handler(websocket):
    print("Client connected")

    try:
        async for message in websocket:
            print("Received:", message)

            await websocket.send(
                f"Server received: {message}"
            )

    except websockets.ConnectionClosed:
        print("Client disconnected")


async def main():
    async with websockets.serve(
        handler,
        "localhost",
        8000,
    ):
        print("WebSocket server running on ws://localhost:8000")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

``` bash
python server.py
```

This server:

1.  Listens for WebSocket connections on port `8000`.
2.  Accepts a connection.
3.  Waits for incoming messages.
4.  Sends a response for each message.
5.  Continues until the connection closes.

This is a protocol-learning example, not a production server. Production
systems need authentication, authorization, limits, logging, and
controlled shutdown.

------------------------------------------------------------------------

## 7. Browser Client Implementation

Create a simple HTML page:

``` html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Demo</title>
</head>
<body>
    <h2>WebSocket Demo</h2>

    <input id="messageInput" placeholder="Enter a message">
    <button id="sendButton">Send</button>

    <ul id="messages"></ul>

    <script>
        const socket = new WebSocket(
            "ws://localhost:8000"
        );

        const input = document.getElementById("messageInput");
        const messages = document.getElementById("messages");
        const sendButton = document.getElementById("sendButton");

        socket.onopen = () => {
            console.log("Connected to server");
        };

        socket.onmessage = (event) => {
            const item = document.createElement("li");
            item.textContent = event.data;
            messages.appendChild(item);
        };

        socket.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        socket.onclose = (event) => {
            console.log("Connection closed:", event.code);
        };

        sendButton.onclick = () => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(input.value);
                input.value = "";
            }
        };
    </script>
</body>
</html>
```

### What happens?

1.  The page creates a WebSocket connection.
2.  The browser performs the handshake.
3.  When the connection opens, `onopen` runs.
4.  Clicking Send calls `socket.send()`.
5.  The server receives the message.
6.  The server sends a reply.
7.  The browser receives it through `onmessage`.

The browser does not make a new HTTP request for every message.

------------------------------------------------------------------------

## 8. Django WebSockets with Django Channels

Django's traditional request-response views are designed around HTTP. To
build WebSocket applications in Django, a common solution is **Django
Channels**.

Channels extends Django to handle protocols such as WebSockets using
ASGI.

### 8.1 WSGI vs ASGI

Traditional Django deployments commonly use WSGI:

``` text
HTTP request
    |
    v
WSGI server
    |
    v
Django view
    |
    v
HTTP response
```

ASGI supports asynchronous application interfaces and long-lived
connections:

``` text
HTTP / WebSocket
       |
       v
   ASGI server
       |
       v
  ASGI application
       |
       +------ HTTP routing
       |
       +------ WebSocket routing
```

A WebSocket connection remains active beyond the initial handshake, so
the application needs to handle connection, receive, send, and
disconnect events.

### 8.2 Install dependencies

``` bash
pip install channels channels-redis
```

For local development, an in-memory channel layer can be used for a
single process. For multi-process or multi-instance deployments, use a
shared channel layer such as Redis.

### 8.3 Configure Django

In `settings.py`:

``` python
INSTALLED_APPS = [
    # Existing Django apps
    "channels",
]

ASGI_APPLICATION = "config.asgi.application"
```

For Redis:

``` python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

Replace the Redis address with the service hostname and credentials used
by your deployment.

### 8.4 Configure ASGI routing

In `config/asgi.py`:

``` python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from apps.chat.consumers import ChatConsumer

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": AuthMiddlewareStack(
        URLRouter([
            path(
                "ws/chat/",
                ChatConsumer.as_asgi(),
            ),
        ])
    ),
})
```

`ProtocolTypeRouter` selects the application based on the protocol type.
`URLRouter` matches the WebSocket URL. `AuthMiddlewareStack` provides
Django session-based authentication to the consumer's scope.

For production, also validate the browser origin using
`AllowedHostsOriginValidator` or `OriginValidator`, and implement
resource-level authorization.

### 8.5 Create a consumer

A Channels consumer is conceptually similar to a Django view, but it
handles the lifecycle of a WebSocket connection.

Create `apps/chat/consumers.py`:

``` python
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_group_name = "chat_room"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        data = json.loads(text_data)
        message = data.get("message", "")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
        }))
```

### 8.6 Understand the consumer lifecycle

**`connect()`**

Runs when a client attempts to connect. The consumer joins a group and
accepts the connection.

**`receive()`**

Runs when the client sends a WebSocket message. It parses the payload
and publishes a group event.

**`chat_message()`**

This is a channel-layer event handler. Channels maps the event type
`chat.message` to the method `chat_message`.

**`disconnect()`**

Runs when the connection closes. The consumer leaves the group to avoid
retaining a stale subscription.

### 8.7 Run the ASGI application

For example, using Daphne:

``` bash
pip install daphne
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

Use an ASGI server in deployment. Do not assume that starting a
conventional WSGI server automatically enables WebSocket routing.

------------------------------------------------------------------------

## 9. A Real-Time Chat Example

The previous consumer broadcasts messages to every connection in one
group. This demonstrates group messaging, but it is not a complete
private chat system.

### 9.1 Frontend

``` javascript
const socket = new WebSocket(
    "ws://localhost:8000/ws/chat/"
);

socket.onopen = () => {
    console.log("Connected");
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("New message:", data.message);
};

socket.onclose = (event) => {
    console.log("Disconnected:", event.code);
};

function sendMessage(message) {
    if (socket.readyState !== WebSocket.OPEN) {
        console.error("WebSocket is not connected");
        return;
    }

    socket.send(JSON.stringify({
        message: message,
    }));
}
```

### 9.2 Two-client flow

Suppose Browser A and Browser B both connect to `/ws/chat/`.

``` text
Browser A             Django Channels / Redis             Browser B
    |                           |                             |
    |------ Connect ------------|                             |
    |                           |<---------- Connect ----------|
    |                           |                             |
    |------ Join chat_room -----|                             |
    |                           |------ Join chat_room ------>|
    |                           |                             |
    |------ Send "Hello" ------>|                             |
    |                           |                             |
    |                           |---- group event ----------->|
    |<----- group event --------|                             |
    |                           |                             |
```

Both consumers join the same group. When one sends a message, the group
event is delivered to all active members, including the sender.

### 9.3 What this example does not implement

A real chat application also needs:

-   Persistent message storage.
-   Conversation membership checks.
-   Sender identity from authenticated server-side context.
-   Message validation and length limits.
-   Rate limiting and abuse protection.
-   Read receipts, delivery status, and presence if required.
-   Pagination and history retrieval through HTTP APIs.
-   A clear policy for offline users.

Do not trust a client-supplied `user_id`, `sender`, or room membership
field. Derive identity from the authenticated connection and authorize
every room subscription.

------------------------------------------------------------------------

## 10. Groups, Channels, and Redis

These concepts are central to Django Channels.

### 10.1 Channel

A channel is an addressable destination for messages associated with an
application consumer. Each consumer instance has a channel name.

Think of it as a mailbox for one connected consumer.

### 10.2 Group

A group is a named collection of channels.

For example:

``` text
Group: chat_room_10

Members:
    channel_A
    channel_B
    channel_C
```

Sending an event to the group distributes it to its current members.

Groups are useful for:

-   Chat rooms.
-   Per-user notifications.
-   Order-specific updates.
-   Live dashboards.
-   Team collaboration rooms.

A group is a messaging abstraction, not a persistent database table or a
substitute for authorization.

### 10.3 Channel layer

The channel layer provides communication between consumers, including
consumers running in different processes.

Without a shared channel layer, an in-memory group in one process is not
automatically visible to another process.

### 10.4 Why Redis?

Consider two ASGI application instances:

``` text
                 Load Balancer
                  /         \
                 /           \
                v             v
          ASGI Instance A  ASGI Instance B
             |                  |
         Consumer A          Consumer B
             |                  |
             +--------+---------+
                      |
                    Redis
                Channel Layer
```

If Browser A connects to instance A and Browser B connects to instance
B, both instances need a shared mechanism to distribute group events.

Redis-backed Channels provides that shared channel layer.

**Important distinction:** Django Channels' Redis channel layer is not
the same thing as directly using Redis Pub/Sub in application code. Use
the Channels channel-layer API (`group_send`, `group_add`, and related
methods) when working with Channels groups. The backend manages its own
message and group semantics.

### 10.5 Channel-layer event example

``` python
await self.channel_layer.group_send(
    "order_123",
    {
        "type": "order_status_changed",
        "order_id": 123,
        "status": "Confirmed",
    },
)
```

The receiving consumer handles it with:

``` python
async def order_status_changed(self, event):
    await self.send(text_data=json.dumps({
        "order_id": event["order_id"],
        "status": event["status"],
    }))
```

The event's `type` selects the handler method by replacing dots with
underscores.

------------------------------------------------------------------------

## 11. Scaling WebSockets Across Multiple Instances

A single application instance can manage WebSocket connections and
broadcast messages locally. Production systems often run multiple
instances for capacity and availability.

### 11.1 The multi-instance problem

Imagine:

-   Customer A connects to application instance 1.
-   Customer B connects to application instance 2.
-   Customer A sends a message.

If instance 1 only knows about its own local connections, it cannot
directly deliver the message to Customer B on instance 2.

A shared channel layer solves this communication problem.

### 11.2 Scaled architecture

``` text
 Browser A                         Browser B
     |                                 |
     v                                 v
 Load Balancer                     Load Balancer
     |                                 |
     v                                 v
 ASGI Instance 1                  ASGI Instance 2
     |                                 |
     +---------------+-----------------+
                     |
                     v
              Redis Channel Layer
                     |
                     v
             Group event delivery
```

The load balancer distributes new connections. Redis allows application
instances to communicate.

### 11.3 Load balancer considerations

-   The proxy must support HTTP upgrade requests.
-   Configure suitable idle/read timeouts.
-   Ensure the load balancer does not buffer or terminate upgraded
    connections unexpectedly.
-   Monitor active connections per instance.
-   Plan graceful shutdown and connection draining during deployments.
-   Sticky sessions are not a replacement for a shared channel layer.
    They may be useful for some infrastructure behavior, but correctness
    should not depend on them.

### 11.4 Backpressure and slow clients

A client may receive messages more slowly than the server produces them.

If the application queues messages without bounds, memory usage can
grow.

Production designs should define:

-   Bounded per-connection queues.
-   A policy for dropping noncritical updates.
-   Disconnect behavior for persistently slow clients.
-   Message size and frequency limits.
-   Coalescing of replaceable state updates, such as dashboard counters.

------------------------------------------------------------------------

## 12. Reliability, Reconnection, and Message Delivery

WebSockets provide a communication channel. They do not, by themselves,
guarantee that a business message is stored, delivered, processed, or
acknowledged exactly once.

### 12.1 What happens when the network disconnects?

``` text
Client                  Server
  |                        |
  |------ Message A ------>|
  |<----- Response A ------|
  |                        |
  |    Network disconnect  |
  X                        |
                           |
  |    Network reconnect   |
  |                        |
  |------ New connection ->|
```

The browser's native WebSocket API does not automatically reconnect. The
application must create a new connection.

### 12.2 Basic reconnection example

``` javascript
let socket;
let reconnectDelay = 1000;
const maxReconnectDelay = 30000;
let shouldReconnect = true;

function connect() {
    socket = new WebSocket("wss://example.com/ws/chat/");

    socket.onopen = () => {
        console.log("Connected");
        reconnectDelay = 1000;
    };

    socket.onmessage = (event) => {
        console.log("Received:", event.data);
    };

    socket.onclose = () => {
        if (!shouldReconnect) {
            return;
        }

        const delay = reconnectDelay + Math.random() * 500;

        setTimeout(connect, delay);

        reconnectDelay = Math.min(
            reconnectDelay * 2,
            maxReconnectDelay
        );
    };

    socket.onerror = () => {
        // The close handler normally performs reconnection.
        socket.close();
    };
}

connect();

// When intentionally leaving the application:
function disconnect() {
    shouldReconnect = false;
    socket?.close(1000, "Client disconnected");
}
```

This illustrates exponential backoff with jitter. A production
implementation should also:

-   Avoid multiple concurrent reconnect timers.
-   Distinguish intentional closure from unexpected disconnection.
-   Handle authentication expiry.
-   Restore subscriptions after reconnecting.
-   Avoid replaying stale client commands blindly.
-   Stop reconnecting when the application is no longer active.

### 12.3 Message acknowledgements

For important operations, the application can define an acknowledgement
protocol.

Client sends:

``` json
{
  "type": "send_message",
  "message_id": "msg-1001",
  "conversation_id": 42,
  "content": "Hello"
}
```

Server replies:

``` json
{
  "type": "message_accepted",
  "message_id": "msg-1001"
}
```

The acknowledgement should be sent only after the server has completed
the operation represented by that acknowledgement. If it only means the
message was accepted into memory, document that distinction.

### 12.4 Persist before broadcasting

For chat messages, a common sequence is:

``` text
Receive message
      |
      v
Authenticate and authorize
      |
      v
Validate payload
      |
      v
Persist message in database
      |
      v
Publish event to conversation group
      |
      v
Connected clients receive message
```

This way, a user who was offline can fetch message history later through
a normal HTTP API.

For stronger delivery guarantees across database and messaging systems,
use an outbox pattern and idempotent consumers.

------------------------------------------------------------------------

## 13. Authentication and Authorization

A WebSocket connection must be secured just like an HTTP API.

### 13.1 Authentication

Django Channels can use Django's session authentication:

``` python
from channels.auth import AuthMiddlewareStack
```

This works when the browser sends the appropriate session cookie during
the handshake.

For token-based authentication, implement carefully designed ASGI
middleware or another supported authentication approach. The native
browser WebSocket constructor does not support arbitrary custom headers.

### 13.2 Authorization

Authentication answers:

> Who is connecting?

Authorization answers:

> Is this user allowed to access this resource?

For example, a user may be authenticated but must not join another
customer's private conversation or subscribe to another customer's
order.

A safe connection flow:

1.  Authenticate the connection.
2.  Extract the authenticated user from `scope["user"]`.
3.  Validate the requested conversation or order identifier.
4.  Check resource membership or ownership in the database.
5.  Join only the authorized group.
6.  Reject unauthorized connections.

Illustrative consumer:

``` python
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PrivateChatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        # Fetch and authorize the requested conversation here.
        # Do not trust a client-provided user ID or membership claim.

        await self.accept()
```

The example shows the authentication gate only. Add actual conversation
authorization before accepting or joining a group.

### 13.3 Origin validation

Browsers include an `Origin` header in the handshake. Validate allowed
origins to reduce Cross-Site WebSocket Hijacking risk, particularly when
using cookie-based authentication.

For example, wrap routing with:

``` python
from channels.security.websocket import AllowedHostsOriginValidator

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

Configure `ALLOWED_HOSTS` correctly. For more restrictive policies, use
`OriginValidator` with an explicit list of trusted origins.

### 13.4 Additional security controls

-   Use `wss://` in production.
-   Validate message schemas and types.
-   Enforce maximum payload size.
-   Rate-limit messages and connection attempts.
-   Apply per-user and per-resource authorization.
-   Avoid logging passwords, tokens, or sensitive payloads.
-   Define connection and idle timeouts.
-   Re-check permissions when long-lived connections outlast relevant
    access changes.

------------------------------------------------------------------------

## 14. Production Deployment

### 14.1 ASGI server

Use an ASGI server such as Daphne or Uvicorn with the Django ASGI
application.

Example:

``` bash
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

Choose a worker/process configuration appropriate for the server and
application. Test graceful shutdown behavior and connection draining.

### 14.2 Nginx reverse proxy

A simplified Nginx configuration:

``` nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl;
    server_name api.example.com;

    location /ws/ {
        proxy_pass http://django_asgi;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

This is an illustrative location block. Configure TLS, upstream
definitions, health checks, timeouts, and security headers for your
environment.

Unlike SSE, WebSocket traffic is upgraded and then carried as WebSocket
frames. SSE proxy buffering directives are not the central concern for
an upgraded WebSocket connection; upgrade forwarding and connection
timeouts are.

### 14.3 Docker Compose example

A simplified local development setup:

``` yaml
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"

  web:
    build: .
    command: >
      uvicorn config.asgi:application
      --host 0.0.0.0
      --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
```

Configure the Channels Redis backend to use the `redis` service hostname
inside Docker:

``` python
import os

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.getenv("REDIS_HOST", "127.0.0.1"),
                    int(os.getenv("REDIS_PORT", "6379")),
                )
            ],
        },
    },
}
```

For production, add health checks, persistent/managed Redis where
appropriate, secrets management, resource limits, monitoring, and a
deliberate deployment strategy.

### 14.4 Observability

Monitor at least:

-   Active WebSocket connections.
-   Connection attempts and failures.
-   Close codes and disconnect reasons.
-   Messages sent and received.
-   Message processing latency.
-   Redis/channel-layer health.
-   Per-instance memory and CPU.
-   Slow-client and queue behavior.
-   Authentication and authorization failures.

Do not log sensitive message contents by default.

------------------------------------------------------------------------

## 15. Testing and Debugging

### 15.1 Browser developer tools

Open the browser's Developer Tools:

1.  Select the Network tab.
2.  Filter by WS (WebSocket).
3.  Open the WebSocket request.
4.  Inspect the handshake.
5.  Inspect sent and received frames.
6.  Check close codes and connection timing.

A successful handshake normally returns status
`101 Switching Protocols`.

### 15.2 Test with a command-line client

Install `websocat` or another WebSocket client. With `websocat`:

``` bash
websocat ws://localhost:8000/ws/chat/
```

Type a message and inspect the server response.

For a secure endpoint:

``` bash
websocat wss://example.com/ws/chat/
```

### 15.3 Test cases

-   [ ] A valid user can establish a connection.
-   [ ] An unauthenticated user is rejected where authentication is
    required.
-   [ ] A user cannot join an unauthorized room.
-   [ ] Text and JSON messages are validated.
-   [ ] Invalid payloads do not crash the consumer.
-   [ ] Disconnect removes the consumer from its groups.
-   [ ] Reconnection restores the required subscriptions.
-   [ ] Multiple application instances can exchange group events.
-   [ ] Oversized or excessive messages are handled safely.
-   [ ] Slow clients do not cause unbounded memory growth.
-   [ ] Deployment shutdown does not leave stale resources.

------------------------------------------------------------------------

## 16. Common Problems

  -----------------------------------------------------------------------
  Problem                 Likely cause            What to inspect
  ----------------------- ----------------------- -----------------------
  Handshake returns 404   WebSocket route is not  `asgi.py`, URL patterns
                          configured              

  Handshake returns 403   Origin validation or    `Origin`, allowed
                          authorization failure   hosts, permissions

  Handshake returns 200   Request was handled as  ASGI routing and proxy
  instead of 101          ordinary HTTP           upgrade headers

  Works locally but not   Upgrade headers or      `Upgrade`,
  behind Nginx            timeout missing         `Connection`, proxy
                                                  timeouts

  Messages reach only     Local in-memory layer   `CHANNEL_LAYERS`
  some instances          or misconfigured Redis  

  Connection drops after  Proxy/load-balancer     Infrastructure timeouts
  a fixed period          idle timeout            and heartbeat policy

  Duplicate messages      Retry or                Message IDs and
                          application-level       idempotency
                          duplicate processing    

  Missed messages after   No durable replay       Database history,
  reconnect               mechanism               outbox, event IDs

  High memory usage       Too many connections or Connection limits and
                          unbounded queues        backpressure

  Unauthorized room       Missing resource-level  Consumer connection and
  access                  authorization           group-join logic
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 17. When to Use WebSockets

### Good use cases

  Use case                  Why WebSockets fit
  ------------------------- ------------------------------------------------
  Chat applications         Both users and server send messages
  Multiplayer games         Frequent bidirectional state updates
  Collaborative editors     Multiple participants exchange changes
  Live support              Agents and customers communicate interactively
  Interactive dashboards    Client subscriptions and server updates
  Real-time collaboration   Low-latency two-way communication

### When WebSockets may be unnecessary

-   A page only needs a notification when a background job finishes: SSE
    may be simpler.
-   A customer only needs order status updates: SSE may be sufficient.
-   A page refreshes data every few minutes: polling may be sufficient.
-   A server streams generated AI tokens to a browser: SSE is often a
    natural fit, although WebSockets can also support it.

### Practical architecture for an e-commerce chat system

A useful separation of responsibilities is:

``` text
HTTP APIs
   |
   +-- Create conversation
   +-- Fetch conversation history
   +-- Paginate messages
   +-- Upload attachments
   |
   v
Database (persistent state)

WebSocket
   |
   +-- Send a live message
   +-- Receive a live message
   +-- Typing indicators
   +-- Presence updates
   |
   v
Django Channels + Redis
   |
   v
Connected clients
```

Use HTTP for resource creation, history, pagination, and file uploads.
Use WebSockets for the interactive live communication path. Persist
important messages in the database rather than treating the WebSocket
connection as message storage.

------------------------------------------------------------------------

## 18. Key Takeaways

1.  **WebSockets provide full-duplex communication.** Both client and
    server can send messages independently over one persistent
    connection.
2.  **The connection begins with an HTTP handshake.** A successful
    upgrade normally returns `101 Switching Protocols`.
3.  **After the handshake, communication uses WebSocket frames.** It is
    no longer a normal HTTP request-response exchange.
4.  **The browser's native WebSocket API does not reconnect
    automatically.** Implement reconnection, backoff, and subscription
    restoration.
5.  **Django Channels brings WebSocket support to Django.** It uses ASGI
    and consumers to manage connection lifecycles.
6.  **Groups support broadcast to multiple connections.** They are a
    messaging abstraction, not an authorization system.
7.  **Redis enables cross-process communication.** A shared channel
    layer is important when the application runs multiple instances.
8.  **WebSockets do not guarantee durable message delivery.** Persist
    important data, use acknowledgements where appropriate, and design
    idempotent operations.
9.  **Security is essential.** Authenticate connections, validate
    origins, authorize every resource subscription, and use `wss://`.
10. **Production requires operational planning.** Consider proxy
    upgrades, timeouts, connection limits, backpressure, observability,
    and graceful shutdown.

## Further Reading

-   [RFC 6455: The WebSocket
    Protocol](https://www.rfc-editor.org/rfc/rfc6455)
-   [MDN: WebSocket
    API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
-   [Django Channels documentation](https://channels.readthedocs.io/)
-   [Channels channel
    layers](https://channels.readthedocs.io/en/stable/topics/channel_layers.html)
-   [Channels
    authentication](https://channels.readthedocs.io/en/stable/topics/authentication.html)
-   [Uvicorn documentation](https://www.uvicorn.org/)
-   [Redis documentation](https://redis.io/docs/latest/)
