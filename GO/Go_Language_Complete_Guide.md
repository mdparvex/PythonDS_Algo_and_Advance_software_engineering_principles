# Go (Golang) Complete Learning Path — For a Python Developer

**Who this is for:** You have ~4 years of Python experience (Django/FastAPI-style backend work). This guide leans on that background — every new Go concept is anchored to something you already know from Python, so you learn *differences*, not everything from zero.

**How to use this document:**
- Work top to bottom. Don't skip steps — later steps assume earlier ones.
- Each step ends with a **🧪 Practice Task**. Do it before moving on. Don't just read code — type it, run it, break it.
- Steps 1–9 are core language. Steps 10–14 are concurrency + tooling (Go's specialty). Steps 15–19 are the web framework (Gin) + database + auth — this is where it becomes "backend engineering" like your FastAPI/Django work.
- The **Final Capstone Project** at the end combines everything into one real service.

---

## Step 0 — Mental Model: Go vs Python

Before writing code, internalize these differences:

| Concept | Python | Go |
|---|---|---|
| Typing | Dynamic | Static, compiled |
| Error handling | try/except | Explicit `error` return values, no exceptions for control flow |
| OOP | Classes, inheritance | No classes, no inheritance — structs + interfaces (composition) |
| Concurrency | asyncio / threading (GIL-limited) | Goroutines + channels (true concurrency, built into language) |
| Package manager | pip + venv | Go modules (`go mod`) — built in, no virtualenv needed |
| Null | `None` | `nil` (works differently — see Step 8) |
| Web framework | Django / FastAPI | Gin / Echo / Fiber (much thinner, less "batteries included") |
| Execution | Interpreted | Compiled to a single static binary |

Go's philosophy: explicit over implicit, simplicity over cleverness, one obvious way to do things. You'll find it more verbose than Python at first — that's intentional, not a bug.

**🧪 Practice Task 0:** Write down (in your own words, 3-4 sentences) what you expect to be the hardest adjustment coming from Python. Revisit this note after finishing the guide and see if you were right.

---

## Step 1 — Installation & Environment Setup

1. Install Go from https://go.dev/dl/ (get the latest stable version).
2. Verify: `go version`
3. Unlike Python's venv-per-project model, Go uses **modules** — no virtual environment needed. Each project has a `go.mod` file declaring its module path and dependencies.
4. Set up your editor: VS Code with the official **Go extension** (auto-installs `gopls`, the language server) is the standard choice. Since you already use VS Code/Claude Code, this will feel familiar.

```bash
mkdir go-learning && cd go-learning
go mod init github.com/yourname/go-learning
```

This creates `go.mod` — think of it as `requirements.txt` + `pyproject.toml` combined, but version-locked automatically via `go.sum` (like `poetry.lock`).

**🧪 Practice Task 1:**
- Install Go, set up VS Code with the Go extension.
- Create a folder `hello-go`, run `go mod init`, create `main.go`:
```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, Go!")
}
```
- Run it with `go run main.go`, then compile it with `go build` and run the binary directly. Note the difference — no Python interpreter needed at runtime.

---

## Step 2 — Variables, Types & Constants

Go is statically typed. Every variable has a fixed type, known at compile time.

```go
// Explicit typing
var age int = 30
var name string = "Nazmul"

// Type inference (like Python, but still static under the hood)
city := "Dhaka"   // := is short variable declaration, infers type

// Constants
const AppName = "MedEasy"

// Basic types: int, int8/16/32/64, uint variants, float32/64, string, bool, byte, rune
```

Key differences from Python:
- `:=` only works inside functions for new variables. Top-level (package scope) needs `var`.
- Unused variables and unused imports are **compile errors** in Go — not warnings.
- No implicit type conversion. `int` + `float64` won't compile; you must cast explicitly: `float64(x)`.

**🧪 Practice Task 2:** Write a program that declares an `int`, `float64`, `string`, and `bool` using both `var` and `:=`. Deliberately trigger and read three compiler errors: an unused variable, an unused import, and a type mismatch in arithmetic. Fix each.

---

## Step 3 — Control Structures

```go
// if / else — no parentheses needed around condition
if age >= 18 {
    fmt.Println("adult")
} else if age > 12 {
    fmt.Println("teen")
} else {
    fmt.Println("child")
}

// Go has only ONE loop keyword: for
for i := 0; i < 5; i++ {
    fmt.Println(i)
}

// "while" loop equivalent
n := 0
for n < 5 {
    n++
}

// infinite loop
for {
    break
}

// switch — no fallthrough by default (opposite of Python's match-case gotchas)
switch day := "Mon"; day {
case "Sat", "Sun":
    fmt.Println("Weekend")
default:
    fmt.Println("Weekday")
}
```

**🧪 Practice Task 3:** Write a program that uses `for` to implement: (1) a classic counting loop, (2) a while-style loop, and (3) a `switch` that categorizes a number as negative/zero/positive. No `if/else` chain allowed for the switch part.

---

## Step 4 — Functions

```go
func add(a int, b int) int {
    return a + b
}

// shorthand when params share a type
func multiply(a, b int) int {
    return a * b
}

// multiple return values — Go's answer to Python's tuple returns,
// but idiomatically used for (result, error) pairs
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("cannot divide by zero")
    }
    return a / b, nil
}

// named return values
func rectangleProps(l, w float64) (area, perimeter float64) {
    area = l * w
    perimeter = 2 * (l + w)
    return // "naked" return
}

// variadic functions — like Python's *args
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}
```

There are no default argument values in Go (unlike Python) and no keyword arguments. This is a deliberate simplicity trade-off — you'll typically use a config struct instead (see Step 6).

**🧪 Practice Task 4:** Implement a `calculate(op string, nums ...float64) (float64, error)` function supporting "sum", "avg", "max", "min". Return an error for an unknown op. Call it from `main` and handle the error the Go way (`if err != nil`).

---

## Step 5 — Arrays, Slices, Maps

```go
// Array — fixed size, rarely used directly
var arr [3]int = [3]int{1, 2, 3}

// Slice — dynamic, like a Python list. This is what you'll actually use.
nums := []int{1, 2, 3}
nums = append(nums, 4)         // append returns a new slice — reassign it!
sub := nums[1:3]               // slicing works like Python

// Map — like a Python dict
ages := map[string]int{"Nazmul": 30, "Rahim": 25}
ages["Karim"] = 40
val, exists := ages["Nazmul"]  // "comma ok" idiom — check existence explicitly
delete(ages, "Karim")

// range — like Python's enumerate() / items()
for i, v := range nums {
    fmt.Println(i, v)
}
for k, v := range ages {
    fmt.Println(k, v)
}
```

Critical gotcha: slices share underlying arrays. Appending can silently mutate a "shared" slice or silently *not* mutate it depending on capacity. This trips up every Python developer at first.

**🧪 Practice Task 5:**
- Build a `map[string][]string` representing categories → list of medicine names (nod to your MedEasy catalog data).
- Write a function that takes this map and returns a flat, deduplicated slice of all medicine names.
- Deliberately create the slice-aliasing bug (two slices from the same `append` chain that unexpectedly affect each other), observe it, then explain in a comment why it happened.

---

## Step 6 — Structs & Methods (Go's replacement for classes)

```go
type Medicine struct {
    ID    int
    Name  string
    Price float64
}

// Method with a value receiver (gets a copy)
func (m Medicine) Describe() string {
    return fmt.Sprintf("%s costs %.2f", m.Name, m.Price)
}

// Method with a pointer receiver (can mutate the original — use this by default
// for anything that changes state, same reason you'd use `self` mutation in Python)
func (m *Medicine) ApplyDiscount(percent float64) {
    m.Price = m.Price - (m.Price * percent / 100)
}

func main() {
    med := Medicine{ID: 1, Name: "Paracetamol", Price: 10}
    med.ApplyDiscount(10) // Go auto-takes the address, no need for &med here
    fmt.Println(med.Describe())
}
```

There's no inheritance. Go uses **composition** (embedding):

```go
type Auditable struct {
    CreatedAt time.Time
    UpdatedBy string
}

type Product struct {
    Auditable // embedded — Product now "has" CreatedAt and UpdatedBy directly
    Name      string
}
```

**🧪 Practice Task 6:** Model a `Doctor` and a `Patient` struct (echoing your MedEasy telemedicine domain). Give `Doctor` a pointer-receiver method `AddConsultation(patient Patient, notes string)` that appends to an internal slice. Use struct embedding to give both types a shared `Timestamps` struct (CreatedAt/UpdatedAt).

---

## Step 7 — Interfaces (Go's version of polymorphism)

Go interfaces are **implicit** — a type satisfies an interface just by having the right methods, with no `implements` keyword. This is structurally similar to Python's duck typing, but enforced at compile time.

```go
type Shape interface {
    Area() float64
}

type Circle struct{ Radius float64 }
func (c Circle) Area() float64 { return 3.14159 * c.Radius * c.Radius }

type Rectangle struct{ W, H float64 }
func (r Rectangle) Area() float64 { return r.W * r.H }

func PrintArea(s Shape) {
    fmt.Println(s.Area())
}

// Both Circle and Rectangle satisfy Shape automatically
PrintArea(Circle{Radius: 5})
PrintArea(Rectangle{W: 3, H: 4})
```

The empty interface `interface{}` (or `any` in modern Go) is like Python's "accepts anything" — but you lose type safety and must type-assert to use it, so it's a last resort, not a default.

**🧪 Practice Task 7:** Define a `Notifier` interface with `Send(message string) error`. Implement it with two structs: `SMSNotifier` and `EmailNotifier` (mock the actual sending, just print). Write a function `Notify(n Notifier, msg string)` and call it with both types through the same function.

---

## Step 8 — Pointers & `nil`

```go
x := 10
p := &x        // p is a pointer to x
*p = 20        // dereference and mutate — x is now 20
fmt.Println(x) // 20

var mp *int    // nil pointer — no value yet
if mp == nil {
    fmt.Println("mp points to nothing")
}
```

Key difference from Python: in Python *everything* is a reference under the hood. In Go, you choose — pass by value (a copy) or by pointer (a reference) — and this choice matters constantly, especially with structs and methods (Step 6).

`nil` in Go isn't one universal "nothing" like Python's `None` — it applies differently to pointers, slices, maps, interfaces, channels, and functions, and comparing an interface holding a nil pointer to `nil` can surprise you. This is one of Go's most common bug sources for newcomers.

**🧪 Practice Task 8:** Write a function `updateInPlace(p *Medicine, newPrice float64)` that mutates via pointer, and a sibling function `updateCopy(m Medicine, newPrice float64) Medicine` that doesn't mutate the original. Call both, print before/after in `main`, and explain in comments exactly why one mutates the caller's variable and the other doesn't.

---

## Step 9 — Error Handling (idiomatic Go)

No exceptions for expected failure paths. Errors are values, returned explicitly and checked immediately.

```go
func readConfig(path string) (string, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return "", fmt.Errorf("reading config: %w", err) // %w wraps the original error
    }
    return string(data), nil
}

func main() {
    cfg, err := readConfig("config.txt")
    if err != nil {
        log.Fatal(err) // or handle gracefully
    }
    fmt.Println(cfg)
}
```

`panic`/`recover` exist (roughly like exceptions) but are reserved for truly unrecoverable situations — not for normal control flow like Python's `try/except` is often used.

**🧪 Practice Task 9:** Write a `ParseMedicineCSVLine(line string) (Medicine, error)` function that parses a comma-separated line ("name,price") into a `Medicine` struct, returning a descriptive wrapped error for malformed input (missing comma, non-numeric price). Write a `main` that processes 5 lines, some intentionally broken, and logs which succeeded/failed without crashing the program.

---

## Step 10 — Goroutines (Go's concurrency primitive)

This is Go's headline feature. A goroutine is a lightweight thread managed by the Go runtime — you can spawn thousands cheaply, unlike OS threads or even Python's `asyncio` tasks.

```go
func sayHello() {
    fmt.Println("hello from goroutine")
}

func main() {
    go sayHello()          // runs concurrently, doesn't block
    time.Sleep(time.Second) // naive way to "wait" — don't do this in real code (see WaitGroup below)
}
```

Proper synchronization with `sync.WaitGroup`:

```go
var wg sync.WaitGroup

for i := 0; i < 5; i++ {
    wg.Add(1)
    go func(n int) {
        defer wg.Done()
        fmt.Println("worker", n)
    }(i) // pass i explicitly — classic loop-variable-capture bug otherwise
}
wg.Wait()
```

**🧪 Practice Task 10:** Write a program that spawns 10 goroutines, each simulating a "fetch product price" task with `time.Sleep(random duration)`, using `sync.WaitGroup` to wait for all of them. Print total elapsed time and confirm it's close to the *slowest* single task, not the sum of all — proving they ran concurrently.

---

## Step 11 — Channels

Channels are how goroutines communicate safely, instead of sharing memory directly (Go's mantra: "share memory by communicating, don't communicate by sharing memory").

```go
ch := make(chan string)

go func() {
    ch <- "result from goroutine" // send
}()

msg := <-ch // receive (blocks until a value arrives)
fmt.Println(msg)

// Buffered channel
buffered := make(chan int, 3)
buffered <- 1
buffered <- 2

// Closing and ranging over a channel
results := make(chan int)
go func() {
    defer close(results)
    for i := 0; i < 5; i++ {
        results <- i * i
    }
}()
for r := range results {
    fmt.Println(r)
}

// select — like a switch for channels, useful for timeouts
select {
case msg := <-ch:
    fmt.Println(msg)
case <-time.After(2 * time.Second):
    fmt.Println("timeout")
}
```

**🧪 Practice Task 11:** Build a worker pool: 3 worker goroutines pull "order IDs" (ints) from an input channel, simulate processing with `time.Sleep`, and push "processed order" results to an output channel. Main collects and prints all results using `select` with a timeout guard so it never hangs forever.

---

## Step 12 — Packages, Modules & Project Structure

```
myapp/
  go.mod
  main.go
  internal/
    domain/
      medicine.go
    repository/
      medicine_repo.go
  cmd/
    server/
      main.go
```

- `internal/` is special — Go enforces that packages inside it can't be imported by code outside the module. Good for hiding implementation details.
- Exported identifiers (usable from other packages) start with a **capital letter**. Unexported ones (lowercase) are package-private. This replaces Python's `_private` convention with a compiler-enforced rule.
- `go get` fetches dependencies; `go mod tidy` cleans up `go.mod`/`go.sum` — analogous to `pip install` + `pip freeze`.

**🧪 Practice Task 12:** Restructure your Task 9 and Task 11 code into a small multi-package project: a `domain` package for the `Medicine` struct, a `parser` package for the CSV parsing logic, and a `main` package that ties them together. Practice capitalized vs lowercase naming to control what's exported.

---

## Step 13 — Testing

Go has testing built into the standard library — no pytest install needed.

```go
// medicine_test.go
package domain

import "testing"

func TestApplyDiscount(t *testing.T) {
    m := Medicine{Name: "Paracetamol", Price: 100}
    m.ApplyDiscount(10)
    if m.Price != 90 {
        t.Errorf("expected 90, got %.2f", m.Price)
    }
}

// Table-driven tests — the idiomatic Go pattern (similar to pytest.mark.parametrize)
func TestDivide(t *testing.T) {
    cases := []struct {
        a, b     float64
        expected float64
        wantErr  bool
    }{
        {10, 2, 5, false},
        {10, 0, 0, true},
    }
    for _, c := range cases {
        result, err := divide(c.a, c.b)
        if c.wantErr && err == nil {
            t.Errorf("expected error for %v/%v", c.a, c.b)
        }
        if !c.wantErr && result != c.expected {
            t.Errorf("got %v, want %v", result, c.expected)
        }
    }
}
```

Run with `go test ./...`. Add `-cover` for coverage, `-race` to catch data races in concurrent code (invaluable given Step 10-11).

**🧪 Practice Task 13:** Write table-driven tests for your `ParseMedicineCSVLine` function from Task 9, covering at least 5 cases (valid, missing field, bad price format, negative price, empty string). Run with `go test -v ./... -cover` and get to 100% coverage of that function.

---

## Step 14 — Standard Library Essentials

Skim and try these — you'll use them constantly:
- `net/http` — HTTP client and server (you'll build directly on this before adding Gin)
- `encoding/json` — struct tags control JSON field names, just like Pydantic models
- `context` — request-scoped cancellation/timeouts, used everywhere in web services
- `time` — durations, formatting, timers
- `os`, `io` — files and streams
- `log` / `log/slog` — structured logging (slog is the modern standard-library logger)

```go
type Medicine struct {
    Name  string  `json:"name"`
    Price float64 `json:"price"`
}

data, _ := json.Marshal(Medicine{Name: "Paracetamol", Price: 10})
fmt.Println(string(data)) // {"name":"Paracetamol","price":10}

var m Medicine
json.Unmarshal(data, &m)
```

**🧪 Practice Task 14:** Using only `net/http` (no framework yet), build a bare HTTP server with a `/medicines` GET endpoint that returns a hardcoded slice of `Medicine` structs as JSON. Add a `context.WithTimeout` around a simulated slow operation and demonstrate it being cancelled.

---

## Step 15 — Web Framework: Gin

Gin is the most widely used Go web framework — conceptually closest to Flask/FastAPI in ergonomics, but thinner and faster. Install:

```bash
go get -u github.com/gin-gonic/gin
```

```go
package main

import "github.com/gin-gonic/gin"

type Medicine struct {
    ID    int     `json:"id"`
    Name  string  `json:"name" binding:"required"`
    Price float64 `json:"price" binding:"required,gt=0"`
}

func main() {
    r := gin.Default() // includes logger + recovery middleware

    r.GET("/medicines/:id", func(c *gin.Context) {
        id := c.Param("id")
        c.JSON(200, gin.H{"id": id, "name": "Paracetamol"})
    })

    r.POST("/medicines", func(c *gin.Context) {
        var m Medicine
        if err := c.ShouldBindJSON(&m); err != nil {
            c.JSON(400, gin.H{"error": err.Error()})
            return
        }
        c.JSON(201, m)
    })

    r.Run(":8080") // listens on 0.0.0.0:8080
}
```

`binding` tags giving you FastAPI/Pydantic-style request validation for free is the closest 1:1 mapping to what you already know.

**🧪 Practice Task 15:** Build a Gin server with full CRUD (`GET /medicines`, `GET /medicines/:id`, `POST /medicines`, `PUT /medicines/:id`, `DELETE /medicines/:id`) backed by an in-memory slice (no DB yet). Add validation tags and return proper HTTP status codes (200/201/400/404).

---

## Step 16 — Middleware & Routing Groups

```go
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.AbortWithStatusJSON(401, gin.H{"error": "unauthorized"})
            return
        }
        c.Set("userID", "extracted-from-token")
        c.Next()
    }
}

func main() {
    r := gin.Default()

    public := r.Group("/api/v1")
    public.GET("/medicines", listMedicines)

    protected := r.Group("/api/v1/admin")
    protected.Use(AuthMiddleware())
    protected.POST("/medicines", createMedicine)

    r.Run(":8080")
}
```

**🧪 Practice Task 16:** Add a logging middleware (logs method, path, status, latency for every request) and an auth middleware guarding all `/admin/*` routes, applied to your Task 15 CRUD server. Test both protected and public routes with `curl`.

---

## Step 17 — Database Integration (GORM)

GORM is Go's most popular ORM — plays a role similar to Django's ORM or SQLAlchemy.

```bash
go get -u gorm.io/gorm
go get -u gorm.io/driver/postgres
```

```go
type Medicine struct {
    gorm.Model         // adds ID, CreatedAt, UpdatedAt, DeletedAt
    Name  string `json:"name"`
    Price float64 `json:"price"`
}

dsn := "host=localhost user=postgres password=postgres dbname=meddb port=5432"
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
if err != nil {
    log.Fatal(err)
}
db.AutoMigrate(&Medicine{}) // like Django/Alembic migrations, but auto

// CRUD
db.Create(&Medicine{Name: "Paracetamol", Price: 10})
var meds []Medicine
db.Where("price < ?", 50).Find(&meds)
db.Model(&Medicine{}).Where("id = ?", 1).Update("price", 15)
db.Delete(&Medicine{}, 1)
```

**🧪 Practice Task 17:** Wire GORM + PostgreSQL (or SQLite for local simplicity via `gorm.io/driver/sqlite`) into your Task 16 server, replacing the in-memory slice entirely. Every CRUD endpoint should now persist to the database. Add a `repository` layer (separate package) so handlers don't call `db` directly — mirrors the service/repository separation you already use in Django/FastAPI.

---

## Step 18 — Authentication (JWT)

```bash
go get -u github.com/golang-jwt/jwt/v5
```

```go
func GenerateToken(userID string) (string, error) {
    claims := jwt.MapClaims{
        "user_id": userID,
        "exp":     time.Now().Add(24 * time.Hour).Unix(),
    }
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString([]byte("your-secret-key")) // load from env/config in real code
}

func ValidateToken(tokenStr string) (jwt.MapClaims, error) {
    token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
        return []byte("your-secret-key"), nil
    })
    if err != nil || !token.Valid {
        return nil, fmt.Errorf("invalid token")
    }
    return token.Claims.(jwt.MapClaims), nil
}
```

**🧪 Practice Task 18:** Add `/auth/register` and `/auth/login` endpoints (hash passwords with `golang.org/x/crypto/bcrypt`). On login, issue a JWT. Rewrite your `AuthMiddleware` from Task 16 to actually validate the JWT (not just check for a non-empty header) and attach `user_id` to the Gin context for handlers to use.

---

## Step 19 — Advanced Concurrency Patterns & Context Propagation

```go
// Context-aware DB call with timeout — critical in real web services so one
// slow query can't hang a request forever
func GetMedicine(ctx context.Context, db *gorm.DB, id int) (*Medicine, error) {
    ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
    defer cancel()

    var m Medicine
    if err := db.WithContext(ctx).First(&m, id).Error; err != nil {
        return nil, err
    }
    return &m, nil
}
```

Fan-out/fan-in pattern for parallel work (e.g., calling multiple downstream services concurrently, similar to `asyncio.gather` in Python):

```go
func fetchAll(ids []int) []Medicine {
    results := make(chan Medicine, len(ids))
    var wg sync.WaitGroup
    for _, id := range ids {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            m, err := fetchOne(id) // some slow call
            if err == nil {
                results <- m
            }
        }(id)
    }
    go func() {
        wg.Wait()
        close(results)
    }()

    var all []Medicine
    for m := range results {
        all = append(all, m)
    }
    return all
}
```

**🧪 Practice Task 19:** Add an endpoint `GET /medicines/bulk?ids=1,2,3` that fetches multiple medicines concurrently using the fan-out/fan-in pattern above, propagates `c.Request.Context()` down to the DB call with a timeout, and gracefully returns partial results if one lookup fails or times out.

---

## Step 20 — Deployment: Docker & Config

```dockerfile
# Multi-stage build — final image has no Go toolchain, just the binary
FROM golang:1.23-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o server ./cmd/server

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/server .
EXPOSE 8080
CMD ["./server"]
```

Config via environment variables (12-factor style, same principle you already use for MedEasy's Azure deployments):

```go
type Config struct {
    Port      string
    DBUrl     string
    JWTSecret string
}

func LoadConfig() Config {
    return Config{
        Port:      getEnv("PORT", "8080"),
        DBUrl:     getEnv("DATABASE_URL", ""),
        JWTSecret: getEnv("JWT_SECRET", ""),
    }
}

func getEnv(key, fallback string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return fallback
}
```

**🧪 Practice Task 20:** Containerize your full application with the multi-stage Dockerfile above, externalize all secrets/config to environment variables, and run it with `docker-compose` alongside a Postgres container. Confirm the app starts cleanly from a fresh `docker-compose up` with no local Go install needed.

---

## 🏁 Final Capstone Project — "MediTrack API"

Build a production-shaped Go backend service that exercises **every concept above**. This mirrors real work you'd do at MedEasy, scoped down to a learnable size.

### Requirements

**Domain:** A pharmacy inventory + order management API.

**Must include:**

1. **Project structure** — `cmd/server`, `internal/domain`, `internal/repository`, `internal/handler`, `internal/middleware`, `internal/service` (clean separation, no handler talking directly to the DB).
2. **Entities (GORM models):** `Medicine` (name, price, stock, category), `User` (email, hashed password, role: admin/customer), `Order` (belongs to User, has many OrderItems), `OrderItem` (belongs to Order and Medicine, quantity).
3. **Auth:** Register/login with bcrypt-hashed passwords, JWT issuance, and role-based middleware (only `admin` can create/update/delete medicines; any authenticated user can place orders).
4. **Full CRUD** on medicines (admin-only for writes, public for reads), with request validation via Gin binding tags.
5. **Order flow:** `POST /orders` accepts a list of `{medicine_id, quantity}`, validates stock availability, decrements stock **atomically** (use a DB transaction — `db.Transaction(func(tx *gorm.DB) error {...})`), and computes total price server-side (never trust client-sent prices).
6. **Concurrency:** A `GET /medicines/bulk-check?ids=1,2,3` endpoint that concurrently checks live stock for multiple medicine IDs using goroutines + channels, with context timeout, returning partial results on partial failure.
7. **Middleware:** structured request logging (method, path, status, latency), panic recovery, and the auth/role middleware from #3.
8. **Error handling:** consistent JSON error shape (`{"error": "message"}`) across all failure paths — no raw panics leaking to the client.
9. **Testing:** table-driven unit tests for at least the order-total-calculation logic and the stock-validation logic, plus one integration test that spins up against a test SQLite DB and hits `POST /orders` end-to-end. Run with `-cover` and aim for meaningful coverage of `internal/service`.
10. **Config & Deployment:** all secrets/config via environment variables, a working multi-stage `Dockerfile`, and a `docker-compose.yml` running the API + Postgres together.
11. **Documentation:** a `README.md` with setup instructions and a table of all endpoints (method, path, auth required, description) — think of it as the API contract, similar to what you'd hand off to your Android/iOS teams at MedEasy.

### Definition of Done (self-check against this before you call it finished)

- [ ] `go build ./...` succeeds with zero errors
- [ ] `go vet ./...` and `gofmt -l .` report nothing
- [ ] `go test ./... -race -cover` passes with no data races
- [ ] `docker-compose up` brings up a fully working API from scratch
- [ ] You can, via `curl` or Postman: register → login → get a JWT → create a medicine (as admin) → place an order (as customer) → see stock decrement → attempt to over-order and get a clean 400 error
- [ ] Killing the DB connection mid-request doesn't crash the server (panic recovery middleware catches it)
- [ ] The bulk-check endpoint returns results even if one of the requested IDs is invalid

If you can complete this end to end without referring back to earlier steps, you've internalized idiomatic Go: static typing, explicit error handling, goroutines/channels, interfaces-over-inheritance, and the Gin + GORM web stack. At that point you're ready to comfortably contribute to a real Go service — including, if it's ever useful, a Go microservice alongside MedEasy's existing Django/FastAPI backend.

---

## Where to Go Next (Optional, Post-Capstone)

- **gRPC** (`google.golang.org/grpc`) — for internal service-to-service communication, common in microservice fleets.
- **Fiber** — an alternative to Gin, Express.js-styled, worth comparing once Gin feels natural.
- **Effective Go** (https://go.dev/doc/effective_go) — official idiomatic-style guide, worth reading once, not before.
- **Go Concurrency Patterns** (Rob Pike's talks) — deepen Step 10-11-19 once the basics are solid.
