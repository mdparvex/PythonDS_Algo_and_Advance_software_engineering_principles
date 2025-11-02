# 📘 Technical Documentation: Content Negotiation in APIs

## 1\. Introduction

APIs often support multiple **data formats** (e.g., JSON, XML, CSV) or **different versions** of a resource.  
But how does the client tell the server what kind of response it prefers?  
This is where **Content Negotiation** comes in.

**Content negotiation** is the process by which the **client and server agree on the format of the response**. It ensures flexibility and allows the same API to serve multiple clients (web, mobile, IoT) with different needs.

## 2\. What is Content Negotiation?

Content negotiation is part of the **HTTP specification (RFC 7231)**. It allows the client to specify **what type of data it wants**, and the server to either provide it or return an error if not supported.

### Two Main Types

1. **Server-driven negotiation** → The server selects the best response format based on the client’s request headers.
2. **Client-driven negotiation** → The client explicitly requests a specific format via query parameters or custom headers.

## 3\. HTTP Headers Used in Content Negotiation

- **Accept** → What response type(s) the client can handle.  
    Example:
    ```bash
    Accept: application/json
    Accept: application/xml;q=0.9, application/json;q=0.8
    ```

(q is a quality factor; higher means more preferred)

- **Content-Type** → What type of data is being sent in the request body (important for POST/PUT).  
    Example:
    `Content-Type: application/json`
- **Accept-Language** → Preferred human language for the response.  
    Example:
    `Accept-Language: en-US,en;q=0.9, fr;q=0.8`
- **Accept-Encoding** → What compression formats the client supports.  
    Example:
 `Accept-Encoding: gzip, deflate, br `

## 4\. Examples of Content Negotiation

### Example 1: JSON vs XML

#### Request (client prefers JSON)

```http
GET /books/1
Accept: application/json
```

#### Response

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt"
}
```

#### Request (client prefers XML)

```http
GET /books/1
Accept: application/xml
```

#### Response

```xml
<Book>
  <Id>1</Id>
  <Title>The Pragmatic Programmer</Title>
  <Author>Andrew Hunt</Author>
</Book>
```

### Example 2: API Versioning

Some APIs use **content negotiation for versioning** instead of embedding version in the URL.

#### Request

```http
GET /books/1
Accept: application/vnd.myapi.v2+json
```

#### Response

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": {
    "name": "Andrew Hunt"
  }
}
```

### Example 3: Language Negotiation

#### Request

```http
GET /greeting
Accept-Language: fr
```

#### Response

```json
{
  "message": "Bonjour"
}
```

## 5\. Use Cases of Content Negotiation

1. **Multi-format support** → Same endpoint can return JSON, XML, or CSV based on client needs.
2. **API versioning** → Clients request specific versions without changing endpoints.
3. **Localization** → Serve responses in the client’s preferred language.
4. **Performance optimization** → Negotiate compressed responses (gzip, br).
5. **Mobile vs Desktop clients** → Return different data formats or reduced payloads.

## 6\. Comparisons with Alternatives

### 6.1 Content Negotiation vs Separate Endpoints

- **With negotiation**:
  - ```url GET /books/1 ``` → Decide response via Accept header.
- **Without negotiation** (separate endpoints):
  - ```url GET /books/1.json ```
  - ```url GET /books/1.xml ```

👉 Negotiation is **cleaner and RESTful**, but separate endpoints may be **easier to test/debug**.

### 6.2 Server-driven vs Client-driven

| **Aspect** | **Server-driven (Accept header)** | **Client-driven (Query params)** |
| --- | --- | --- |
| Example | ```url Accept: application/json ``` | ```url /books/1?format=json ``` |
| Pros | Standards-based, flexible | Simpler, easier to test |
| Cons | Harder to debug | Less RESTful |

## 7\. Advantages & Disadvantages

### ✅ Advantages

- Flexible (same endpoint, multiple formats).
- Standards-based (built into HTTP).
- Useful for versioning and localization.

### ❌ Disadvantages

- More complex to implement on the server side.
- Harder to test/debug compared to explicit query parameters.
- Can confuse clients if not well-documented.

## 8\. Best Practices

- **Always support JSON** (industry standard).
- Use **explicit versioning in headers** (```text Accept: application/vnd.api.v2+json ```) if versioning with negotiation.
- Document supported formats clearly in API docs.
- Handle unsupported formats gracefully with ```text 406 Not Acceptable ```.
- Use ```text Content-Type ``` for request validation (reject XML if only JSON is supported).

## 9\. Conclusion

Content negotiation is a **powerful HTTP feature** that allows APIs to serve **different formats, versions, languages, or encodings** from the same endpoint. While it adds complexity, it’s a best practice for **flexible and scalable APIs**.

In practice:

- ✅ Use **JSON as default**.
- ✅ Support **headers for advanced clients** (versioning, localization).
- ✅ Consider **query params for simplicity** in public APIs.

✅ **In short**:

- Use content negotiation when supporting **multiple formats, languages, or versions**.
- Prefer JSON as a default.
- Return ```text 406 Not Acceptable ``` if requested format is unsupported.
