# Gin Framework — Complete Technical Documentation

> **Framework:** Gin v1.10.x | **Language:** Go 1.22+ | **Author:** Nazmul Hossain
> **Last Updated:** June 2026

---

## Table of Contents

1. [Introduction & Philosophy](#1-introduction--philosophy)
2. [How Gin Works Internally](#2-how-gin-works-internally)
3. [Installation & Project Setup](#3-installation--project-setup)
4. [Core Concepts](#4-core-concepts)
   - 4.1 [Engine & Router](#41-engine--router)
   - 4.2 [Route Parameters & Binding](#42-route-parameters--binding)
   - 4.3 [Context (`gin.Context`)](#43-context-gincontext)
   - 4.4 [Request Binding & Validation](#44-request-binding--validation)
   - 4.5 [Response Rendering](#45-response-rendering)
5. [Middleware System](#5-middleware-system)
6. [Route Groups & Versioning](#6-route-groups--versioning)
7. [Authentication & Security](#7-authentication--security)
8. [Database Integration (GORM + PostgreSQL)](#8-database-integration-gorm--postgresql)
9. [Advanced Patterns](#9-advanced-patterns)
   - 9.1 [Dependency Injection](#91-dependency-injection)
   - 9.2 [Error Handling](#92-error-handling)
   - 9.3 [File Upload & Streaming](#93-file-upload--streaming)
   - 9.4 [WebSockets](#94-websockets)
   - 9.5 [Background Jobs](#95-background-jobs)
10. [Testing](#10-testing)
11. [Real-World Project: MedTrack API in Go](#11-real-world-project-medtrack-api-in-go)
12. [Performance Optimization](#12-performance-optimization)
13. [Deployment](#13-deployment)
14. [Gin vs Other Go Frameworks](#14-gin-vs-other-go-frameworks)

---

## 1. Introduction & Philosophy

**Gin** is a high-performance HTTP web framework for Go, built on top of Go's `net/http` standard library and the `httprouter` package for blazing-fast routing. It was created by Manuel Martínez-Almeida and is one of the most starred Go web frameworks on GitHub.

### Why Gin?

| Feature | net/http | Echo | Fiber | **Gin** |
|---|---|---|---|---|
| Performance | High | High | Very High | **Very High** |
| Middleware | Manual | Built-in | Built-in | **Built-in** |
| Routing | Basic | Radix tree | Radix tree | **Radix tree** |
| Validation | ❌ | ❌ | ❌ | **✅ via validator** |
| JSON binding | Manual | Built-in | Built-in | **Built-in** |
| Community | N/A | Large | Large | **Largest** |
| Maturity | Core stdlib | High | Medium | **Very High** |

### Gin's Core Design Principles

```
Gin Framework Architecture
│
├── httprouter (radix tree)     → O(log n) route matching, zero allocations
├── net/http compatibility      → Works with any standard Go HTTP handler
├── gin.Context (pool)          → Reused via sync.Pool — zero GC pressure
├── validator/v10               → Struct-tag-based validation (go-playground)
└── encoding/json               → Default JSON codec (swappable to sonic/json-iterator)
```

### Performance Benchmark (req/sec, single core)

```
Framework        Req/Sec     Latency
─────────────────────────────────────
Gin              ~97,000     ~10µs
Echo             ~91,000     ~11µs
Fiber (fasthttp) ~190,000    ~5µs   (non-stdlib HTTP)
net/http         ~85,000     ~12µs
```

> Gin uses `sync.Pool` to recycle `gin.Context` objects between requests — this is the primary source of its low GC overhead and high throughput.

---

## 2. How Gin Works Internally

### 2.1 Request Lifecycle

```
Incoming HTTP Request
        │
        ▼
┌───────────────────┐
│  net/http Server  │  ← Go's stdlib HTTP server (TCP listener, HTTP parser)
│  (ListenAndServe) │
└────────┬──────────┘
         │  http.Handler interface → gin.Engine implements ServeHTTP()
         ▼
┌───────────────────┐
│   gin.Engine      │  ← Implements http.Handler
│   ServeHTTP()     │
└────────┬──────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  Radix Tree Router  (httprouter-based)    │
│  Matches: method + path → handler chain  │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  gin.Context acquired from sync.Pool      │
│  (reset and reused — zero allocation)    │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  Middleware Chain (HandlersChain)         │
│  [ Logger → Auth → CORS → YourHandler ]  │
│  Each calls c.Next() to proceed          │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  Your Route Handler                       │
│  c.JSON() / c.Bind() / c.ShouldBind()   │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  Response Writer                          │
│  Buffers headers + body → flushes        │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│  gin.Context returned to sync.Pool       │
└───────────────────────────────────────────┘
         │
         ▼
HTTP Response sent to client
```

### 2.2 Radix Tree Routing

Gin uses a **compressed radix tree** (also called a Patricia trie) for each HTTP method. This gives O(k) lookup where k is the URL length — not O(n) where n is the number of routes.

```
Routes registered:
  GET /api/v1/patients
  GET /api/v1/patients/:id
  GET /api/v1/patients/:id/prescriptions
  GET /api/v1/pharmacy/drugs

Radix Tree (GET):
  /api/v1/
  ├── patients           → handler: ListPatients
  │   └── /:id          → handler: GetPatient
  │       └── /prescriptions → handler: GetRx
  └── pharmacy/drugs     → handler: ListDrugs
```

```go
// How gin internally matches routes (simplified)
// engine.trees is a slice of methodTrees, one per HTTP method
type methodTree struct {
    method string
    root   *node  // radix tree root node
}

// Each node in the radix tree:
type node struct {
    path      string          // path segment
    indices   string          // first char of child paths
    children  []*node         // child nodes
    handlers  HandlersChain   // middleware + handler slice
    priority  uint32          // for ordering wildcard vs static
    nType     nodeType        // static, param, catchAll
    wildChild bool
}
```

### 2.3 Middleware Chain (`HandlersChain`)

```go
// HandlersChain is just a slice of HandlerFunc
type HandlersChain []HandlerFunc
type HandlerFunc func(*Context)

// When you register:
r.GET("/patients", AuthMiddleware(), LogMiddleware(), GetPatientsHandler)
// Gin stores: [AuthMiddleware, LogMiddleware, GetPatientsHandler]
// in the node's handlers field

// Context tracks which handler is currently executing
type Context struct {
    handlers HandlersChain
    index    int8  // current position in chain
    // ...
}

// c.Next() advances the index:
func (c *Context) Next() {
    c.index++
    for c.index < int8(len(c.handlers)) {
        c.handlers[c.index](c)
        c.index++
    }
}

// c.Abort() stops the chain:
func (c *Context) Abort() {
    c.index = abortIndex  // math.MaxInt8 / 2
}
```

### 2.4 sync.Pool — Zero Allocation Context

```go
// Inside gin.Engine:
pool sync.Pool

// On init:
engine.pool.New = func() any {
    return engine.allocateContext(engine.maxParams)
}

// On every request (ServeHTTP):
func (engine *Engine) ServeHTTP(w http.ResponseWriter, req *http.Request) {
    c := engine.pool.Get().(*Context)  // Reuse from pool
    c.writermem.reset(w)
    c.Request = req
    c.reset()                          // Clear all fields
    engine.handleHTTPRequest(c)
    engine.pool.Put(c)                 // Return to pool
}
```

> This is why you **must never store a `*gin.Context` in a goroutine** — by the time the goroutine runs, the context may have been reused for a different request. Always copy what you need.

---

## 3. Installation & Project Setup

### 3.1 Initialize Go Module

```bash
# Create project
mkdir medtrack-gin && cd medtrack-gin
go mod init github.com/nazmul/medtrack-gin

# Install Gin and essential packages
go get github.com/gin-gonic/gin@v1.10.0
go get github.com/gin-contrib/cors
go get github.com/gin-contrib/requestid
go get gorm.io/gorm
go get gorm.io/driver/postgres
go get github.com/golang-jwt/jwt/v5
go get github.com/go-playground/validator/v10
go get github.com/redis/go-redis/v9
go get go.uber.org/zap
go get github.com/spf13/viper
go get golang.org/x/crypto/bcrypt
go get github.com/google/uuid
go get github.com/swaggo/gin-swagger   # OpenAPI docs
go get github.com/swaggo/swag/cmd/swag

# Download all dependencies
go mod tidy
```

### 3.2 Recommended Project Structure

```
medtrack-gin/
│
├── cmd/
│   └── server/
│       └── main.go              ← Entry point
│
├── internal/                    ← Private application code
│   ├── config/
│   │   └── config.go            ← Viper-based config
│   │
│   ├── api/
│   │   ├── router.go            ← Route registration
│   │   ├── middleware/
│   │   │   ├── auth.go
│   │   │   ├── cors.go
│   │   │   ├── logger.go
│   │   │   ├── ratelimit.go
│   │   │   └── recovery.go
│   │   └── handlers/
│   │       ├── auth.go
│   │       ├── patient.go
│   │       ├── prescription.go
│   │       └── analytics.go
│   │
│   ├── domain/                  ← Business logic (framework-agnostic)
│   │   ├── patient/
│   │   │   ├── model.go         ← Domain model
│   │   │   ├── repository.go    ← Interface
│   │   │   └── service.go       ← Business rules
│   │   └── prescription/
│   │       ├── model.go
│   │       ├── repository.go
│   │       └── service.go
│   │
│   ├── repository/              ← GORM implementations
│   │   ├── patient_repo.go
│   │   └── prescription_repo.go
│   │
│   ├── dto/                     ← Request/Response structs
│   │   ├── patient.go
│   │   └── prescription.go
│   │
│   └── db/
│       ├── postgres.go          ← DB connection pool
│       └── migrations/
│
├── pkg/                         ← Reusable public packages
│   ├── apperror/                ← Custom error types
│   ├── response/                ← Standard API response helpers
│   ├── jwt/                     ← JWT utilities
│   └── validator/               ← Custom validation rules
│
├── docs/                        ← Swagger docs (generated)
├── tests/
│   ├── integration/
│   └── unit/
│
├── Dockerfile
├── docker-compose.yml
├── .env
└── go.mod
```

### 3.3 Configuration with Viper

```go
// internal/config/config.go
package config

import (
    "strings"
    "github.com/spf13/viper"
)

type Config struct {
    App      AppConfig
    Database DatabaseConfig
    Redis    RedisConfig
    JWT      JWTConfig
}

type AppConfig struct {
    Name        string `mapstructure:"name"`
    Port        int    `mapstructure:"port"`
    Environment string `mapstructure:"environment"`
    Debug       bool   `mapstructure:"debug"`
}

type DatabaseConfig struct {
    Host         string `mapstructure:"host"`
    Port         int    `mapstructure:"port"`
    User         string `mapstructure:"user"`
    Password     string `mapstructure:"password"`
    Name         string `mapstructure:"name"`
    SSLMode      string `mapstructure:"ssl_mode"`
    MaxOpenConns int    `mapstructure:"max_open_conns"`
    MaxIdleConns int    `mapstructure:"max_idle_conns"`
}

type RedisConfig struct {
    URL      string `mapstructure:"url"`
    Password string `mapstructure:"password"`
    DB       int    `mapstructure:"db"`
}

type JWTConfig struct {
    SecretKey            string `mapstructure:"secret_key"`
    AccessTokenExpireMin int    `mapstructure:"access_token_expire_min"`
    RefreshTokenExpireDays int  `mapstructure:"refresh_token_expire_days"`
}

func Load() (*Config, error) {
    viper.SetConfigName(".env")
    viper.SetConfigType("env")
    viper.AddConfigPath(".")
    viper.AddConfigPath("..")

    // Allow ENV vars to override config file
    viper.AutomaticEnv()
    viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

    // Defaults
    viper.SetDefault("app.port", 8080)
    viper.SetDefault("app.environment", "development")
    viper.SetDefault("database.max_open_conns", 25)
    viper.SetDefault("database.max_idle_conns", 10)
    viper.SetDefault("jwt.access_token_expire_min", 30)
    viper.SetDefault("jwt.refresh_token_expire_days", 7)

    if err := viper.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            return nil, err
        }
    }

    cfg := &Config{}
    if err := viper.Unmarshal(cfg); err != nil {
        return nil, err
    }
    return cfg, nil
}
```

```env
# .env
APP_NAME=MedTrack API
APP_PORT=8080
APP_ENVIRONMENT=development
APP_DEBUG=true

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=medtrack
DATABASE_PASSWORD=secret
DATABASE_NAME=medtrack
DATABASE_SSL_MODE=disable

REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-256-bit-secret-change-in-production
```

---

## 4. Core Concepts

### 4.1 Engine & Router

`gin.Engine` is the core struct — it embeds `RouterGroup` (which provides all the routing methods) and holds the middleware stack, route trees, and configuration.

```go
package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

func main() {
    // gin.Default() = gin.New() + Logger + Recovery middleware
    r := gin.Default()

    // gin.New() = bare engine, no middleware
    r2 := gin.New()
    r2.Use(gin.Logger())    // Add individually
    r2.Use(gin.Recovery())  // Recovers from panics → 500

    // ── Mode ──────────────────────────────────────────
    gin.SetMode(gin.ReleaseMode)  // Disables debug logs in prod
    // gin.DebugMode / gin.TestMode

    // ── Engine-level config ───────────────────────────
    r.MaxMultipartMemory = 8 << 20  // 8 MiB for file uploads
    r.HandleMethodNotAllowed = true  // Return 405 instead of 404
    r.ForwardedByClientIP = true     // Trust X-Forwarded-For

    // ── Trusted proxies ───────────────────────────────
    // IMPORTANT: Always set this in production behind a proxy
    r.SetTrustedProxies([]string{"10.0.0.0/8", "172.16.0.0/12"})

    // ── Basic routes ──────────────────────────────────
    r.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{"status": "healthy"})
    })

    // ── Custom 404 / 405 ──────────────────────────────
    r.NoRoute(func(c *gin.Context) {
        c.JSON(http.StatusNotFound, gin.H{
            "code":    "NOT_FOUND",
            "message": "The requested route does not exist",
        })
    })
    r.NoMethod(func(c *gin.Context) {
        c.JSON(http.StatusMethodNotAllowed, gin.H{
            "code":    "METHOD_NOT_ALLOWED",
            "message": "HTTP method not allowed for this route",
        })
    })

    // ── Start server ──────────────────────────────────
    r.Run(":8080")  // Shorthand for http.ListenAndServe

    // Or with custom server (recommended for production):
    srv := &http.Server{
        Addr:         ":8080",
        Handler:      r,
        ReadTimeout:  15 * time.Second,
        WriteTimeout: 15 * time.Second,
        IdleTimeout:  60 * time.Second,
    }
    srv.ListenAndServe()
}
```

### 4.2 Route Parameters & Binding

```go
// ── Path Parameters ────────────────────────────────────────────
// :param   → required, matches everything except /
// *param   → wildcard, matches everything including /

r.GET("/patients/:id", func(c *gin.Context) {
    id := c.Param("id")             // string — always a string from path
    c.JSON(200, gin.H{"id": id})
})

r.GET("/files/*filepath", func(c *gin.Context) {
    path := c.Param("filepath")     // "/folder/file.pdf"
    c.JSON(200, gin.H{"path": path})
})

// ── Query Parameters ───────────────────────────────────────────
r.GET("/patients", func(c *gin.Context) {
    page      := c.DefaultQuery("page", "1")       // with default
    perPage   := c.DefaultQuery("per_page", "20")
    search    := c.Query("search")                 // "" if not present
    isActive  := c.QueryArray("status")            // ?status=A&status=B → []string

    // Check if param exists explicitly
    query, exists := c.GetQuery("search")
    _ = exists  // bool

    c.JSON(200, gin.H{
        "page":      page,
        "per_page":  perPage,
        "search":    search,
        "is_active": isActive,
        "query":     query,
    })
})

// ── Form Data ─────────────────────────────────────────────────
r.POST("/upload", func(c *gin.Context) {
    name    := c.PostForm("name")
    email   := c.DefaultPostForm("email", "unknown@example.com")
    tags    := c.PostFormArray("tags")  // Multiple values for same key

    c.JSON(200, gin.H{"name": name, "email": email, "tags": tags})
})

// ── Header & Cookie ───────────────────────────────────────────
r.GET("/info", func(c *gin.Context) {
    apiKey    := c.GetHeader("X-API-Key")
    userAgent := c.GetHeader("User-Agent")
    token, _  := c.Cookie("session_token")  // (value, error)

    c.JSON(200, gin.H{"api_key": apiKey, "ua": userAgent, "token": token})
})
```

### 4.3 Context (`gin.Context`)

`gin.Context` is the most important type in Gin. It carries the request, response writer, path params, and a key-value store for sharing data between middleware and handlers.

```go
// gin.Context key fields (simplified):
type Context struct {
    // Public fields
    Request  *http.Request
    Writer   ResponseWriter

    // Params (path parameters)
    Params   Params

    // Keys — shared data between middleware/handlers
    Keys     map[string]any

    // Internal
    handlers HandlersChain
    index    int8
    engine   *Engine
    // ...
}

// ── Key-Value Store (sharing between middleware) ───────────────
// In AuthMiddleware:
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // ... validate token ...
        user := fetchUserFromDB(claims.UserID)
        c.Set("current_user", user)     // Store any type
        c.Set("user_id", claims.UserID) // Store primitives
        c.Next()                        // Continue to next handler
    }
}

// In handler:
func GetPatient(c *gin.Context) {
    // Type-safe retrieval
    user, exists := c.Get("current_user")
    if !exists {
        c.AbortWithStatusJSON(401, gin.H{"error": "Unauthorized"})
        return
    }
    currentUser := user.(*domain.User)  // Type assertion

    // Convenience typed getters
    userID, _ := c.Get("user_id")
    id := userID.(int64)
    _ = id
}

// ── Request Info Helpers ──────────────────────────────────────
func InfoHandler(c *gin.Context) {
    clientIP    := c.ClientIP()          // Respects X-Forwarded-For
    method      := c.Request.Method
    path        := c.FullPath()          // Route pattern: /patients/:id
    requestURI  := c.Request.RequestURI  // Actual URI: /patients/42?foo=bar
    contentType := c.ContentType()
    isJSON      := c.IsWebsocket()
    _ = clientIP; _ = method; _ = path
    _ = requestURI; _ = contentType; _ = isJSON
}

// ── Flow Control ──────────────────────────────────────────────
func SomeMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if unauthorized {
            c.AbortWithStatusJSON(401, gin.H{"error": "Unauthorized"})
            // AbortWithStatus(401) + JSON response + stops chain
            return
        }
        c.Next()     // Proceed to next handler in chain
        // Code here runs AFTER the handler returns (like defer)
        // Useful for logging response status, cleanup, etc.
        status := c.Writer.Status()
        log.Printf("Response status: %d", status)
    }
}
```

### 4.4 Request Binding & Validation

This is where Gin truly shines. `ShouldBind*` uses `go-playground/validator/v10` under the hood.

```go
// dto/patient.go
package dto

import "time"

// ── Struct tags ────────────────────────────────────────────────
// json:"..."    → JSON field name
// form:"..."    → Form field name (query/form)
// uri:"..."     → Path parameter name
// binding:"..." → Validation rules (go-playground/validator)
// example:"..."  → Swagger example (optional)

type CreatePatientRequest struct {
    FullName         string    `json:"full_name"        binding:"required,min=2,max=100"`
    Email            string    `json:"email"            binding:"required,email"`
    Phone            string    `json:"phone"            binding:"required,e164"`
    DateOfBirth      time.Time `json:"date_of_birth"    binding:"required"`
    BloodGroup       string    `json:"blood_group"      binding:"required,oneof=A+ A- B+ B- O+ O- AB+ AB-"`
    WeightKg         float64   `json:"weight_kg"        binding:"required,gt=0,lt=500"`
    HeightCm         float64   `json:"height_cm"        binding:"required,gt=0,lt=300"`
    Allergies        []string  `json:"allergies"        binding:"omitempty,dive,min=2"`
    EmergencyContact string    `json:"emergency_contact" binding:"omitempty,min=5"`
}

type UpdatePatientRequest struct {
    FullName         *string  `json:"full_name"         binding:"omitempty,min=2,max=100"`
    Phone            *string  `json:"phone"             binding:"omitempty,e164"`
    WeightKg         *float64 `json:"weight_kg"         binding:"omitempty,gt=0,lt=500"`
    HeightCm         *float64 `json:"height_cm"         binding:"omitempty,gt=0,lt=300"`
    EmergencyContact *string  `json:"emergency_contact" binding:"omitempty,min=5"`
}

// URI params binding
type PatientURI struct {
    ID int64 `uri:"id" binding:"required,min=1"`
}

// Query params binding
type ListPatientsQuery struct {
    Page     int    `form:"page"      binding:"omitempty,min=1"`
    PerPage  int    `form:"per_page"  binding:"omitempty,min=1,max=100"`
    Search   string `form:"search"    binding:"omitempty,min=3,max=100"`
    IsActive *bool  `form:"is_active" binding:"omitempty"`
    SortBy   string `form:"sort_by"   binding:"omitempty,oneof=created_at full_name email"`
    SortDir  string `form:"sort_dir"  binding:"omitempty,oneof=asc desc"`
}

func (q *ListPatientsQuery) Defaults() {
    if q.Page == 0 {
        q.Page = 1
    }
    if q.PerPage == 0 {
        q.PerPage = 20
    }
    if q.SortBy == "" {
        q.SortBy = "created_at"
    }
    if q.SortDir == "" {
        q.SortDir = "desc"
    }
}
```

```go
// handlers/patient.go — binding in action
package handlers

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "github.com/nazmul/medtrack-gin/internal/dto"
)

type PatientHandler struct {
    service domain.PatientService
}

func (h *PatientHandler) CreatePatient(c *gin.Context) {
    var req dto.CreatePatientRequest

    // ShouldBindJSON: binds + validates, returns error (doesn't abort)
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusUnprocessableEntity, gin.H{
            "code":    "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors":  formatValidationErrors(err),
        })
        return
    }

    patient, err := h.service.Create(c.Request.Context(), req)
    if err != nil {
        handleServiceError(c, err)
        return
    }

    c.JSON(http.StatusCreated, gin.H{
        "success": true,
        "data":    patient,
        "message": "Patient created successfully",
    })
}

func (h *PatientHandler) GetPatient(c *gin.Context) {
    // Bind URI params separately
    var uri dto.PatientURI
    if err := c.ShouldBindUri(&uri); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid patient ID"})
        return
    }

    patient, err := h.service.GetByID(c.Request.Context(), uri.ID)
    if err != nil {
        handleServiceError(c, err)
        return
    }

    c.JSON(http.StatusOK, gin.H{"success": true, "data": patient})
}

func (h *PatientHandler) ListPatients(c *gin.Context) {
    var query dto.ListPatientsQuery
    if err := c.ShouldBindQuery(&query); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    query.Defaults()

    patients, total, err := h.service.List(c.Request.Context(), query)
    if err != nil {
        handleServiceError(c, err)
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "success":     true,
        "data":        patients,
        "total":       total,
        "page":        query.Page,
        "per_page":    query.PerPage,
        "total_pages": (total + int64(query.PerPage) - 1) / int64(query.PerPage),
    })
}
```

```go
// pkg/validator/errors.go — Format validator errors for API responses
package validator

import (
    "fmt"
    "strings"
    "github.com/go-playground/validator/v10"
)

type FieldError struct {
    Field   string `json:"field"`
    Message string `json:"message"`
    Value   any    `json:"value,omitempty"`
}

func FormatErrors(err error) []FieldError {
    var errs []FieldError

    if validationErrs, ok := err.(validator.ValidationErrors); ok {
        for _, e := range validationErrs {
            field := strings.ToLower(e.Field())
            errs = append(errs, FieldError{
                Field:   field,
                Message: fieldErrorMsg(e),
                Value:   e.Value(),
            })
        }
    } else {
        errs = append(errs, FieldError{
            Field:   "body",
            Message: err.Error(),
        })
    }
    return errs
}

func fieldErrorMsg(e validator.FieldError) string {
    switch e.Tag() {
    case "required":
        return fmt.Sprintf("%s is required", e.Field())
    case "email":
        return fmt.Sprintf("%s must be a valid email address", e.Field())
    case "min":
        if e.Type().Kind().String() == "string" {
            return fmt.Sprintf("%s must be at least %s characters", e.Field(), e.Param())
        }
        return fmt.Sprintf("%s must be at least %s", e.Field(), e.Param())
    case "max":
        return fmt.Sprintf("%s must not exceed %s", e.Field(), e.Param())
    case "oneof":
        return fmt.Sprintf("%s must be one of: %s", e.Field(), strings.ReplaceAll(e.Param(), " ", ", "))
    case "gt":
        return fmt.Sprintf("%s must be greater than %s", e.Field(), e.Param())
    case "lt":
        return fmt.Sprintf("%s must be less than %s", e.Field(), e.Param())
    case "e164":
        return fmt.Sprintf("%s must be a valid phone number in E.164 format (+8801XXXXXXXXX)", e.Field())
    default:
        return fmt.Sprintf("%s failed validation: %s", e.Field(), e.Tag())
    }
}

// Register custom validators
func RegisterCustomValidators(v *validator.Validate) {
    // Custom: validate NID (Bangladesh National ID)
    v.RegisterValidation("nid", func(fl validator.FieldLevel) bool {
        nid := fl.Field().String()
        return len(nid) == 10 || len(nid) == 13 || len(nid) == 17
    })

    // Custom: validate prescription number format RX-YYYYMMDD-XXXXXX
    v.RegisterValidation("rx_number", func(fl validator.FieldLevel) bool {
        val := fl.Field().String()
        return len(val) == 20 && strings.HasPrefix(val, "RX-")
    })
}
```

### 4.5 Response Rendering

```go
package handlers

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

func ResponseExamples(c *gin.Context) {
    // ── JSON ──────────────────────────────────────────────────
    c.JSON(http.StatusOK, gin.H{
        "message": "Hello MedTrack",
        "version": "1.0.0",
    })

    // With struct
    type Patient struct {
        ID   int64  `json:"id"`
        Name string `json:"name"`
    }
    c.JSON(200, Patient{ID: 1, Name: "John"})

    // ── Indented JSON (pretty print) ──────────────────────────
    c.IndentedJSON(200, gin.H{"data": "pretty"})

    // ── Pure JSON (fastest — disables HTML escaping) ──────────
    c.PureJSON(200, gin.H{"html": "<b>not escaped</b>"})

    // ── XML ───────────────────────────────────────────────────
    c.XML(200, gin.H{"message": "XML response"})

    // ── String ───────────────────────────────────────────────
    c.String(200, "Patient %d found: %s", 42, "John Doe")

    // ── HTML Template ─────────────────────────────────────────
    c.HTML(200, "patient.html", gin.H{"name": "John"})

    // ── File / Download ───────────────────────────────────────
    c.File("./reports/patient_42.pdf")
    c.FileAttachment("./reports/patient_42.pdf", "patient_report.pdf")

    // ── Redirect ──────────────────────────────────────────────
    c.Redirect(http.StatusMovedPermanently, "/api/v2/patients")

    // ── Stream (SSE / chunked) ────────────────────────────────
    c.Stream(func(w io.Writer) bool {
        c.SSEvent("message", gin.H{"data": "chunk"})
        time.Sleep(1 * time.Second)
        return true  // return false to stop streaming
    })

    // ── Raw bytes ─────────────────────────────────────────────
    data := []byte{0x89, 0x50, 0x4E, 0x47} // PNG header
    c.Data(200, "image/png", data)

    // ── Status only (no body) ─────────────────────────────────
    c.Status(http.StatusNoContent) // 204
}
```

---

## 5. Middleware System

Middleware in Gin is just a `gin.HandlerFunc` that calls `c.Next()` to pass control forward and can optionally do work after the chain returns.

### 5.1 Logger Middleware (Production-grade with Zap)

```go
// internal/api/middleware/logger.go
package middleware

import (
    "time"
    "github.com/gin-gonic/gin"
    "go.uber.org/zap"
    "github.com/gin-contrib/requestid"
)

func ZapLogger(logger *zap.Logger) gin.HandlerFunc {
    return func(c *gin.Context) {
        start  := time.Now()
        path   := c.Request.URL.Path
        raw    := c.Request.URL.RawQuery
        reqID  := requestid.Get(c)

        // Process request
        c.Next()

        // After handler returns:
        latency    := time.Since(start)
        statusCode := c.Writer.Status()
        clientIP   := c.ClientIP()
        method     := c.Request.Method
        bodySize   := c.Writer.Size()

        if raw != "" {
            path = path + "?" + raw
        }

        fields := []zap.Field{
            zap.String("request_id",  reqID),
            zap.String("method",      method),
            zap.String("path",        path),
            zap.String("client_ip",   clientIP),
            zap.Int("status",         statusCode),
            zap.Duration("latency",   latency),
            zap.Int("body_size",      bodySize),
            zap.String("user_agent",  c.Request.UserAgent()),
        }

        // Add error if any
        if len(c.Errors) > 0 {
            fields = append(fields, zap.String("errors", c.Errors.String()))
        }

        switch {
        case statusCode >= 500:
            logger.Error("Server error", fields...)
        case statusCode >= 400:
            logger.Warn("Client error", fields...)
        default:
            logger.Info("Request", fields...)
        }
    }
}
```

### 5.2 JWT Auth Middleware

```go
// internal/api/middleware/auth.go
package middleware

import (
    "net/http"
    "strings"
    "github.com/gin-gonic/gin"
    jwtpkg "github.com/nazmul/medtrack-gin/pkg/jwt"
    "github.com/nazmul/medtrack-gin/internal/domain/user"
)

func JWTAuth(userRepo user.Repository) gin.HandlerFunc {
    return func(c *gin.Context) {
        // Extract token from Authorization header
        authHeader := c.GetHeader("Authorization")
        if authHeader == "" {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
                "code":    "MISSING_TOKEN",
                "message": "Authorization header is required",
            })
            return
        }

        parts := strings.SplitN(authHeader, " ", 2)
        if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
                "code":    "INVALID_TOKEN_FORMAT",
                "message": "Authorization header format: Bearer <token>",
            })
            return
        }

        claims, err := jwtpkg.ParseToken(parts[1])
        if err != nil {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
                "code":    "INVALID_TOKEN",
                "message": err.Error(),
            })
            return
        }

        // Fetch user from DB (or Redis cache)
        currentUser, err := userRepo.FindByID(c.Request.Context(), claims.UserID)
        if err != nil || currentUser == nil {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
                "code":    "USER_NOT_FOUND",
                "message": "User associated with token not found",
            })
            return
        }

        if !currentUser.IsActive {
            c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
                "code":    "ACCOUNT_DEACTIVATED",
                "message": "Your account has been deactivated",
            })
            return
        }

        // Store in context for downstream handlers
        c.Set("current_user", currentUser)
        c.Set("user_id", currentUser.ID)
        c.Set("user_role", currentUser.Role)
        c.Next()
    }
}

// Role-based authorization middleware factory
func RequireRole(roles ...string) gin.HandlerFunc {
    roleSet := make(map[string]bool, len(roles))
    for _, r := range roles {
        roleSet[r] = true
    }

    return func(c *gin.Context) {
        role, exists := c.Get("user_role")
        if !exists {
            c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
                "code":    "NO_ROLE",
                "message": "User role not found in context",
            })
            return
        }

        if !roleSet[role.(string)] {
            c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
                "code":    "INSUFFICIENT_PERMISSIONS",
                "message": "You don't have permission to access this resource",
            })
            return
        }
        c.Next()
    }
}
```

### 5.3 Rate Limiting Middleware (Redis-based)

```go
// internal/api/middleware/ratelimit.go
package middleware

import (
    "context"
    "fmt"
    "net/http"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/redis/go-redis/v9"
)

type RateLimiterConfig struct {
    Requests int           // Number of requests allowed
    Window   time.Duration // Time window
    KeyFunc  func(*gin.Context) string // How to identify client
}

func RateLimiter(rdb *redis.Client, cfg RateLimiterConfig) gin.HandlerFunc {
    if cfg.KeyFunc == nil {
        cfg.KeyFunc = func(c *gin.Context) string {
            return c.ClientIP()
        }
    }

    return func(c *gin.Context) {
        ctx := context.Background()
        key := fmt.Sprintf("rate_limit:%s:%s", cfg.KeyFunc(c), c.FullPath())

        // Sliding window using Redis sorted set
        now := time.Now().UnixMilli()
        windowStart := now - cfg.Window.Milliseconds()

        pipe := rdb.Pipeline()
        pipe.ZRemRangeByScore(ctx, key, "0", fmt.Sprintf("%d", windowStart))
        pipe.ZCard(ctx, key)
        pipe.ZAdd(ctx, key, redis.Z{Score: float64(now), Member: now})
        pipe.Expire(ctx, key, cfg.Window)

        results, err := pipe.Exec(ctx)
        if err != nil {
            // On Redis failure, allow request (fail open)
            c.Next()
            return
        }

        count := results[1].(*redis.IntCmd).Val()
        remaining := int64(cfg.Requests) - count
        resetTime := time.Now().Add(cfg.Window).Unix()

        c.Header("X-RateLimit-Limit", fmt.Sprintf("%d", cfg.Requests))
        c.Header("X-RateLimit-Remaining", fmt.Sprintf("%d", max(0, remaining)))
        c.Header("X-RateLimit-Reset", fmt.Sprintf("%d", resetTime))

        if count > int64(cfg.Requests) {
            c.Header("Retry-After", fmt.Sprintf("%d", int(cfg.Window.Seconds())))
            c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
                "code":        "RATE_LIMIT_EXCEEDED",
                "message":     "Too many requests, please slow down",
                "retry_after": int(cfg.Window.Seconds()),
            })
            return
        }

        c.Next()
    }
}

func max(a, b int64) int64 {
    if a > b {
        return a
    }
    return b
}
```

### 5.4 CORS Middleware

```go
// internal/api/middleware/cors.go
package middleware

import (
    "github.com/gin-contrib/cors"
    "time"
)

func CORS(allowedOrigins []string) gin.HandlerFunc {
    return cors.New(cors.Config{
        AllowOrigins:     allowedOrigins,
        AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
        AllowHeaders:     []string{
            "Origin", "Content-Type", "Authorization",
            "X-API-Key", "X-Request-ID", "X-Client-Version",
        },
        ExposeHeaders:    []string{"X-Request-ID", "X-Process-Time", "X-RateLimit-Remaining"},
        AllowCredentials: true,
        MaxAge:           12 * time.Hour,
    })
}
```

---

## 6. Route Groups & Versioning

```go
// internal/api/router.go
package api

import (
    "github.com/gin-gonic/gin"
    "github.com/gin-contrib/requestid"
    "github.com/nazmul/medtrack-gin/internal/api/handlers"
    "github.com/nazmul/medtrack-gin/internal/api/middleware"
)

type Router struct {
    engine          *gin.Engine
    patientHandler  *handlers.PatientHandler
    rxHandler       *handlers.PrescriptionHandler
    authHandler     *handlers.AuthHandler
    analyticsHandler *handlers.AnalyticsHandler
    // dependencies
    rdb             *redis.Client
    userRepo        user.Repository
    logger          *zap.Logger
}

func (r *Router) Setup() {
    engine := r.engine

    // ── Global Middleware ──────────────────────────────────────
    engine.Use(
        requestid.New(),                                   // X-Request-ID header
        middleware.CORS([]string{"https://medeasy.health"}),
        middleware.ZapLogger(r.logger),
        gin.Recovery(),                                    // Panic recovery → 500
        middleware.RateLimiter(r.rdb, middleware.RateLimiterConfig{
            Requests: 200,
            Window:   60 * time.Second,
        }),
    )

    // ── Public Routes ─────────────────────────────────────────
    engine.GET("/health", r.authHandler.HealthCheck)
    engine.GET("/ready", r.authHandler.ReadinessCheck)

    // ── API v1 ────────────────────────────────────────────────
    v1 := engine.Group("/api/v1")
    {
        // Auth (public)
        auth := v1.Group("/auth")
        {
            auth.POST("/register", r.authHandler.Register)
            auth.POST("/login", r.authHandler.Login)
            auth.POST("/refresh", r.authHandler.RefreshToken)
            auth.POST("/logout", middleware.JWTAuth(r.userRepo), r.authHandler.Logout)
        }

        // Prescription verification (public — for QR code scanning)
        v1.GET("/prescriptions/verify/:number", r.rxHandler.VerifyPrescription)

        // Protected routes (require JWT)
        protected := v1.Group("/")
        protected.Use(middleware.JWTAuth(r.userRepo))
        {
            // Patients
            patients := protected.Group("/patients")
            {
                patients.GET("",    r.patientHandler.ListPatients)
                patients.GET("/:id", r.patientHandler.GetPatient)
                patients.POST("",
                    middleware.RequireRole("doctor", "admin"),
                    r.patientHandler.CreatePatient,
                )
                patients.PATCH("/:id",
                    middleware.RequireRole("doctor", "admin"),
                    r.patientHandler.UpdatePatient,
                )
                patients.DELETE("/:id",
                    middleware.RequireRole("admin"),
                    r.patientHandler.DeletePatient,
                )
                // Nested resource
                patients.GET("/:id/prescriptions", r.rxHandler.GetPatientPrescriptions)
                patients.GET("/:id/adherence",     r.rxHandler.GetAdherenceReport)
            }

            // Prescriptions
            rx := protected.Group("/prescriptions")
            {
                rx.GET("",    r.rxHandler.ListPrescriptions)
                rx.GET("/:id", r.rxHandler.GetPrescription)
                rx.POST("",
                    middleware.RequireRole("doctor"),
                    middleware.RateLimiter(r.rdb, middleware.RateLimiterConfig{
                        Requests: 10,
                        Window:   60 * time.Second,
                        KeyFunc:  func(c *gin.Context) string {
                            id, _ := c.Get("user_id")
                            return fmt.Sprintf("doctor:%v", id)
                        },
                    }),
                    r.rxHandler.CreatePrescription,
                )
                rx.PATCH("/:id/dispense",
                    middleware.RequireRole("pharmacist", "admin"),
                    r.rxHandler.DispensePrescription,
                )
                rx.PATCH("/:id/cancel",
                    middleware.RequireRole("doctor", "admin"),
                    r.rxHandler.CancelPrescription,
                )
            }

            // Analytics (admin only)
            analytics := protected.Group("/analytics")
            analytics.Use(middleware.RequireRole("admin"))
            {
                analytics.GET("/dashboard", r.analyticsHandler.Dashboard)
                analytics.GET("/prescriptions", r.analyticsHandler.PrescriptionStats)
                analytics.GET("/adherence",      r.analyticsHandler.AdherenceStats)
            }
        }
    }

    // ── API v2 (future) ───────────────────────────────────────
    v2 := engine.Group("/api/v2")
    v2.Use(middleware.JWTAuth(r.userRepo))
    {
        // v2 endpoints...
        _ = v2
    }
}
```

---

## 7. Authentication & Security

### 7.1 JWT Package

```go
// pkg/jwt/jwt.go
package jwt

import (
    "errors"
    "time"
    "github.com/golang-jwt/jwt/v5"
)

var (
    ErrTokenExpired = errors.New("token has expired")
    ErrTokenInvalid = errors.New("token is invalid")
)

type TokenType string
const (
    AccessToken  TokenType = "access"
    RefreshToken TokenType = "refresh"
)

type Claims struct {
    UserID int64     `json:"user_id"`
    Email  string    `json:"email"`
    Role   string    `json:"role"`
    Type   TokenType `json:"type"`
    jwt.RegisteredClaims
}

type Manager struct {
    secretKey        []byte
    accessExpireMin  int
    refreshExpireDays int
}

func NewManager(secretKey string, accessMin, refreshDays int) *Manager {
    return &Manager{
        secretKey:        []byte(secretKey),
        accessExpireMin:  accessMin,
        refreshExpireDays: refreshDays,
    }
}

func (m *Manager) GenerateAccessToken(userID int64, email, role string) (string, error) {
    claims := &Claims{
        UserID: userID,
        Email:  email,
        Role:   role,
        Type:   AccessToken,
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Duration(m.accessExpireMin) * time.Minute)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
            Issuer:    "medtrack-api",
        },
    }
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(m.secretKey)
}

func (m *Manager) GenerateRefreshToken(userID int64) (string, error) {
    claims := &Claims{
        UserID: userID,
        Type:   RefreshToken,
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Duration(m.refreshExpireDays) * 24 * time.Hour)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
            Issuer:    "medtrack-api",
        },
    }
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(m.secretKey)
}

func (m *Manager) ParseToken(tokenStr string) (*Claims, error) {
    token, err := jwt.ParseWithClaims(
        tokenStr,
        &Claims{},
        func(token *jwt.Token) (any, error) {
            if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
                return nil, ErrTokenInvalid
            }
            return m.secretKey, nil
        },
        jwt.WithValidMethods([]string{"HS256"}),
    )

    if err != nil {
        if errors.Is(err, jwt.ErrTokenExpired) {
            return nil, ErrTokenExpired
        }
        return nil, ErrTokenInvalid
    }

    claims, ok := token.Claims.(*Claims)
    if !ok || !token.Valid {
        return nil, ErrTokenInvalid
    }
    return claims, nil
}
```

### 7.2 Auth Handler

```go
// internal/api/handlers/auth.go
package handlers

import (
    "net/http"
    "golang.org/x/crypto/bcrypt"
    "github.com/gin-gonic/gin"
)

type AuthHandler struct {
    userRepo   user.Repository
    jwtManager *jwt.Manager
    rdb        *redis.Client
    logger     *zap.Logger
}

type LoginRequest struct {
    Email    string `json:"email"    binding:"required,email"`
    Password string `json:"password" binding:"required,min=8"`
}

type TokenResponse struct {
    AccessToken  string `json:"access_token"`
    RefreshToken string `json:"refresh_token"`
    TokenType    string `json:"token_type"`
    ExpiresIn    int    `json:"expires_in"` // seconds
}

func (h *AuthHandler) Login(c *gin.Context) {
    var req LoginRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusUnprocessableEntity, gin.H{
            "code":   "VALIDATION_ERROR",
            "errors": validator.FormatErrors(err),
        })
        return
    }

    u, err := h.userRepo.FindByEmail(c.Request.Context(), req.Email)
    if err != nil || u == nil {
        // Constant-time response to prevent user enumeration
        bcrypt.CompareHashAndPassword([]byte("$2a$10$dummy"), []byte(req.Password))
        c.JSON(http.StatusUnauthorized, gin.H{
            "code":    "INVALID_CREDENTIALS",
            "message": "Incorrect email or password",
        })
        return
    }

    if err := bcrypt.CompareHashAndPassword([]byte(u.HashedPassword), []byte(req.Password)); err != nil {
        c.JSON(http.StatusUnauthorized, gin.H{
            "code":    "INVALID_CREDENTIALS",
            "message": "Incorrect email or password",
        })
        return
    }

    if !u.IsActive {
        c.JSON(http.StatusForbidden, gin.H{
            "code":    "ACCOUNT_DEACTIVATED",
            "message": "Your account has been deactivated",
        })
        return
    }

    accessToken, err := h.jwtManager.GenerateAccessToken(u.ID, u.Email, u.Role)
    if err != nil {
        h.logger.Error("Failed to generate access token", zap.Error(err))
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Token generation failed"})
        return
    }

    refreshToken, err := h.jwtManager.GenerateRefreshToken(u.ID)
    if err != nil {
        h.logger.Error("Failed to generate refresh token", zap.Error(err))
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Token generation failed"})
        return
    }

    // Store refresh token in Redis (for revocation)
    key := fmt.Sprintf("refresh_token:%d", u.ID)
    h.rdb.Set(c.Request.Context(), key, refreshToken,
        time.Duration(h.jwtManager.RefreshExpireDays)*24*time.Hour)

    c.JSON(http.StatusOK, TokenResponse{
        AccessToken:  accessToken,
        RefreshToken: refreshToken,
        TokenType:    "Bearer",
        ExpiresIn:    h.jwtManager.AccessExpireMin * 60,
    })
}

func (h *AuthHandler) Logout(c *gin.Context) {
    userID, _ := c.Get("user_id")

    // Invalidate refresh token in Redis
    key := fmt.Sprintf("refresh_token:%v", userID)
    h.rdb.Del(c.Request.Context(), key)

    // Add access token to denylist until expiry
    authHeader := c.GetHeader("Authorization")
    token := strings.TrimPrefix(authHeader, "Bearer ")
    claims, _ := h.jwtManager.ParseToken(token)
    if claims != nil {
        denyKey := fmt.Sprintf("token_denylist:%s", token[:16]) // prefix for memory efficiency
        ttl := time.Until(claims.ExpiresAt.Time)
        h.rdb.Set(c.Request.Context(), denyKey, "1", ttl)
    }

    c.JSON(http.StatusOK, gin.H{"message": "Logged out successfully"})
}
```

---

## 8. Database Integration (GORM + PostgreSQL)

### 8.1 Database Setup

```go
// internal/db/postgres.go
package db

import (
    "fmt"
    "time"
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
    "gorm.io/gorm/logger"
    "go.uber.org/zap"
)

func NewPostgresDB(cfg *config.DatabaseConfig, zapLogger *zap.Logger) (*gorm.DB, error) {
    dsn := fmt.Sprintf(
        "host=%s user=%s password=%s dbname=%s port=%d sslmode=%s TimeZone=Asia/Dhaka",
        cfg.Host, cfg.User, cfg.Password, cfg.Name, cfg.Port, cfg.SSLMode,
    )

    gormCfg := &gorm.Config{
        Logger: logger.Default.LogMode(logger.Info),
        NowFunc: func() time.Time {
            return time.Now().UTC()
        },
        PrepareStmt: true, // Cache prepared statements → faster repeated queries
    }

    db, err := gorm.Open(postgres.New(postgres.Config{
        DSN:                  dsn,
        PreferSimpleProtocol: false, // Use extended protocol for better performance
    }), gormCfg)
    if err != nil {
        return nil, fmt.Errorf("failed to connect to database: %w", err)
    }

    // Configure connection pool
    sqlDB, err := db.DB()
    if err != nil {
        return nil, err
    }

    sqlDB.SetMaxOpenConns(cfg.MaxOpenConns)
    sqlDB.SetMaxIdleConns(cfg.MaxIdleConns)
    sqlDB.SetConnMaxLifetime(time.Hour)
    sqlDB.SetConnMaxIdleTime(30 * time.Minute)

    return db, nil
}
```

### 8.2 GORM Models

```go
// internal/domain/patient/model.go
package patient

import (
    "time"
    "gorm.io/gorm"
    "github.com/lib/pq"
)

type BloodGroup string

const (
    BloodGroupAPos  BloodGroup = "A+"
    BloodGroupANeg  BloodGroup = "A-"
    BloodGroupBPos  BloodGroup = "B+"
    BloodGroupBNeg  BloodGroup = "B-"
    BloodGroupOPos  BloodGroup = "O+"
    BloodGroupONeg  BloodGroup = "O-"
    BloodGroupABPos BloodGroup = "AB+"
    BloodGroupABNeg BloodGroup = "AB-"
)

type Patient struct {
    ID               int64          `gorm:"primaryKey;autoIncrement" json:"id"`
    FullName         string         `gorm:"not null;size:100;index"   json:"full_name"`
    Email            string         `gorm:"uniqueIndex;not null;size:255" json:"email"`
    Phone            string         `gorm:"not null;size:20"          json:"phone"`
    DateOfBirth      time.Time      `gorm:"not null"                  json:"date_of_birth"`
    BloodGroup       BloodGroup     `gorm:"size:5"                    json:"blood_group"`
    WeightKg         *float64       `gorm:"type:decimal(5,2)"         json:"weight_kg,omitempty"`
    HeightCm         *float64       `gorm:"type:decimal(5,2)"         json:"height_cm,omitempty"`
    Allergies        pq.StringArray `gorm:"type:text[]"               json:"allergies"`
    EmergencyContact string         `gorm:"size:200"                  json:"emergency_contact,omitempty"`
    IsActive         bool           `gorm:"default:true;not null"     json:"is_active"`
    CreatedAt        time.Time      `json:"created_at"`
    UpdatedAt        time.Time      `json:"updated_at"`
    DeletedAt        gorm.DeletedAt `gorm:"index"                     json:"-"` // Soft delete

    // Associations
    Prescriptions []Prescription `gorm:"foreignKey:PatientID"  json:"prescriptions,omitempty"`
    User          *User          `gorm:"foreignKey:PatientID"  json:"user,omitempty"`
}

// TableName overrides the table name
func (Patient) TableName() string { return "patients" }

// Hooks
func (p *Patient) BeforeCreate(tx *gorm.DB) error {
    // Normalize phone
    p.Phone = normalizePhone(p.Phone)
    return nil
}

func (p *Patient) AfterCreate(tx *gorm.DB) error {
    // Could trigger async event here
    return nil
}

// domain/prescription/model.go
type PrescriptionStatus string

const (
    StatusActive    PrescriptionStatus = "active"
    StatusDispensed PrescriptionStatus = "dispensed"
    StatusCompleted PrescriptionStatus = "completed"
    StatusCancelled PrescriptionStatus = "cancelled"
    StatusExpired   PrescriptionStatus = "expired"
)

type MedicationFrequency string

const (
    FreqOnceDaily       MedicationFrequency = "once_daily"
    FreqTwiceDaily      MedicationFrequency = "twice_daily"
    FreqThreeTimesDaily MedicationFrequency = "three_times_daily"
    FreqEvery8Hours     MedicationFrequency = "every_8_hours"
    FreqEvery12Hours    MedicationFrequency = "every_12_hours"
    FreqAsNeeded        MedicationFrequency = "as_needed"
    FreqWeekly          MedicationFrequency = "weekly"
)

type PrescribedMedication struct {
    DrugGenericName string              `json:"drug_generic_name"`
    DrugBrandName   string              `json:"drug_brand_name,omitempty"`
    Strength        string              `json:"strength"`
    DosageForm      string              `json:"dosage_form"`
    Frequency       MedicationFrequency `json:"frequency"`
    DurationDays    int                 `json:"duration_days"`
    Quantity        int                 `json:"quantity"`
    Instructions    string              `json:"instructions,omitempty"`
    IsBeforeFood    bool                `json:"is_before_food"`
}

type Prescription struct {
    ID                   int64              `gorm:"primaryKey;autoIncrement"  json:"id"`
    PrescriptionNumber   string             `gorm:"uniqueIndex;not null;size:25" json:"prescription_number"`
    PatientID            int64              `gorm:"not null;index"            json:"patient_id"`
    DoctorID             int64              `gorm:"not null;index"            json:"doctor_id"`
    Diagnosis            string             `gorm:"not null;size:500"         json:"diagnosis"`
    ChiefComplaint       string             `gorm:"not null;size:500"         json:"chief_complaint"`
    Medications          datatypes.JSON     `gorm:"not null;type:jsonb"       json:"medications"`
    Notes                string             `gorm:"size:1000"                 json:"notes,omitempty"`
    Status               PrescriptionStatus `gorm:"not null;default:'active'" json:"status"`
    FollowUpDate         *time.Time         `json:"follow_up_date,omitempty"`
    IssuedAt             time.Time          `gorm:"not null"                  json:"issued_at"`
    ExpiresAt            time.Time          `gorm:"not null;index"            json:"expires_at"`
    DispensedByID        *int64             `json:"dispensed_by_id,omitempty"`
    DispensedAt          *time.Time         `json:"dispensed_at,omitempty"`
    QRCodeURL            string             `gorm:"size:500"                  json:"qr_code_url,omitempty"`
    CreatedAt            time.Time          `json:"created_at"`
    UpdatedAt            time.Time          `json:"updated_at"`

    // Associations (preloaded)
    Patient  *Patient `gorm:"foreignKey:PatientID" json:"patient,omitempty"`
    Doctor   *User    `gorm:"foreignKey:DoctorID"  json:"doctor,omitempty"`
}
```

### 8.3 Repository Pattern

```go
// internal/domain/patient/repository.go
package patient

import "context"

// Interface — testable, framework-agnostic
type Repository interface {
    FindByID(ctx context.Context, id int64) (*Patient, error)
    FindByEmail(ctx context.Context, email string) (*Patient, error)
    List(ctx context.Context, opts ListOptions) ([]*Patient, int64, error)
    Create(ctx context.Context, p *Patient) error
    Update(ctx context.Context, p *Patient) error
    SoftDelete(ctx context.Context, id int64) error
    ExistsByEmail(ctx context.Context, email string, excludeID ...int64) (bool, error)
}

type ListOptions struct {
    Page     int
    PerPage  int
    Search   string
    IsActive *bool
    SortBy   string
    SortDir  string
}

// internal/repository/patient_repo.go — GORM implementation
package repository

import (
    "context"
    "errors"
    "gorm.io/gorm"
    "github.com/nazmul/medtrack-gin/internal/domain/patient"
)

type patientRepository struct {
    db *gorm.DB
}

func NewPatientRepository(db *gorm.DB) patient.Repository {
    return &patientRepository{db: db}
}

func (r *patientRepository) FindByID(ctx context.Context, id int64) (*patient.Patient, error) {
    var p patient.Patient
    err := r.db.WithContext(ctx).
        Preload("Prescriptions", func(db *gorm.DB) *gorm.DB {
            return db.Where("status = ?", patient.StatusActive).Limit(5)
        }).
        First(&p, id).Error

    if errors.Is(err, gorm.ErrRecordNotFound) {
        return nil, nil // Not found → nil, nil (caller checks for nil)
    }
    return &p, err
}

func (r *patientRepository) List(ctx context.Context, opts patient.ListOptions) ([]*patient.Patient, int64, error) {
    var patients []*patient.Patient
    var total int64

    query := r.db.WithContext(ctx).Model(&patient.Patient{})

    // Dynamic filters
    if opts.Search != "" {
        search := "%" + opts.Search + "%"
        query = query.Where(
            "full_name ILIKE ? OR email ILIKE ? OR phone LIKE ?",
            search, search, search,
        )
    }
    if opts.IsActive != nil {
        query = query.Where("is_active = ?", *opts.IsActive)
    }

    // Count total before pagination
    if err := query.Count(&total).Error; err != nil {
        return nil, 0, fmt.Errorf("count patients: %w", err)
    }

    // Apply sorting and pagination
    sortColumn := map[string]string{
        "created_at": "created_at",
        "full_name":  "full_name",
        "email":      "email",
    }[opts.SortBy]
    if sortColumn == "" {
        sortColumn = "created_at"
    }
    sortDir := "DESC"
    if opts.SortDir == "asc" {
        sortDir = "ASC"
    }

    offset := (opts.Page - 1) * opts.PerPage
    err := query.
        Order(fmt.Sprintf("%s %s", sortColumn, sortDir)).
        Offset(offset).
        Limit(opts.PerPage).
        Find(&patients).Error

    return patients, total, err
}

func (r *patientRepository) Create(ctx context.Context, p *patient.Patient) error {
    return r.db.WithContext(ctx).Create(p).Error
}

func (r *patientRepository) Update(ctx context.Context, p *patient.Patient) error {
    return r.db.WithContext(ctx).Save(p).Error
}

func (r *patientRepository) SoftDelete(ctx context.Context, id int64) error {
    return r.db.WithContext(ctx).Delete(&patient.Patient{}, id).Error
}

func (r *patientRepository) ExistsByEmail(ctx context.Context, email string, excludeID ...int64) (bool, error) {
    query := r.db.WithContext(ctx).Model(&patient.Patient{}).Where("email = ?", email)
    if len(excludeID) > 0 && excludeID[0] > 0 {
        query = query.Where("id != ?", excludeID[0])
    }
    var count int64
    err := query.Count(&count).Error
    return count > 0, err
}
```

---

## 9. Advanced Patterns

### 9.1 Dependency Injection

Go doesn't have built-in DI, so we use constructor injection (the most idiomatic approach), optionally with `google/wire` for large codebases.

```go
// cmd/server/main.go — manual wiring (clear and explicit)
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "go.uber.org/zap"
)

func main() {
    // ── Config ────────────────────────────────────────────────
    cfg, err := config.Load()
    if err != nil {
        log.Fatalf("Failed to load config: %v", err)
    }

    // ── Logger ────────────────────────────────────────────────
    var logger *zap.Logger
    if cfg.App.Debug {
        logger, _ = zap.NewDevelopment()
    } else {
        logger, _ = zap.NewProduction()
    }
    defer logger.Sync()

    // ── Database ──────────────────────────────────────────────
    gormDB, err := db.NewPostgresDB(&cfg.Database, logger)
    if err != nil {
        logger.Fatal("Failed to connect to database", zap.Error(err))
    }

    // Auto-migrate
    gormDB.AutoMigrate(
        &user.User{},
        &patient.Patient{},
        &prescription.Prescription{},
        &audit.AuditLog{},
    )

    // ── Redis ─────────────────────────────────────────────────
    rdb := redis.NewClient(&redis.Options{
        Addr:     cfg.Redis.URL,
        Password: cfg.Redis.Password,
        DB:       cfg.Redis.DB,
    })

    // ── JWT Manager ───────────────────────────────────────────
    jwtManager := jwt.NewManager(
        cfg.JWT.SecretKey,
        cfg.JWT.AccessTokenExpireMin,
        cfg.JWT.RefreshTokenExpireDays,
    )

    // ── Repositories ──────────────────────────────────────────
    userRepo     := repository.NewUserRepository(gormDB)
    patientRepo  := repository.NewPatientRepository(gormDB)
    rxRepo       := repository.NewPrescriptionRepository(gormDB)
    doseRepo     := repository.NewDoseLogRepository(gormDB)

    // ── Services ──────────────────────────────────────────────
    patientSvc := patient.NewService(patientRepo, logger)
    rxSvc      := prescription.NewService(rxRepo, patientRepo, doseRepo, rdb, logger)
    authSvc    := user.NewAuthService(userRepo, jwtManager, rdb, logger)

    // ── Handlers ──────────────────────────────────────────────
    authHandler     := handlers.NewAuthHandler(authSvc, logger)
    patientHandler  := handlers.NewPatientHandler(patientSvc, logger)
    rxHandler       := handlers.NewPrescriptionHandler(rxSvc, logger)
    analyticsHandler := handlers.NewAnalyticsHandler(patientRepo, rxRepo, logger)

    // ── Gin Engine ────────────────────────────────────────────
    if cfg.App.Environment == "production" {
        gin.SetMode(gin.ReleaseMode)
    }
    engine := gin.New()

    // ── Router ────────────────────────────────────────────────
    router := &api.Router{
        Engine:           engine,
        PatientHandler:   patientHandler,
        RxHandler:        rxHandler,
        AuthHandler:      authHandler,
        AnalyticsHandler: analyticsHandler,
        UserRepo:         userRepo,
        Rdb:              rdb,
        Logger:           logger,
    }
    router.Setup()

    // ── HTTP Server ───────────────────────────────────────────
    srv := &http.Server{
        Addr:         fmt.Sprintf(":%d", cfg.App.Port),
        Handler:      engine,
        ReadTimeout:  15 * time.Second,
        WriteTimeout: 30 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    // ── Graceful Shutdown ─────────────────────────────────────
    go func() {
        logger.Info("Starting server", zap.Int("port", cfg.App.Port))
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            logger.Fatal("Server failed", zap.Error(err))
        }
    }()

    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    logger.Info("Shutting down server...")
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := srv.Shutdown(ctx); err != nil {
        logger.Fatal("Server forced to shutdown", zap.Error(err))
    }
    logger.Info("Server stopped gracefully")
}
```

### 9.2 Error Handling

```go
// pkg/apperror/errors.go
package apperror

import (
    "errors"
    "net/http"
)

type AppError struct {
    Code       string `json:"code"`
    Message    string `json:"message"`
    StatusCode int    `json:"-"`
    Err        error  `json:"-"`
}

func (e *AppError) Error() string { return e.Message }
func (e *AppError) Unwrap() error { return e.Err }

func New(code, message string, statusCode int, err ...error) *AppError {
    ae := &AppError{Code: code, Message: message, StatusCode: statusCode}
    if len(err) > 0 {
        ae.Err = err[0]
    }
    return ae
}

// Constructors
func NotFound(resource string, id any) *AppError {
    return New("NOT_FOUND", fmt.Sprintf("%s with id '%v' not found", resource, id), http.StatusNotFound)
}

func Conflict(message string) *AppError {
    return New("CONFLICT", message, http.StatusConflict)
}

func Unauthorized(message string) *AppError {
    return New("UNAUTHORIZED", message, http.StatusUnauthorized)
}

func Forbidden(message string) *AppError {
    return New("FORBIDDEN", message, http.StatusForbidden)
}

func Internal(message string, err error) *AppError {
    return New("INTERNAL_ERROR", message, http.StatusInternalServerError, err)
}

func BadRequest(message string) *AppError {
    return New("BAD_REQUEST", message, http.StatusBadRequest)
}

// Helper used in all handlers
func HandleServiceError(c *gin.Context, err error) {
    var appErr *AppError
    if errors.As(err, &appErr) {
        c.JSON(appErr.StatusCode, gin.H{
            "success": false,
            "code":    appErr.Code,
            "message": appErr.Message,
        })
        return
    }

    // Unknown error — log and return generic 500
    c.JSON(http.StatusInternalServerError, gin.H{
        "success": false,
        "code":    "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
    })
}
```

### 9.3 File Upload & Streaming

```go
// handlers/prescription.go — PDF generation and file upload
func (h *PrescriptionHandler) UploadPrescriptionScan(c *gin.Context) {
    var uri dto.PrescriptionURI
    if err := c.ShouldBindUri(&uri); err != nil {
        c.JSON(400, gin.H{"error": "Invalid prescription ID"})
        return
    }

    // Limit upload size: 5MB
    c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 5<<20)

    file, header, err := c.Request.FormFile("scan")
    if err != nil {
        c.JSON(400, gin.H{"error": "No file uploaded or file too large (max 5MB)"})
        return
    }
    defer file.Close()

    // Validate MIME type
    buf := make([]byte, 512)
    if _, err := file.Read(buf); err != nil {
        c.JSON(400, gin.H{"error": "Failed to read file"})
        return
    }
    mimeType := http.DetectContentType(buf)
    allowedTypes := map[string]bool{
        "image/jpeg": true,
        "image/png":  true,
        "application/pdf": true,
    }
    if !allowedTypes[mimeType] {
        c.JSON(415, gin.H{"error": "Only JPEG, PNG, and PDF files are allowed"})
        return
    }

    // Reset reader
    file.Seek(0, io.SeekStart)

    // Save to disk (or upload to S3/Azure Blob)
    filename := fmt.Sprintf("rx_%d_%s%s",
        uri.ID,
        uuid.New().String(),
        filepath.Ext(header.Filename),
    )
    savePath := filepath.Join("./uploads/prescriptions", filename)

    if err := c.SaveUploadedFile(header, savePath); err != nil {
        c.JSON(500, gin.H{"error": "Failed to save file"})
        return
    }

    c.JSON(200, gin.H{
        "filename": filename,
        "size":     header.Size,
        "mime":     mimeType,
        "url":      fmt.Sprintf("/files/prescriptions/%s", filename),
    })
}

// Stream large CSV export
func (h *AnalyticsHandler) ExportPatients(c *gin.Context) {
    c.Header("Content-Type", "text/csv")
    c.Header("Content-Disposition", "attachment; filename=patients_export.csv")
    c.Header("Transfer-Encoding", "chunked")

    c.Stream(func(w io.Writer) bool {
        csvWriter := csv.NewWriter(w)

        // Write header
        csvWriter.Write([]string{"ID", "Full Name", "Email", "Phone", "Blood Group", "Created At"})
        csvWriter.Flush()

        // Stream in batches of 1000 rows
        page := 1
        for {
            patients, _, err := h.patientRepo.List(context.Background(), patient.ListOptions{
                Page: page, PerPage: 1000, SortBy: "id", SortDir: "asc",
            })
            if err != nil || len(patients) == 0 {
                return false // Stop streaming
            }

            for _, p := range patients {
                csvWriter.Write([]string{
                    fmt.Sprintf("%d", p.ID),
                    p.FullName,
                    p.Email,
                    p.Phone,
                    string(p.BloodGroup),
                    p.CreatedAt.Format(time.RFC3339),
                })
            }
            csvWriter.Flush()

            if len(patients) < 1000 {
                return false // Last page
            }
            page++
        }
    })
}
```

### 9.4 WebSockets

```go
// internal/api/handlers/ws.go
package handlers

import (
    "encoding/json"
    "net/http"
    "sync"

    "github.com/gin-gonic/gin"
    "golang.org/x/net/websocket"
    "nhooyr.io/websocket"
    "nhooyr.io/websocket/wsjson"
)

// Using nhooyr.io/websocket (gorilla is archived; nhooyr is maintained)
type WSMessage struct {
    Type    string          `json:"type"`
    Payload json.RawMessage `json:"payload"`
}

type Hub struct {
    mu      sync.RWMutex
    rooms   map[string]map[*websocket.Conn]bool
}

var hub = &Hub{rooms: make(map[string]map[*websocket.Conn]bool)}

func (h *Hub) Join(roomID string, conn *websocket.Conn) {
    h.mu.Lock()
    defer h.mu.Unlock()
    if h.rooms[roomID] == nil {
        h.rooms[roomID] = make(map[*websocket.Conn]bool)
    }
    h.rooms[roomID][conn] = true
}

func (h *Hub) Leave(roomID string, conn *websocket.Conn) {
    h.mu.Lock()
    defer h.mu.Unlock()
    delete(h.rooms[roomID], conn)
}

func (h *Hub) Broadcast(ctx context.Context, roomID string, msg any) {
    h.mu.RLock()
    conns := h.rooms[roomID]
    h.mu.RUnlock()

    for conn := range conns {
        go wsjson.Write(ctx, conn, msg)
    }
}

func (h *WSHandler) HandleNotifications(c *gin.Context) {
    userID, _ := c.Get("user_id")
    roomID := fmt.Sprintf("user_%v", userID)

    conn, err := websocket.Accept(c.Writer, c.Request, &websocket.AcceptOptions{
        OriginPatterns: []string{"medeasy.health", "localhost:*"},
    })
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "WebSocket upgrade failed"})
        return
    }
    defer conn.CloseNow()

    hub.Join(roomID, conn)
    defer hub.Leave(roomID, conn)

    ctx := c.Request.Context()
    for {
        var msg WSMessage
        if err := wsjson.Read(ctx, conn, &msg); err != nil {
            break // Client disconnected
        }

        switch msg.Type {
        case "ping":
            wsjson.Write(ctx, conn, WSMessage{Type: "pong"})
        case "dose_ack":
            // Patient acknowledged a medication reminder
            var ack struct{ MedicationID int64 `json:"medication_id"` }
            json.Unmarshal(msg.Payload, &ack)
            h.rxSvc.AcknowledgeDoseReminder(ctx, userID.(int64), ack.MedicationID)
        }
    }
}
```

### 9.5 Background Jobs

```go
// internal/jobs/scheduler.go
package jobs

import (
    "context"
    "time"
    "go.uber.org/zap"
)

type Scheduler struct {
    rxRepo  prescription.Repository
    hub     *handlers.Hub
    logger  *zap.Logger
    rdb     *redis.Client
}

func (s *Scheduler) Start(ctx context.Context) {
    // Medication reminder check — runs every minute
    go s.runEvery(ctx, 1*time.Minute, s.SendMedicationReminders)

    // Expire prescriptions — runs every hour
    go s.runEvery(ctx, 1*time.Hour, s.ExpirePrescriptions)

    // Weekly adherence report — runs every Monday 8am
    go s.runAt(ctx, "Monday", 8, 0, s.SendAdherenceReports)
}

func (s *Scheduler) runEvery(ctx context.Context, interval time.Duration, fn func(context.Context)) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()
    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            fn(ctx)
        }
    }
}

func (s *Scheduler) SendMedicationReminders(ctx context.Context) {
    // Find medications due in next 15 minutes
    activePrescriptions, _ := s.rxRepo.FindActiveDue(ctx, 15*time.Minute)

    for _, rx := range activePrescriptions {
        roomID := fmt.Sprintf("user_%d", rx.PatientID)
        s.hub.Broadcast(ctx, roomID, map[string]any{
            "type": "medication_reminder",
            "payload": map[string]any{
                "prescription_id":  rx.ID,
                "drug_name":        rx.Medications[0].DrugGenericName,
                "due_at":           time.Now().Add(15 * time.Minute),
                "instructions":     rx.Medications[0].Instructions,
            },
        })
        s.logger.Info("Reminder sent", zap.Int64("patient_id", rx.PatientID))
    }
}

func (s *Scheduler) ExpirePrescriptions(ctx context.Context) {
    result := s.rxRepo.DB.WithContext(ctx).
        Model(&prescription.Prescription{}).
        Where("status = ? AND expires_at < ?", prescription.StatusActive, time.Now()).
        Update("status", prescription.StatusExpired)

    if result.RowsAffected > 0 {
        s.logger.Info("Prescriptions expired", zap.Int64("count", result.RowsAffected))
    }
}
```

---

## 10. Testing

### 10.1 Unit Tests

```go
// tests/unit/patient_service_test.go
package unit

import (
    "context"
    "errors"
    "testing"
    "time"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/mock"
)

// Mock repository
type MockPatientRepository struct {
    mock.Mock
}

func (m *MockPatientRepository) FindByID(ctx context.Context, id int64) (*patient.Patient, error) {
    args := m.Called(ctx, id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*patient.Patient), args.Error(1)
}

func (m *MockPatientRepository) ExistsByEmail(ctx context.Context, email string, excludeID ...int64) (bool, error) {
    args := m.Called(ctx, email)
    return args.Bool(0), args.Error(1)
}

func (m *MockPatientRepository) Create(ctx context.Context, p *patient.Patient) error {
    args := m.Called(ctx, p)
    p.ID = 1  // Simulate DB auto-increment
    return args.Error(0)
}

// Ensure mock implements interface at compile time
var _ patient.Repository = (*MockPatientRepository)(nil)

func TestPatientService_Create_Success(t *testing.T) {
    mockRepo := new(MockPatientRepository)
    logger, _ := zap.NewNop(), nil
    svc := patient.NewService(mockRepo, logger)

    req := dto.CreatePatientRequest{
        FullName:    "Test Patient",
        Email:       "test@example.com",
        Phone:       "+8801700000000",
        DateOfBirth: time.Date(1990, 1, 15, 0, 0, 0, 0, time.UTC),
        BloodGroup:  "O+",
        WeightKg:    70.0,
        HeightCm:    170.0,
    }

    mockRepo.On("ExistsByEmail", mock.Anything, "test@example.com").Return(false, nil)
    mockRepo.On("Create", mock.Anything, mock.AnythingOfType("*patient.Patient")).Return(nil)

    result, err := svc.Create(context.Background(), req)

    assert.NoError(t, err)
    assert.NotNil(t, result)
    assert.Equal(t, "Test Patient", result.FullName)
    assert.Equal(t, int64(1), result.ID)
    mockRepo.AssertExpectations(t)
}

func TestPatientService_Create_DuplicateEmail(t *testing.T) {
    mockRepo := new(MockPatientRepository)
    svc := patient.NewService(mockRepo, zap.NewNop())

    req := dto.CreatePatientRequest{Email: "exists@example.com"}
    mockRepo.On("ExistsByEmail", mock.Anything, "exists@example.com").Return(true, nil)

    _, err := svc.Create(context.Background(), req)

    assert.Error(t, err)
    var appErr *apperror.AppError
    assert.True(t, errors.As(err, &appErr))
    assert.Equal(t, "CONFLICT", appErr.Code)
    mockRepo.AssertNotCalled(t, "Create")
}
```

### 10.2 Integration / Handler Tests

```go
// tests/integration/patient_handler_test.go
package integration

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/gin-gonic/gin"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/suite"
)

type PatientHandlerSuite struct {
    suite.Suite
    router *gin.Engine
    db     *gorm.DB
    token  string
}

func (s *PatientHandlerSuite) SetupSuite() {
    gin.SetMode(gin.TestMode)

    // Use in-memory SQLite for integration tests
    db, _ := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
    db.AutoMigrate(&user.User{}, &patient.Patient{})
    s.db = db

    // Wire up the full stack
    jwtManager := jwt.NewManager("test-secret", 30, 7)
    userRepo    := repository.NewUserRepository(db)
    patientRepo := repository.NewPatientRepository(db)
    patientSvc  := patient.NewService(patientRepo, zap.NewNop())
    authSvc     := user.NewAuthService(userRepo, jwtManager, nil, zap.NewNop())
    patientH    := handlers.NewPatientHandler(patientSvc, zap.NewNop())
    authH       := handlers.NewAuthHandler(authSvc, zap.NewNop())

    s.router = gin.New()
    s.router.POST("/api/v1/auth/login", authH.Login)

    protected := s.router.Group("/api/v1")
    protected.Use(middleware.JWTAuth(userRepo))
    protected.GET("/patients", patientH.ListPatients)
    protected.POST("/patients", middleware.RequireRole("doctor", "admin"), patientH.CreatePatient)
    protected.GET("/patients/:id", patientH.GetPatient)

    // Create test admin user
    hashedPw, _ := bcrypt.GenerateFromPassword([]byte("testpass123"), 10)
    testUser := &user.User{Email: "admin@test.com", HashedPassword: string(hashedPw), Role: "admin", IsActive: true}
    db.Create(testUser)

    // Get auth token
    s.token = s.getToken("admin@test.com", "testpass123")
}

func (s *PatientHandlerSuite) getToken(email, password string) string {
    body, _ := json.Marshal(map[string]string{"email": email, "password": password})
    w := httptest.NewRecorder()
    req, _ := http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer(body))
    req.Header.Set("Content-Type", "application/json")
    s.router.ServeHTTP(w, req)

    var resp map[string]any
    json.Unmarshal(w.Body.Bytes(), &resp)
    return resp["access_token"].(string)
}

func (s *PatientHandlerSuite) makeRequest(method, path string, body any) *httptest.ResponseRecorder {
    var reqBody *bytes.Buffer
    if body != nil {
        b, _ := json.Marshal(body)
        reqBody = bytes.NewBuffer(b)
    } else {
        reqBody = &bytes.Buffer{}
    }

    w := httptest.NewRecorder()
    req, _ := http.NewRequest(method, path, reqBody)
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+s.token)
    s.router.ServeHTTP(w, req)
    return w
}

func (s *PatientHandlerSuite) TestCreatePatient_Success() {
    payload := map[string]any{
        "full_name":    "John Doe",
        "email":        "john.doe@example.com",
        "phone":        "+8801700000001",
        "date_of_birth": "1990-01-15T00:00:00Z",
        "blood_group":  "O+",
        "weight_kg":    70.0,
        "height_cm":    170.0,
    }

    w := s.makeRequest("POST", "/api/v1/patients", payload)

    s.Equal(http.StatusCreated, w.Code)
    var resp map[string]any
    json.Unmarshal(w.Body.Bytes(), &resp)
    s.True(resp["success"].(bool))
    s.Equal("John Doe", resp["data"].(map[string]any)["full_name"])
}

func (s *PatientHandlerSuite) TestCreatePatient_ValidationError() {
    payload := map[string]any{
        "full_name": "J",              // Too short
        "email":     "not-an-email",   // Invalid
    }
    w := s.makeRequest("POST", "/api/v1/patients", payload)

    s.Equal(http.StatusUnprocessableEntity, w.Code)
    var resp map[string]any
    json.Unmarshal(w.Body.Bytes(), &resp)
    s.Equal("VALIDATION_ERROR", resp["code"])
}

func (s *PatientHandlerSuite) TestGetPatient_NotFound() {
    w := s.makeRequest("GET", "/api/v1/patients/99999", nil)
    s.Equal(http.StatusNotFound, w.Code)
}

func (s *PatientHandlerSuite) TestListPatients_Unauthenticated() {
    w := httptest.NewRecorder()
    req, _ := http.NewRequest("GET", "/api/v1/patients", nil)
    s.router.ServeHTTP(w, req)
    s.Equal(http.StatusUnauthorized, w.Code)
}

func TestPatientHandlerSuite(t *testing.T) {
    suite.Run(t, new(PatientHandlerSuite))
}
```

---

## 11. Real-World Project: MedTrack API in Go

This is a complete prescription and medication tracking system solving real digital health problems — identical domain to the FastAPI version but built idiomatically in Go.

### 11.1 Service Layer (Business Logic)

```go
// internal/domain/prescription/service.go
package prescription

import (
    "context"
    "crypto/rand"
    "fmt"
    "time"

    "github.com/nazmul/medtrack-gin/pkg/apperror"
    "go.uber.org/zap"
)

type Service interface {
    Create(ctx context.Context, req dto.CreatePrescriptionRequest, doctorID int64) (*Prescription, error)
    GetByID(ctx context.Context, id int64, requesterID int64, requesterRole string) (*Prescription, error)
    ListByPatient(ctx context.Context, patientID int64) ([]*Prescription, error)
    Dispense(ctx context.Context, id int64, pharmacistID int64) (*Prescription, error)
    Cancel(ctx context.Context, id int64, doctorID int64, reason string) (*Prescription, error)
    Verify(ctx context.Context, prescriptionNumber string) (*VerificationResult, error)
    LogDose(ctx context.Context, req dto.LogDoseRequest, patientID int64) error
    GetAdherenceReport(ctx context.Context, patientID int64, days int) (*AdherenceReport, error)
}

type service struct {
    rxRepo     Repository
    patientRepo patient.Repository
    doseRepo   DoseLogRepository
    rdb        *redis.Client
    logger     *zap.Logger
}

func NewService(
    rxRepo Repository,
    patientRepo patient.Repository,
    doseRepo DoseLogRepository,
    rdb *redis.Client,
    logger *zap.Logger,
) Service {
    return &service{rxRepo: rxRepo, patientRepo: patientRepo, doseRepo: doseRepo, rdb: rdb, logger: logger}
}

func (s *service) Create(ctx context.Context, req dto.CreatePrescriptionRequest, doctorID int64) (*Prescription, error) {
    // Verify patient exists
    patient, err := s.patientRepo.FindByID(ctx, req.PatientID)
    if err != nil {
        return nil, apperror.Internal("Failed to fetch patient", err)
    }
    if patient == nil {
        return nil, apperror.NotFound("Patient", req.PatientID)
    }
    if !patient.IsActive {
        return nil, apperror.BadRequest("Cannot prescribe for an inactive patient")
    }

    // Check for drug interactions (simplified)
    if warnings := checkDrugInteractions(req.Medications, patient.Allergies); len(warnings) > 0 {
        s.logger.Warn("Drug allergy interaction detected",
            zap.Int64("patient_id", req.PatientID),
            zap.Strings("warnings", warnings),
        )
    }

    rxNumber, err := generatePrescriptionNumber()
    if err != nil {
        return nil, apperror.Internal("Failed to generate prescription number", err)
    }

    now := time.Now().UTC()
    rx := &Prescription{
        PrescriptionNumber: rxNumber,
        PatientID:          req.PatientID,
        DoctorID:           doctorID,
        Diagnosis:          req.Diagnosis,
        ChiefComplaint:     req.ChiefComplaint,
        Notes:              req.Notes,
        Status:             StatusActive,
        IssuedAt:           now,
        ExpiresAt:          now.AddDate(0, 0, req.ValidityDays),
    }

    // Marshal medications to JSONB
    medsJSON, _ := json.Marshal(req.Medications)
    rx.Medications = datatypes.JSON(medsJSON)

    if req.FollowUpDate != nil {
        rx.FollowUpDate = req.FollowUpDate
    }

    if err := s.rxRepo.Create(ctx, rx); err != nil {
        return nil, apperror.Internal("Failed to create prescription", err)
    }

    // Async: Generate QR code (non-blocking)
    go s.attachQRCode(context.Background(), rx.ID, rxNumber)

    s.logger.Info("Prescription created",
        zap.String("rx_number", rxNumber),
        zap.Int64("patient_id", req.PatientID),
        zap.Int64("doctor_id", doctorID),
    )

    return rx, nil
}

func (s *service) Dispense(ctx context.Context, id int64, pharmacistID int64) (*Prescription, error) {
    rx, err := s.rxRepo.FindByID(ctx, id)
    if err != nil {
        return nil, apperror.Internal("DB error", err)
    }
    if rx == nil {
        return nil, apperror.NotFound("Prescription", id)
    }

    if rx.Status != StatusActive {
        return nil, apperror.Conflict(
            fmt.Sprintf("Prescription is already '%s'. Cannot dispense.", rx.Status),
        )
    }
    if time.Now().After(rx.ExpiresAt) {
        // Auto-expire
        rx.Status = StatusExpired
        s.rxRepo.Update(ctx, rx)
        return nil, apperror.Conflict("Prescription has expired and cannot be dispensed")
    }

    now := time.Now().UTC()
    rx.Status      = StatusDispensed
    rx.DispensedByID = &pharmacistID
    rx.DispensedAt  = &now

    if err := s.rxRepo.Update(ctx, rx); err != nil {
        return nil, apperror.Internal("Failed to update prescription", err)
    }

    // Cache invalidation
    cacheKey := fmt.Sprintf("rx:%d", id)
    s.rdb.Del(ctx, cacheKey)

    // Notify patient via WebSocket
    go func() {
        // hub.Broadcast(...)
    }()

    return rx, nil
}

func (s *service) GetAdherenceReport(ctx context.Context, patientID int64, days int) (*AdherenceReport, error) {
    since := time.Now().AddDate(0, 0, -days)

    // Cache check
    cacheKey := fmt.Sprintf("adherence:%d:%d", patientID, days)
    cached, err := s.rdb.Get(ctx, cacheKey).Result()
    if err == nil {
        var report AdherenceReport
        if json.Unmarshal([]byte(cached), &report) == nil {
            return &report, nil
        }
    }

    // Get active prescriptions
    prescriptions, err := s.rxRepo.FindActiveByPatient(ctx, patientID, since)
    if err != nil {
        return nil, apperror.Internal("Failed to fetch prescriptions", err)
    }

    // Calculate expected doses
    freqMap := map[MedicationFrequency]float64{
        FreqOnceDaily:       1,
        FreqTwiceDaily:      2,
        FreqThreeTimesDaily: 3,
        FreqEvery8Hours:     3,
        FreqEvery12Hours:    2,
        FreqWeekly:          1.0 / 7,
        FreqAsNeeded:        0,
    }

    totalExpected := 0
    for _, rx := range prescriptions {
        var meds []PrescribedMedication
        json.Unmarshal(rx.Medications, &meds)
        for _, med := range meds {
            daily := freqMap[med.Frequency]
            dur := math.Min(float64(med.DurationDays), float64(days))
            totalExpected += int(daily * dur)
        }
    }

    // Count actual dose logs
    dosesTaken, err := s.doseRepo.CountByPatient(ctx, patientID, since)
    if err != nil {
        return nil, apperror.Internal("Failed to count doses", err)
    }

    adherencePct := 100.0
    if totalExpected > 0 {
        adherencePct = math.Min(100.0, float64(dosesTaken)/float64(totalExpected)*100)
    }

    riskLevel := "low"
    switch {
    case adherencePct < 60:
        riskLevel = "high"
    case adherencePct < 80:
        riskLevel = "medium"
    }

    streak, _ := s.calculateStreak(ctx, patientID)

    report := &AdherenceReport{
        PatientID:            patientID,
        PeriodDays:           days,
        TotalDosesRequired:   totalExpected,
        TotalDosesTaken:      int(dosesTaken),
        AdherencePercentage:  math.Round(adherencePct*100) / 100,
        MissedDoses:          totalExpected - int(dosesTaken),
        StreakDays:           streak,
        RiskLevel:            riskLevel,
    }

    // Cache for 10 minutes
    reportJSON, _ := json.Marshal(report)
    s.rdb.Set(ctx, cacheKey, reportJSON, 10*time.Minute)

    return report, nil
}

func generatePrescriptionNumber() (string, error) {
    b := make([]byte, 3)
    if _, err := rand.Read(b); err != nil {
        return "", err
    }
    return fmt.Sprintf("RX-%s-%X", time.Now().Format("20060102"), b), nil
}

func checkDrugInteractions(meds []dto.PrescribedMedication, allergies []string) []string {
    var warnings []string
    allergySet := make(map[string]bool)
    for _, a := range allergies {
        allergySet[strings.ToLower(a)] = true
    }
    for _, med := range meds {
        if allergySet[strings.ToLower(med.DrugGenericName)] {
            warnings = append(warnings, fmt.Sprintf("Patient is allergic to %s", med.DrugGenericName))
        }
    }
    return warnings
}
```

### 11.2 Analytics Handler

```go
// internal/api/handlers/analytics.go
package handlers

import (
    "context"
    "net/http"
    "sync"
    "time"

    "github.com/gin-gonic/gin"
)

type DashboardStats struct {
    PeriodDays           int                  `json:"period_days"`
    NewPatients          int64                `json:"new_patients"`
    TotalPrescriptions   int64                `json:"total_prescriptions"`
    DispensedRx          int64                `json:"dispensed_prescriptions"`
    DispenseRate         float64              `json:"dispense_rate_pct"`
    AvgAdherencePct      float64              `json:"avg_adherence_pct"`
    TopDiagnoses         []DiagnosisCount     `json:"top_diagnoses"`
    TopMedications       []MedicationCount    `json:"top_medications"`
    DailyRxTrend         []DailyCount         `json:"daily_rx_trend"`
    HighRiskPatients     int64                `json:"high_risk_patients"`
}

func (h *AnalyticsHandler) Dashboard(c *gin.Context) {
    var query struct {
        PeriodDays int `form:"period_days" binding:"omitempty,min=1,max=365"`
    }
    if err := c.ShouldBindQuery(&query); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    if query.PeriodDays == 0 {
        query.PeriodDays = 30
    }

    since := time.Now().AddDate(0, 0, -query.PeriodDays)
    ctx := c.Request.Context()

    // Run all DB queries concurrently
    var (
        newPatients        int64
        totalRx            int64
        dispensedRx        int64
        avgAdherence       float64
        topDiagnoses       []DiagnosisCount
        topMeds            []MedicationCount
        dailyTrend         []DailyCount
        highRisk           int64
        wg                 sync.WaitGroup
        mu                 sync.Mutex
        errs               []error
    )

    run := func(fn func() error) {
        wg.Add(1)
        go func() {
            defer wg.Done()
            if err := fn(); err != nil {
                mu.Lock()
                errs = append(errs, err)
                mu.Unlock()
            }
        }()
    }

    run(func() error {
        return h.db.WithContext(ctx).Model(&patient.Patient{}).
            Where("created_at >= ?", since).Count(&newPatients).Error
    })

    run(func() error {
        return h.db.WithContext(ctx).Model(&prescription.Prescription{}).
            Where("issued_at >= ?", since).Count(&totalRx).Error
    })

    run(func() error {
        return h.db.WithContext(ctx).Model(&prescription.Prescription{}).
            Where("issued_at >= ? AND status = ?", since, prescription.StatusDispensed).
            Count(&dispensedRx).Error
    })

    run(func() error {
        return h.db.WithContext(ctx).Raw(`
            SELECT diagnosis, COUNT(*) as count
            FROM prescriptions
            WHERE issued_at >= ?
            GROUP BY diagnosis
            ORDER BY count DESC
            LIMIT 10
        `, since).Scan(&topDiagnoses).Error
    })

    run(func() error {
        return h.db.WithContext(ctx).Raw(`
            SELECT
                jsonb_array_elements(medications)->>'drug_generic_name' as medication,
                COUNT(*) as count
            FROM prescriptions
            WHERE issued_at >= ?
            GROUP BY medication
            ORDER BY count DESC
            LIMIT 10
        `, since).Scan(&topMeds).Error
    })

    run(func() error {
        return h.db.WithContext(ctx).Raw(`
            SELECT
                DATE(issued_at) as date,
                COUNT(*) as count
            FROM prescriptions
            WHERE issued_at >= ?
            GROUP BY DATE(issued_at)
            ORDER BY date ASC
        `, since).Scan(&dailyTrend).Error
    })

    wg.Wait()

    if len(errs) > 0 {
        h.logger.Error("Dashboard query errors", zap.Errors("errors", errs))
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load dashboard data"})
        return
    }

    dispenseRate := 0.0
    if totalRx > 0 {
        dispenseRate = float64(dispensedRx) / float64(totalRx) * 100
    }

    c.JSON(http.StatusOK, gin.H{
        "success": true,
        "data": DashboardStats{
            PeriodDays:         query.PeriodDays,
            NewPatients:        newPatients,
            TotalPrescriptions: totalRx,
            DispensedRx:        dispensedRx,
            DispenseRate:       math.Round(dispenseRate*100) / 100,
            AvgAdherencePct:    avgAdherence,
            TopDiagnoses:       topDiagnoses,
            TopMedications:     topMeds,
            DailyRxTrend:       dailyTrend,
            HighRiskPatients:   highRisk,
        },
    })
}
```

---

## 12. Performance Optimization

### 12.1 JSON Codec Swap (sonic)

```go
// Replace encoding/json with ByteDance's sonic — 3-4x faster
import "github.com/bytedance/sonic"

// In main.go, before creating gin engine:
func init() {
    // Tell Gin to use sonic for all JSON operations
    // Only works on amd64 (x86_64)
    binding.EnableDecoderUseNumber()
}

// Or use gin-sonic binding
import "github.com/gin-contrib/sonic"

func main() {
    r := gin.New()
    r.Use(sonic.New())  // Replaces JSON codec globally
}
```

### 12.2 Response Caching

```go
// pkg/cache/cache.go
package cache

import (
    "crypto/sha256"
    "encoding/json"
    "fmt"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/redis/go-redis/v9"
)

func CacheMiddleware(rdb *redis.Client, ttl time.Duration) gin.HandlerFunc {
    return func(c *gin.Context) {
        // Only cache GET requests
        if c.Request.Method != "GET" {
            c.Next()
            return
        }

        // Build cache key from URL + user role (different roles may see different data)
        role, _ := c.Get("user_role")
        keySource := fmt.Sprintf("%s:%v", c.Request.URL.RequestURI(), role)
        hash := sha256.Sum256([]byte(keySource))
        cacheKey := fmt.Sprintf("http_cache:%x", hash[:8])

        ctx := c.Request.Context()

        // Cache hit
        if cached, err := rdb.Get(ctx, cacheKey).Bytes(); err == nil {
            c.Header("X-Cache", "HIT")
            c.Header("Content-Type", "application/json")
            c.Writer.WriteHeader(200)
            c.Writer.Write(cached)
            c.Abort()
            return
        }

        // Cache miss — wrap writer to capture response
        blw := &bodyLogWriter{body: &bytes.Buffer{}, ResponseWriter: c.Writer}
        c.Writer = blw

        c.Header("X-Cache", "MISS")
        c.Next()

        // Store successful responses in cache
        if c.Writer.Status() == 200 && blw.body.Len() > 0 {
            rdb.Set(ctx, cacheKey, blw.body.Bytes(), ttl)
        }
    }
}

type bodyLogWriter struct {
    gin.ResponseWriter
    body *bytes.Buffer
}

func (w *bodyLogWriter) Write(b []byte) (int, error) {
    w.body.Write(b)
    return w.ResponseWriter.Write(b)
}
```

### 12.3 Connection Pool Tuning

```go
// For a 4-core server handling mixed DB + API workloads:
sqlDB.SetMaxOpenConns(25)       // Limit total connections to DB
sqlDB.SetMaxIdleConns(10)       // Keep 10 warm in pool
sqlDB.SetConnMaxLifetime(1 * time.Hour)    // Prevent stale connections
sqlDB.SetConnMaxIdleTime(30 * time.Minute) // Reclaim idle ones

// Gin's server timeouts — critical for preventing goroutine leaks:
srv := &http.Server{
    ReadTimeout:       5 * time.Second,   // Time to read full request header + body
    ReadHeaderTimeout: 2 * time.Second,   // Time just for headers (prevents Slowloris)
    WriteTimeout:      10 * time.Second,  // Time to write the response
    IdleTimeout:       120 * time.Second, // Keep-alive idle connection lifetime
    MaxHeaderBytes:    1 << 20,           // 1MB max header size
}
```

---

## 13. Deployment

### 13.1 Multi-Stage Dockerfile

```dockerfile
# Dockerfile
# ── Stage 1: Build ────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

# Build dependencies
RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /build

# Download dependencies first (layer caching)
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
    -ldflags="-w -s -X main.version=$(git describe --tags --always)" \
    -o medtrack-api \
    ./cmd/server

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM scratch  # Smallest possible base image

# Copy essentials from builder
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /build/medtrack-api /medtrack-api

# Non-root user
USER 1001:1001

EXPOSE 8080

ENTRYPOINT ["/medtrack-api"]
```

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      APP_ENVIRONMENT: production
      APP_PORT: 8080
      DATABASE_HOST: db
      DATABASE_PORT: 5432
      DATABASE_USER: medtrack
      DATABASE_PASSWORD: ${DB_PASSWORD}
      DATABASE_NAME: medtrack
      REDIS_URL: redis://redis:6379
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "1.0"
          memory: 256M
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/health"]
      interval: 15s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: medtrack
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: medtrack
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medtrack"]
      interval: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
    restart: unless-stopped

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 13.2 Makefile

```makefile
# Makefile
.PHONY: run build test lint docker-build migrate

APP_NAME = medtrack-api
BUILD_DIR = ./bin
MAIN = ./cmd/server

run:
	go run $(MAIN)

build:
	CGO_ENABLED=0 go build -ldflags="-w -s" -o $(BUILD_DIR)/$(APP_NAME) $(MAIN)

test:
	go test ./... -v -race -cover -coverprofile=coverage.out
	go tool cover -html=coverage.out -o coverage.html

test-unit:
	go test ./tests/unit/... -v -race

test-integration:
	go test ./tests/integration/... -v -race

lint:
	golangci-lint run ./...

swagger:
	swag init -g cmd/server/main.go -o docs/

docker-build:
	docker build -t $(APP_NAME):latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

migrate-up:
	migrate -path ./db/migrations -database "$(DATABASE_URL)" up

migrate-down:
	migrate -path ./db/migrations -database "$(DATABASE_URL)" down 1

migrate-create:
	migrate create -ext sql -dir ./db/migrations -seq $(name)

deps:
	go mod download && go mod tidy

clean:
	rm -rf $(BUILD_DIR) coverage.out coverage.html
```

---

## 14. Gin vs Other Go Frameworks

```
Feature Comparison
─────────────────────────────────────────────────────────────────────────
Feature              Gin         Echo        Fiber       Chi
─────────────────────────────────────────────────────────────────────────
Routing              Radix tree  Radix tree  Radix tree  Radix tree
Middleware           ✅          ✅          ✅          ✅
JSON Binding         ✅          ✅          ✅          Manual
Validation           ✅ (built-in) Manual    Manual      Manual
stdlib compatible    ✅          ✅          ❌ (fasthttp) ✅
WebSocket            3rd party   Built-in    Built-in    3rd party
Performance (r/s)    ~97k        ~91k        ~190k       ~85k
Context alloc        sync.Pool   sync.Pool   Custom      stdlib
Community size       Largest     Large       Growing     Medium
Production maturity  Very High   High        Medium      High
─────────────────────────────────────────────────────────────────────────

When to choose Gin:
  ✅ Team knows Gin / existing codebase
  ✅ Need largest ecosystem of middleware plugins
  ✅ Want stdlib http.Handler compatibility
  ✅ Building REST APIs with heavy validation

When to choose Fiber:
  ✅ Maximum throughput is the #1 priority
  ✅ Background: Express.js developer
  ⚠️  Not stdlib compatible — harder to use 3rd party middleware

When to choose Echo:
  ✅ Slightly cleaner API than Gin
  ✅ Built-in WebSocket and SSE
  ✅ Similar performance to Gin

When to choose Chi:
  ✅ Prefer minimal frameworks built on stdlib
  ✅ Maximum compatibility with net/http ecosystem
  ✅ Don't need validation/binding built in
```

---

## Quick Reference Cheat Sheet

```go
// ── Engine Setup ──────────────────────────────────────────────
r := gin.New()
r.Use(gin.Logger(), gin.Recovery())
gin.SetMode(gin.ReleaseMode)  // Production

// ── Routes ────────────────────────────────────────────────────
r.GET("/path/:id", handler)
r.POST("/path", middleware1, middleware2, handler)
g := r.Group("/api/v1")
g.Use(authMiddleware)
g.GET("/patients", listHandler)

// ── Binding ───────────────────────────────────────────────────
c.ShouldBindJSON(&req)     // Body JSON
c.ShouldBindQuery(&query)  // Query params
c.ShouldBindUri(&uri)      // Path params
c.ShouldBindHeader(&h)     // Headers

// ── Context ───────────────────────────────────────────────────
c.Param("id")              // Path param
c.Query("page")            // Query param
c.GetHeader("X-API-Key")   // Header
c.Set("user", u)           // Store value
c.Get("user")              // Get stored value
c.ClientIP()               // Client IP
c.Next()                   // Next middleware
c.Abort()                  // Stop chain

// ── Response ──────────────────────────────────────────────────
c.JSON(200, gin.H{"key": "value"})
c.JSON(201, struct{})
c.String(200, "plain text")
c.File("./file.pdf")
c.FileAttachment("./f.pdf", "download.pdf")
c.Status(204)
c.AbortWithStatusJSON(401, gin.H{"error": "Unauthorized"})
c.Redirect(301, "/new-path")

// ── Server ────────────────────────────────────────────────────
r.Run(":8080")             // Quick start
http.Server{Handler: r}.ListenAndServe()  // Production
```

---

*Documentation compiled for MedEasy Healthcare Limited — MedTrack API (Go Edition)*
*Framework: Gin v1.10.x | Go 1.22 | GORM v2 | PostgreSQL 16 | Redis 7*
GINEOF