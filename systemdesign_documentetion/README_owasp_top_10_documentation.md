# OWASP Top 10 - Complete Documentation

## 🔐 What is OWASP?

**OWASP** (Open Worldwide Application Security Project) is a **non-profit organization** that improves the security of software. It is known for producing **open-source security resources**, tools, and documentation.

---

## 🧩 What is the OWASP Top 10?

The **OWASP Top 10** is a regularly updated **awareness document** that identifies the **ten most critical web application security risks** based on:

- Real-world data (vulnerabilities found in applications)
- Severity of risk
- Exploitability and impact

It serves as a **baseline standard** for developers and organizations to secure their web applications.

---

## ⚒️ How Does It Work?

1. **Data Collection**: OWASP gathers data from security experts, vendors, bug bounty platforms, etc.
2. **Risk Analysis**: Each vulnerability is evaluated based on exploitability, detectability, and impact.
3. **Ranking**: The top 10 vulnerabilities are ranked.
4. **Awareness Guide**: OWASP publishes this as a public guide to educate developers and organizations.

---

## 📋 OWASP Top 10 List (2021)

| Code | Vulnerability Name | Description |
|------|--------------------|-------------|
| A01 | **Broken Access Control** | Unauthorized access to resources (e.g., user sees other users' data). |
| A02 | **Cryptographic Failures** | Weak or missing encryption leading to data exposure. |
| A03 | **Injection** | Malicious input causing SQL, NoSQL, or command injection. |
| A04 | **Insecure Design** | Poor design decisions leading to insecure behavior. |
| A05 | **Security Misconfiguration** | Misconfigured headers, error messages, or access control. |
| A06 | **Vulnerable and Outdated Components** | Use of outdated libraries or dependencies. |
| A07 | **Identification and Authentication Failures** | Broken login, session, or multi-factor security. |
| A08 | **Software and Data Integrity Failures** | Trusting unverified sources in updates or packages. |
| A09 | **Security Logging and Monitoring Failures** | Insufficient logging for attacks or forensic analysis. |
| A10 | **Server-Side Request Forgery (SSRF)** | Server makes unauthorized requests due to manipulated input. |

---

## ✅ How to Use OWASP Top 10 in Your Project

### Step 1: Understand Each Vulnerability
Use the descriptions and examples below to learn what each one is.

---

## 🔟 OWASP Top 10 Explained with Examples

### 🥇 A01 – **Broken Access Control**
**Problem**: Users can access things they shouldn't (e.g., view other users’ accounts).

**Insecure Code (Django)**:
```python
# Anyone can access any user’s profile
def get_profile(request):
    user_id = request.GET['user_id']
    return User.objects.get(id=user_id)
```
**Fix**:
```python
def get_profile(request):
    return request.user.profile
```

---

### 🥈 A02 – **Cryptographic Failures**
**Problem**: Storing passwords or transmitting sensitive data without encryption.

**Insecure Code**:
```python
user.password = request.POST['password']
```
**Fix**:
```python
from django.contrib.auth.hashers import make_password
user.password = make_password(request.POST['password'])
```

---

### 🥉 A03 – **Injection**
**Problem**: Input is used directly in a command or query.

**Insecure Code (Raw SQL)**:
```python
query = "SELECT * FROM users WHERE username = '%s'" % username
cursor.execute(query)
```
**Fix**:
```python
cursor.execute("SELECT * FROM users WHERE username = %s", [username])
```

---

### 🎯 A04 – **Insecure Design**
**Problem**: Security not considered during architecture or design.

**Example**: A banking app allows unlimited transfers without 2FA or fraud checks.

**Fix**: Design for secure practices (rate limiting, 2FA, input validation).

---

### ⚙️ A05 – **Security Misconfiguration**
**Problem**: Default passwords, verbose error messages, disabled security headers.

**Insecure Code**:
```python
DEBUG = True
```
**Fix**:
```python
DEBUG = False
```

---

### 🧱 A06 – **Vulnerable & Outdated Components**
**Problem**: Using old libraries with known vulnerabilities.

**Example**:
```bash
# requirements.txt
Django==2.0
```
**Fix**: Update to the latest secure versions regularly.

---

### 🔐 A07 – **Identification & Authentication Failures**
**Problem**: Broken login logic or missing session handling.

**Insecure Code**:
```python
def logout(request):
    pass
```
**Fix**:
```python
from django.contrib.auth import logout
logout(request)
```

---

### 📦 A08 – **Software & Data Integrity Failures**
**Problem**: Using unsigned packages or CI/CD processes without verification.

**Insecure Example**:
```bash
curl http://example.com/script.sh | bash
```
**Fix**: Use signed packages, checksum verification.

---

### 📋 A09 – **Security Logging & Monitoring Failures**
**Problem**: No logs for failed logins, no alerts for suspicious activity.

**Fix**: Enable structured logging and alerting systems.

---

### 🌐 A10 – **Server-Side Request Forgery (SSRF)**
**Problem**: Server fetches a URL based on user input.

**Insecure Code**:
```python
requests.get(request.GET['url'])
```
**Fix**: Validate and whitelist URLs.

---

## 🚧 How to Implement OWASP Top 10 in Your Workflow

### In Development:
- Use secure coding practices.
- Frameworks with built-in protection (Django, Rails).
- Input validation and output encoding.

### In Testing:
- OWASP ZAP
- Burp Suite
- Static analysis tools (Bandit, SonarQube)

### In CI/CD:
- Use vulnerability scanning tools: Snyk, Safety, Dependency-Check.

### In Deployment:
- Use HTTPS.
- Configure security headers.
- Enable proper logging.

---

## 🔧 Tools and Resources

| Tool | Purpose |
|------|---------|
| OWASP ZAP | Security scanner |
| Burp Suite | Manual/automated web app testing |
| Snyk / Safety | Dependency vulnerability check |
| Bandit | Python static analysis |
| SecurityHeaders.com | HTTP security header checker |
| Mozilla Observatory | Web security analysis |

---

## 📄 Summary

| Key Concept | What to Do |
|-------------|------------|
| Awareness | Learn the OWASP Top 10 risks |
| Prevention | Secure coding, validation, access control |
| Detection | Log and monitor attacks |
| Response | Patch, update, audit regularly |

---

Use this document to audit your application and integrate OWASP Top 10 guidelines into every phase of your software development lifecycle.

