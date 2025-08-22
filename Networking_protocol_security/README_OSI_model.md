# 📘 Technical Documentation: The OSI Model in Networking

## 1\. ****Definition****

The **OSI (Open Systems Interconnection) model** is a **conceptual framework** used to standardize the functions of a communication system into **seven distinct layers**. It was developed by the **International Organization for Standardization (ISO)** in 1984 to facilitate interoperability between different networking systems and vendors.

👉 Simply put: The OSI model defines **how data moves from one device to another** across a network by breaking the process into structured steps.

## 2\. ****The 7 Layers of the OSI Model****

The OSI model has **7 layers**, each with specific responsibilities:

| **Layer No.** | **Layer Name** | **Responsibility** | **Example Protocols/Technologies** |
| --- | --- | --- | --- |
| 7   | Application | User interface, application-level services | HTTP, FTP, SMTP, DNS, POP3, IMAP |
| 6   | Presentation | Data translation, encryption, compression | SSL/TLS, JPEG, MPEG, ASCII, EBCDIC |
| 5   | Session | Establish, maintain, terminate connections | NetBIOS, RPC, PPTP |
| 4   | Transport | Reliable delivery, error checking, flow ctrl | TCP, UDP, SCTP |
| 3   | Network | Routing, logical addressing | IP, ICMP, IPsec, OSPF, BGP |
| 2   | Data Link | Physical addressing, error detection/correct | Ethernet, PPP, Switches, ARP |
| 1   | Physical | Transmission of raw bits over medium | Cables, Hubs, Fiber optics, Wi-Fi |

## 3\. ****Detailed Explanation of Each Layer****

### ****Layer 1 – Physical Layer****

- Concerned with raw **bits transmission** over physical medium.
- Deals with **cables, hubs, switches, voltages, frequencies**.
- Defines **data rate, synchronization, and topology**.

**Example:** Ethernet cables (Cat5/6), Fiber optics, Wi-Fi signals.

### ****Layer 2 – Data Link Layer****

- Ensures reliable **node-to-node delivery**.
- Provides **MAC addressing** and **error detection (CRC)**.
- Divided into **two sublayers**:
  - **LLC (Logical Link Control)** – manages flow control & error checking.
  - **MAC (Media Access Control)** – hardware addressing.

**Example Protocols:** Ethernet (IEEE 802.3), PPP, ARP.  
**Example Device:** Switch.

### ****Layer 3 – Network Layer****

- Responsible for **routing data** from source to destination across networks.
- Provides **logical addressing (IP address)**.
- Determines **best path** via routing algorithms.

**Example Protocols:** IPv4, IPv6, ICMP, OSPF, BGP.  
**Example Device:** Router.

### ****Layer 4 – Transport Layer****

- Provides **end-to-end communication**.
- Ensures **reliable (TCP)** or **fast but unreliable (UDP)** delivery.
- Implements **error detection, sequencing, retransmission, flow control**.

**Example Protocols:** TCP, UDP, SCTP.  
**Example Device:** Gateway, firewall.

### ****Layer 5 – Session Layer****

- Manages **sessions** (connections) between applications.
- Provides **synchronization, checkpoints, recovery**.
- Establishes and terminates sessions.

**Example Protocols:** NetBIOS, RPC, PPTP.

### ****Layer 6 – Presentation Layer****

- Responsible for **data representation, translation, encryption, compression**.
- Ensures data is in a **format understandable** to both sender and receiver.

**Example Protocols:** SSL/TLS, JPEG, GIF, MPEG, ASCII, Unicode.

### ****Layer 7 – Application Layer****

- Closest to the **end-user**.
- Provides services for **applications** like browsers, email clients, etc.
- Enables **HTTP requests, email sending, file transfers**.

**Example Protocols:** HTTP, HTTPS, FTP, SMTP, IMAP, DNS.

## 4\. ****Where to Use the OSI Model****

- **Troubleshooting networks**: Identifying which layer has the issue (e.g., Layer 1 – faulty cable, Layer 3 – wrong IP, Layer 7 – app bug).
- **Standardization**: Helps vendors build interoperable devices.
- **Network design**: Provides modular approach in system architecture.
- **Education**: Clear abstraction for teaching networking concepts.

## 5\. ****Examples****

### ****Example 1 – Sending an Email****

1. **Application Layer** → User writes email (SMTP).
2. **Presentation Layer** → Encodes text (ASCII).
3. **Session Layer** → Opens connection to mail server.
4. **Transport Layer** → TCP ensures reliable delivery.
5. **Network Layer** → IP finds the recipient’s server.
6. **Data Link Layer** → Ethernet prepares frame.
7. **Physical Layer** → Data transmitted over Wi-Fi/cable.

### ****Example 2 – Website Request (HTTP)****

- You type <www.example.com> into browser:
  - **Application Layer:** HTTP request generated.
  - **Presentation Layer:** Data encrypted with TLS.
  - **Session Layer:** SSL handshake initiated.
  - **Transport Layer:** TCP ensures delivery.
  - **Network Layer:** IP finds server via DNS resolution.
  - **Data Link Layer:** Frame transmitted to ISP.
  - **Physical Layer:** Signal travels via fiber optic cable.

## 6\. ****Comparison with TCP/IP Model****

| **OSI Model (7 Layers)** | **TCP/IP Model (4 Layers)** |
| --- | --- |
| Application | Application (HTTP, FTP, SMTP) |
| Presentation | Application |
| Session | Application |
| Transport | Transport (TCP/UDP) |
| Network | Internet (IP, ICMP) |
| Data Link | Network Access (Ethernet, Wi-Fi) |
| Physical | Network Access |

👉 The TCP/IP model is **practical and widely used**, while the OSI model is **theoretical and educational**.

## 7\. ****Visualization****

OSI Model (7 layers) TCP/IP Model (4 layers)

\-------------------------------------------------------------

7\. Application ------------------> Application

6\. Presentation ------------------> Application

5\. Session ------------------> Application

4\. Transport ------------------> Transport

3\. Network ------------------> Internet

2\. Data Link ------------------> Network Access

1\. Physical ------------------> Network Access

## ✅ Conclusion

The **OSI model** is not implemented directly in networking but serves as a **guideline for understanding and troubleshooting communication systems**.

- It explains **how data flows from user to hardware and across networks**.
- While **TCP/IP is the real-world model**, OSI provides the **blueprint**.