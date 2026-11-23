# Protocol description

_For each of the design choices provide a short justification: why did you choose to design it the way you did?_

## Contents

- [Introduction](#1-introduction)
- [Terminology](#2-terminology)
- [Transport protocol](#3-transport-protocol)
- [Port number](#4-port-number)
- [Architecture](#5-architecture)
- [Information flow](#6-information-flow)
- [Protocol type](#7-protocol-type)
- [Constants](#8-constants)
- [Message format](#9-message-format)
- [Error handling](#10-error-handling)
- [Realistic scenario](#11-realistic-scenario)
- [Reliability mechanisms](#12-reliability-mechanisms)
- [Security mechanisms](#13-security-mechanisms)
- [Assumptions](#14-assumptions)

## 1. Introduction

This document describes a simple protocol for a smart home system. A user at a control panel can list the devices in a house, read sensor values, and switch actuators ON or OFF. All messages go through one central server.

**Why:** the project requires us to design our own application-layer protocol.

## 2. Terminology

| Term          | Meaning                                                        |
| ------------- | -------------------------------------------------------------- |
| Node          | A simulated device in the house with sensors and/or actuators. |
| Sensor        | Measures a value, e.g. `temperature`.                          |
| Actuator      | Can be switched, e.g. `irrigator_valve` (`ON` / `OFF`).        |
| Control panel | The user's program. It sends requests.                         |
| Server        | The central program. It receives requests and sends replies.   |
| Packet        | One message.                                                   |
| Payload       | The part of the packet with the actual request or answer.      |
| Action        | The kind of request: `READ`, `WRITE`, `LIST_NODES`.            |
| Access level  | The role of the user: `admin` or `guest`.                      |

## 3. Transport protocol

**TCP.**

**Why:** commands like "unlock the door" must not get lost, and TCP guarantees delivery and order.

## 4. Port number

**8081**, on `127.0.0.1`.

**Why:** 8081 is a high port number, so it is not reserved for standard services and needs no special rights.

## 5. Architecture

- **Control panel** = client. Several can connect at the same time.
- **Server** = the only server. It holds the nodes and carries out the requests.
- **Nodes** = simulated devices, stored inside the server program.

```
[Control panel 1] --TCP--> [Server] --> [Node: temperature]
[Control panel 2] --TCP--> [Server] --> [Node: irrigator]
```

**Why:** one central server means the control panels only need to know one address.

## 6. Information flow

**Request and reply (pull).** The control panel sends one request, and the server sends back exactly one reply. Nodes and server never send anything by themselves.

**Why:** it is the simplest to build and to understand.

## 7. Protocol type

- **Connection-oriented** (a TCP connection stays open for many requests).
- **Stateless**: every request contains everything the server needs, so the server does not remember earlier requests.

**Why:** TCP gives us the connection, and stateless messages are easy to reason about.

## 8. Constants

**Actions:** `READ`, `WRITE`, `LIST_NODES`

**Reply status:** `success`, `failed`, `error`

**Access levels:** `admin`, `guest`

**Restricted for guests:** `door_lock`, `main_valve`

**Device types** (sent as numbers):

| Name                 | Value |
| -------------------- | ----- |
| TEMPERATURE_SENSOR   | 0x001 |
| LIGHT_SENSOR         | 0x002 |
| HUMIDITY_SENSOR      | 0x003 |
| MOTION_SENSOR        | 0x004 |
| SMOKE_FLAME_DETECTOR | 0x005 |
| IRRIGATOR            | 0x101 |
| FAN                  | 0x102 |
| HEATER               | 0x103 |
| DOOR_LOCK            | 0x104 |
| CONTROL_PANEL        | 0x200 |
| PHONE                | 0x201 |
| SERVER               | 0x202 |

**Why:** sensors start with 0x0, actuators with 0x1, and system nodes with 0x2. A new device type is just a new number, so the protocol is easy to extend.

## 9. Message format

### Packet

Every message is JSON with four fields:

| Field         | Meaning                                   |
| ------------- | ----------------------------------------- |
| `device_id`   | Who sent it (a user name, or `"server"`). |
| `device_type` | One of the device type numbers above.     |
| `timestamp`   | Time created (seconds since 1970).        |
| `payload`     | The request or answer.                    |

Example request:

```json
{
  "device_id": "admin_user",
  "device_type": 512,
  "timestamp": 1760000000,
  "payload": {
    "action": "READ",
    "target_id": "temp_node_01",
    "resource": "temperature"
  }
}
```

### Framing

A four-byte unsigned integer in network byte order (big-endian) gives the length of the encoded JSON body in bytes. The prefix itself is excluded from the count. The client and server accept body lengths from 1 byte to 1 MiB.

```
+----------------+---------------------+
| 4 bytes length |     JSON text       |
+----------------+---------------------+
```

**Why:** TCP has no message borders, so the receiver needs the length. JSON is easy to read and debug.

### Requests (control panel -> server)

| Action       | Payload fields                   | Meaning             |
| ------------ | -------------------------------- | ------------------- |
| `LIST_NODES` | none                             | List all nodes.     |
| `READ`       | `target_id`, `resource`          | Get a sensor value. |
| `WRITE`      | `target_id`, `actuator`, `state` | Switch an actuator. |

### Replies (server -> control panel)

| To           | Payload                                                                            |
| ------------ | ---------------------------------------------------------------------------------- |
| `LIST_NODES` | `{"status": "success", "nodes": {"<id>": {"sensors": [...], "actuators": [...]}}}` |
| `READ`       | `{"status": "success", "resource": "temperature", "value": 23.4}`                  |
| `WRITE`      | `{"status": "success", "actuator": "irrigator_valve", "new_state": "ON"}`          |
| any error    | `{"status": "error", "message": "..."}`                                            |

### Who sends what

The control panel sends all requests. The server sends all replies. Nodes send nothing over the network.

## 10. Error handling

| Problem                             | What the server does                       |
| ----------------------------------- | ------------------------------------------ |
| No payload                          | Replies `error`: "Missing payload".        |
| Role not allowed                    | Replies `error`: "Access denied".          |
| Node does not exist                 | Replies `error`: "Target node not found".  |
| Unknown action                      | Replies `error`: "Unknown action".         |
| Actuator does not exist on the node | Replies `failed`.                          |
| Connection lost                     | Server logs it and closes that connection. |

**Why:** the user should always get an answer that explains what went wrong.

## 11. Realistic scenario

_The owner turns on the garden irrigator._

1. The control panel connects to the server (TCP, port 8081).
2. The user chooses "list nodes".
   - Panel -> server: `LIST_NODES`
   - Server -> panel: `success`, with `irrigator_node_01` and `temp_node_01`.
3. The user chooses "irrigator valve ON".
   - Panel -> server: `WRITE`, `target_id = irrigator_node_01`, `actuator = irrigator_valve`, `state = ON`
   - Server -> panel: `success`, `new_state = ON`
4. The panel shows "Irrigator is ON".
5. A guest who tries the same with `door_lock` is refused: `error`, "Access denied".

## 12. Reliability mechanisms

We rely on TCP for delivery, order and retransmission. We have no extra mechanisms of our own.

**Why:** We wanted to make it work before adding any extra pizazz.

## 13. Security mechanisms

A simple role check: `admin` can do everything, `guest` cannot touch restricted actuators. There is no login and no encryption.

**Why:** it shows the idea of access levels without extra complexity.

## 14. Assumptions

- The hardware is simulated; nodes are just software objects.
- Everything runs on one computer.
- Node names and user names are unique.
- If no access level is given, the user is treated as `guest`.
- Sensor values are numbers; actuator states are text such as `ON` and `OFF`.
