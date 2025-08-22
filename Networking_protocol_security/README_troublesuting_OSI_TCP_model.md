here’s a **combined troubleshooting guide using OSI vs TCP/IP**, with **layer-by-layer debugging techniques and practical examples**.

# 🔧 OSI vs TCP/IP Troubleshooting Guide

A step-by-step approach to diagnosing network problems layer by layer

## 1\. 🌐 Introduction

Both **OSI (7 layers)** and **TCP/IP (4 layers)** provide structured ways to understand, design, and troubleshoot networks.

- **OSI model**: Conceptual, detailed (7 layers).
- **TCP/IP model**: Practical, real-world implementation (4 layers).

When diagnosing problems, engineers often **walk through the layers** to isolate where the failure occurs.

## 2\. 🔍 Layer Mapping (OSI ↔ TCP/IP)

| **OSI Layer** | **TCP/IP Layer** | **Example Protocols/Tools** |
| --- | --- | --- |
| **7\. Application** | Application | HTTP, DNS, FTP, SMTP |
| **6\. Presentation** | Application | SSL/TLS, JPEG, MPEG |
| **5\. Session** | Application | RPC, NetBIOS |
| **4\. Transport** | Transport | TCP, UDP |
| **3\. Network** | Internet | IP, ICMP, ARP |
| **2\. Data Link** | Network Access | Ethernet, PPP, Wi-Fi |
| **1\. Physical** | Network Access | Cables, NICs, signals |

## 3\. 🛠️ Troubleshooting by Layers

We’ll use **OSI layers** as the reference, with **TCP/IP equivalents** noted.

### ****Layer 1: Physical (TCP/IP: Network Access)****

- **Problem**: No connectivity at all.
- **Symptoms**:
  - Link lights off on switch/router.
  - ping fails instantly.
- **Checks**:
  - Verify cables are plugged in.
  - Check NIC and switch port LEDs.
  - Run ethtool eth0 (Linux) or Device Manager (Windows).

**Example**:

\# Check if NIC is recognized

ip link show

### ****Layer 2: Data Link (TCP/IP: Network Access)****

- **Problem**: MAC addressing or switching issues.
- **Symptoms**:
  - Device shows “connected” but can’t reach gateway.
  - ARP table empty or incorrect.
- **Checks**:
  - Use arp -a to see MAC mappings.
  - Verify VLAN configuration.
  - Check switch port security rules.

**Example**:

\# Check ARP cache

arp -n

### ****Layer 3: Network (TCP/IP: Internet Layer)****

- **Problem**: IP routing issues.
- **Symptoms**:
  - Can reach local network but not outside.
  - Traceroute fails after a few hops.
- **Checks**:
  - Verify IP configuration (ip addr / ifconfig).
  - Check default gateway with ip route show.
  - Run ping 8.8.8.8 (Google DNS) to confirm external connectivity.

**Example**:

\# Check routing table

netstat -rn

### ****Layer 4: Transport (TCP/IP: Transport Layer)****

- **Problem**: TCP/UDP port issues.
- **Symptoms**:
  - Can ping host, but application (HTTP/FTP/DB) not working.
  - Connection refused / timeout.
- **Checks**:
  - Use telnet host 80 or nc -z host 80 to check ports.
  - Verify firewall (iptables, ufw, Windows Firewall).
  - Inspect TCP handshake with Wireshark.

**Example**:

\# Test if port 80 is open

nc -zv example.com 80

### ****Layer 5–7: Session, Presentation, Application (TCP/IP: Application Layer)****

- **Problem**: Application service issues.
- **Symptoms**:
  - Web server runs but gives errors.
  - DNS lookup fails (ping google.com doesn’t resolve).
- **Checks**:
  - Test DNS with nslookup google.com or dig.
  - Check logs for services (systemctl status nginx).
  - Verify SSL/TLS handshake for HTTPS (openssl s_client).

**Example**:

\# Check DNS resolution

dig google.com

\# Check if HTTP service is running

curl -I <http://localhost>

## 4\. ⚡ Practical Example: Website Down

1. **Ping server IP** → works ✅ (Layer 3 okay).
2. **Ping domain name** → fails ❌ → DNS issue (Layer 7).
3. Run dig example.com → No answer → DNS misconfigured.
    - Solution: Fix DNS A record.

## 5\. ⚡ Practical Example: Database Connection Fails

1. App error: “Connection refused.”
2. ping db-server → works ✅ (Layer 3 okay).
3. nc -zv db-server 5432 → connection refused ❌ (Layer 4 issue).
4. Check firewall → port 5432 blocked.
    - Solution: Open port in firewall.

## 6\. ✅ Best Practices

- Always start **bottom-up (Physical → Application)**.
- Use ping, traceroute, nc, dig, Wireshark.
- Document each test.
- Compare **OSI vs TCP/IP** to know conceptual vs practical debugging.

## 7\. 📌 Summary Table

| **OSI Layer** | **TCP/IP Layer** | **Troubleshooting Tools** |
| --- | --- | --- |
| Physical | Network Access | ethtool, ip link, LEDs |
| Data Link | Network Access | arp -a, switch config |
| Network | Internet | ping, traceroute, netstat -rn |
| Transport | Transport | nc, telnet, firewall logs |
| Session | Application | service logs, protocol analyzers |
| Presentation | Application | SSL/TLS debug (openssl) |
| Application | Application | curl, dig, logs, browser tools |

👉 This way, you can **systematically walk through OSI layers (conceptual)** and **TCP/IP layers (real-world implementation)** to **pinpoint issues quickly**.